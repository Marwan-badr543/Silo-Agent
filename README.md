# Silo

**An open-source AI customer service agent you extend with plugins.**

Silo is one main agent that talks to customers like a caring support manager. It understands what the customer needs, answers questions from your company documents, and gets things done in your systems, such as logging a support ticket in ERPNext. Everything it can do comes from **plugins**. To teach Silo a new skill, you add a plugin. You never touch the core.

Built with [LangGraph](https://github.com/langchain-ai/langgraph), FastAPI and ChromaDB. It runs on free NVIDIA-hosted models.

> **Status:** early and under active development. See [Limitations](#limitations).

## What it can do today

| Plugin | What the agent can do with it |
|---|---|
| `erpnext` | Log a support ticket (Issue) in ERPNext. The customer sees the exact ticket details and must approve them before anything is written. |
| `company_knowledge` | Answer questions about your company (policies, shipping, warranty, prices...) from your own PDF files, using retrieval (RAG). |

Customers reach Silo through a **Telegram bot** or the **HTTP endpoint** `POST /chat`.

## How it works

```
 Customer ──► Telegram / POST /chat
                    │
                    ▼
        ┌───────────────────────┐
        │  Main agent (agent/)  │  talks to the customer, understands the intent,
        │  LangGraph + SQLite   │  offers an action in plain words, reads results
        └───────┬───────────────┘
                │  get_tool_info(name)  ← shows a tool's description and fields
                │  use_tool(name, args) ← runs it
                ▼
     ┌────────────────────────────── plugins/ ──────────────────────────────┐
     │  erpnext                         company_knowledge                    │
     │  human approval ─► create ticket  search ChromaDB ─► top passages     │
     └───────────────────────────────────────────────────────────────────────┘
```

- **One main agent.** It sees only the *names* of the plugin tools. When it needs one, it asks for the tool's schema with `get_tool_info`, then runs it with `use_tool`. Adding a plugin does not change the core or the prompt.
- **Plugins are independent.** Each plugin brings its own model, prompt, graph, client and environment variables. A plugin can be a plain function, or run a whole agent or graph inside. The main agent only sees a tool that takes arguments and returns text.
- **Memory.** Each chat is a LangGraph thread (`telegram-<chat id>` for Telegram), saved in SQLite, so the conversation survives restarts.
- **The customer talks to one agent only.** Plugins never chat with the customer.

### Safe writes: human approval in code

A prompt is a guess, not a guarantee, so writes are guarded in code. The ERPNext plugin runs a small graph:

```
human_approval ──approved──► create_ticket ──► ticket number back to the agent
       │
       └─ declined / unclear ──► nothing is created
```

`human_approval` pauses the run with LangGraph's `interrupt()` and sends the customer the exact ticket details. The customer's next message resumes the run. A model reads it as `approved`, `declined` or `other`, and anything unclear never counts as approval. The main agent cannot approve for the customer.

### Reliability

- A step limit stops runaway loops.
- A failed model call is retried once, with a hint about what went wrong. If it fails again, the customer gets a friendly fallback message.
- The agent answers company questions only from retrieved passages, and says so when the documents do not cover a question.

## Quick start

**Requirements:** Python 3.12, a free [NVIDIA API key](https://build.nvidia.com/), and optionally a Telegram bot token and an ERPNext site.

```bash
git clone https://github.com/Marwan-badr543/Silo-Agent.git
cd Silo-Agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
NVIDIA_API_KEY=your-nvidia-key          # required: the model and the embeddings

TELEGRAM_BOT_TOKEN=your-bot-token       # optional: starts the Telegram bot

ERPNEXT_URL=http://localhost:8000       # for the erpnext plugin
ERPNEXT_API_KEY=your-erpnext-api-key
ERPNEXT_API_SECRET=your-erpnext-api-secret
```

The ERPNext API user needs permission to create *Issue* documents (for example the *Support Team* role).

### Add your company documents

```bash
# put your PDFs in plugins/company_knowledge/docs/  (a demo PDF is already there; delete it first)
python -m plugins.company_knowledge.ingest
```

PDFs must contain real text, since scanned images are not supported. Run the command again whenever the PDFs change, then restart the server.

### Run

```bash
python main.py          # serves on http://127.0.0.1:7000
```

```bash
curl -X POST http://127.0.0.1:7000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How long do I have to return a product?", "session_id": "demo-1"}'
# {"answer": "..."}
```

Use the same `session_id` to continue a conversation. Without it, each call is a fresh chat.

## Project structure

```
main.py                 FastAPI app: starts the agent and the Telegram bot
agent/                  THE CORE. You should not need to edit it.
  silo_agent.py           the main agent graph and ask()
  meta_tools.py           get_tool_info and use_tool
  prompts.py              the main agent's prompt
  call_llm.py             the model client
api/                    HTTP layer: /chat endpoint, Telegram channel, agent factory
plugins/                everything the agent can do. Add yours here.
  erpnext/                log a support ticket, with human approval
  company_knowledge/      RAG over your PDFs (ChromaDB)
```

## Write your own plugin

1. Create `plugins/<name>/` and export `TOOLS`, a list of LangChain tools, from its `__init__.py`.
2. Add it to `TOOLS_BY_NAME` in `plugins/__init__.py`.
3. Give every tool a clear name, a description that says when to use it, and a pydantic `args_schema` with a description for each field.

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class OrderStatusInput(BaseModel):
    order_id: str = Field(description="The order number the customer gave, e.g. 'A1042'.")

@tool(args_schema=OrderStatusInput)
async def order_status(order_id: str) -> str:
    """Look up the status of an order. Use it when the customer asks where their order is."""
    return "Order A1042 shipped on 12 May."
```

Rules for plugins: never import from `agent/` or from another plugin, read secrets from environment variables, return short factual text, and raise `ToolException` with a clear reason when something fails. See [`plugins/README.md`](plugins/README.md) for details.

## Limitations

- **No automated tests yet.** Plugins and flows have only been checked by hand.
- **Model quirks.** The default model (`openai/gpt-oss-20b`) is fast and free but sometimes writes a malformed tool call. Silo retries once, then falls back to a friendly message. A stronger model would be more reliable (change it in `agent/call_llm.py`).
- **Approval costs a model call**, and a question asked during approval counts as "other": the main agent sees it as a tool result, not as a normal message.
- **After re-ingesting documents, restart the server.** A running server does not see data written by another process.
- **The similarity cutoff** in `plugins/company_knowledge/search.py` was tuned on a small demo, so retune it on your documents.
- **A fallback does not notify a human.** The customer is told a human will follow up, but there is no handoff yet.

## Rules for contributors

The project rules are in [`CLAUDE.md`](CLAUDE.md): keep the code simple and reviewable, keep plugins independent, and guard anything irreversible in code.
