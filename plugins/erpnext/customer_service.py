from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from plugins.erpnext.create_issue import CreateIssueInput, erpnext_create_issue
from plugins.erpnext.llm import llm
from plugins.erpnext.prompt import APPROVAL_PROMPT

FIELD_LABELS = {"subject": "Subject", "description": "Description", "raised_by": "Customer email", "priority": "Priority"}


class Approval(BaseModel):
    answer: Literal["approved", "declined", "other"] = Field(
        description="approved: a clear yes. declined: a clear no. other: a question, a correction, or anything unclear."
    )


_approval_llm = llm.with_structured_output(Approval)


class TicketState(TypedDict, total=False):
    ticket: dict
    result: str


async def _human_approval(state: TicketState) -> Command[Literal["create_ticket", "__end__"]]:
    """Pauses the run and shows the customer the ticket details. The graph resumes when the customer answers."""
    details = "\n".join(f"{FIELD_LABELS[key]}: {value}" for key, value in state["ticket"].items() if value)
    customer_answer = interrupt(f"I am about to log a support ticket with these details:\n\n{details}\n\nShall I go ahead?")
    decision = await _approval_llm.ainvoke([SystemMessage(APPROVAL_PROMPT), HumanMessage(customer_answer)])
    if decision.answer == "approved":
        return Command(goto="create_ticket")
    if decision.answer == "declined":
        result = "The customer did not approve, so nothing was created. Do not run this again unless the customer asks for it again."
    else:
        # The customer said something else, so the main agent must see it and reply. It may run this tool again.
        result = (
            "Nothing was created. The customer did not answer the approval question. "
            f"They said: {customer_answer!r}. Reply to them, and if they still want the ticket, run this again."
        )
    return Command(update={"result": result}, goto=END)


async def _create_ticket(state: TicketState) -> TicketState:
    # A failure here raises a ToolException with the reason, which the main agent receives as the tool's error.
    return {"result": await erpnext_create_issue.ainvoke(state["ticket"])}


def _build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("human_approval", _human_approval)
    graph.add_node("create_ticket", _create_ticket)
    graph.add_edge(START, "human_approval")
    graph.add_edge("create_ticket", END)
    return graph.compile()


# Compiled once, when the plugin is imported at server start. No checkpointer of its own: it uses the main agent's,
# so the run can pause at human_approval and resume in the same chat.
_graph = _build_graph()


@tool(args_schema=CreateIssueInput)
async def erpnext_customer_service(
    subject: str,
    priority: str,
    description: str | None = None,
    raised_by: str | None = None,
) -> str:
    """Log a support ticket (Issue) in ERPNext for the customer.

    Use it when the customer reports a problem and wants it logged for the support team, only after the customer
    asked for it or agreed to it. It only creates new tickets; it cannot look up or update one.
    The customer is asked to approve the details before anything is created.
    Returns the new ticket number, or why nothing was created."""
    ticket = {"subject": subject, "priority": priority, "description": description, "raised_by": raised_by}
    result = await _graph.ainvoke({"ticket": ticket})
    return result["result"]
