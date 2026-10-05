from dotenv import load_dotenv

# Plugins read their settings from the environment when they are imported, so load .env first.
# This also makes scripts that import a plugin directly (for example the knowledge ingest) work.
load_dotenv()

from plugins import company_knowledge, erpnext  # noqa: E402

TOOLS_BY_NAME = {tool.name: tool for tool in [*erpnext.TOOLS, *company_knowledge.TOOLS]}
