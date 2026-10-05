from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plugins.erpnext.client import create_document


class CreateIssueInput(BaseModel):
    subject: str = Field(description="Short title of the problem, e.g. 'Cannot log in to my account'.")
    description: str | None = Field(None, description="Full details of the problem, as the customer explained it.")
    raised_by: str | None = Field(None, description="Customer's email address. Ask the customer for it; never guess it.")
    priority: Literal["Low", "Medium", "High"] = Field(
        description=(
            "How urgent the problem is, decided from the customer's state: how they speak (calm, worried, angry) "
            "and how important the problem is (blocks their work or money = High, an annoyance = Medium, "
            "a small question or cosmetic issue = Low)."
        )
    )



 
@tool(args_schema=CreateIssueInput)
async def erpnext_create_issue(
    subject: str,
    priority: str,
    description: str | None = None,
    raised_by: str | None = None,
) -> str:
    """Create a support ticket (Issue) in ERPNext for the customer.

    Use this when the customer reports a problem and wants it logged for the support team.
    Do NOT use it to look up or update an existing ticket; this tool only creates new ones.
    It creates a record that cannot be undone from here, so only call it after the customer
    has confirmed the details. Returns the new ticket number (e.g. ISS-2026-00001)."""
    fields = {"subject": subject, "description": description, "raised_by": raised_by, "priority": priority}
    issue = await create_document("Issue", {key: value for key, value in fields.items() if value})
    return f"Issue {issue['name']} created."
