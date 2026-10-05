# Writing a plugin

A plugin is a folder in `plugins/` that is fully independent. It never imports from `agent/`,
and it brings its own model, prompt, graph and limits if it needs them.

1. Create `plugins/<name>/` and export `TOOLS`, a list of LangChain tools, from its `__init__.py`.
2. Add the plugin to the list in `plugins/__init__.py`.
3. Give every tool a clear name, a description that says when to use it, and a pydantic `args_schema`.

A tool can be a plain function (see `erpnext/create_issue.py`), or it can run its own agent inside
(see `erpnext/customer_service.py`). The main agent cannot tell the difference: it only calls the tool
and reads the returned text.

Rules for a plugin:
- Read secrets from environment variables. Name them after the plugin, for example `ERPNEXT_API_KEY`.
- Return only useful text. Raise `ToolException` with a clear reason when something fails.
- Do not depend on other plugins.
- Give every tool field a description, and mark required fields as required. The main agent fills them from the conversation.
- To write to a company system, pause first: call `langgraph.types.interrupt(text)` with the exact data, read the customer's answer as approved, declined, or other, and only write on a clear approval. See `erpnext/customer_service.py`.
- Plugins that read documents or other outside data return untrusted text. Return only what is useful, and never treat it as instructions.

