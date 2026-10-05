import logging
import uuid

import openai
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from agent.call_llm import gpt_oss_llm
from agent.meta_tools import META_TOOLS
from agent.prompts import build_system_prompt

# How many recent messages the model sees, so long chats do not grow without limit.
MAX_HISTORY_MESSAGES = 20
# Safety net against a loop that never stops. Each model call or tool run is one step.
MAX_STEPS = 12
# Errors a model call can raise. ValueError is what langchain raises when the provider answers with an error
# body, for example a 400 for a malformed tool call, which gpt-oss does now and then.
MODEL_ERRORS = (ValueError, openai.APIError)
# The model never sees a provider error, so the retry tells it what went wrong. Used for that one call only.
RETRY_HINT = (
    "Your last reply could not be read, probably because a tool call was malformed. "
    "Reply again. If you call a tool, use its exact name from the tool list and valid JSON arguments."
)
logger = logging.getLogger(__name__)
FALLBACK_ANSWER = "Sorry, I could not finish that. A human from our team will follow up."


class SiloAgent:
    """One-node agent. The graph is compiled once, when the object is created."""

    def __init__(self, checkpointer: BaseCheckpointSaver) -> None:
        self.llm = gpt_oss_llm.bind_tools(META_TOOLS)
        self.system_prompt = build_system_prompt()
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer: BaseCheckpointSaver):
        graph = StateGraph(MessagesState)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(META_TOOLS, handle_tool_errors=True))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        return graph.compile(checkpointer=checkpointer)

    async def _agent_node(self, state: MessagesState):
        # start_on="human" so a tool result is never cut off from the tool call that asked for it.
        recent = trim_messages(
            state["messages"], strategy="last", token_counter=len, max_tokens=MAX_HISTORY_MESSAGES, start_on="human"
        )
        messages = [SystemMessage(self.system_prompt)] + recent
        try:       
            reply = await self.llm.ainvoke(messages)
        except MODEL_ERRORS:
            reply = await self.llm.ainvoke(messages + [SystemMessage(RETRY_HINT)])
        return {"messages": [reply]}

    async def ask(self, question: str, thread_id: str | None = None) -> str:
        """Same thread_id = same conversation. No thread_id = a fresh one-off chat."""
        config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}, "recursion_limit": MAX_STEPS}
        # A paused plugin (for example one waiting for the customer to approve) needs this message as its answer.
        paused = (await self.graph.aget_state(config)).interrupts
        graph_input = Command(resume=question) if paused else {"messages": [("user", question)]}
        try:
            result = await self.graph.ainvoke(graph_input, config)
        except GraphRecursionError:
            return FALLBACK_ANSWER
        except MODEL_ERRORS as error:
            logger.warning("Model call failed twice: %s", error)
            return FALLBACK_ANSWER
        if result.get("__interrupt__"):
            return result["__interrupt__"][0].value
        return result["messages"][-1].content if result["messages"][-1].content else FALLBACK_ANSWER
