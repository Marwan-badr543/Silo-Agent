import json
import os
import re

import httpx
from langchain_core.tools import ToolException


def _error_message(response: httpx.Response) -> str:
    """Pull the readable reason out of a Frappe error response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    messages = json.loads(body.get("_server_messages", "[]"))
    if messages:
        return re.sub(r"<[^>]+>", "", json.loads(messages[0])["message"])
    return body.get("_error_message") or response.text[:300]


async def create_document(doctype: str, data: dict) -> dict:
    """Create a document in ERPNext and return it. Raises ToolException with the reason on failure."""
    url = f"{os.environ['ERPNEXT_URL']}/api/resource/{doctype}"
    token = f"{os.environ['ERPNEXT_API_KEY']}:{os.environ['ERPNEXT_API_SECRET']}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=data, headers={"Authorization": f"token {token}"})
    except httpx.HTTPError as error:
        raise ToolException(f"ERPNext is not reachable ({type(error).__name__}). Do not retry; tell the customer a human will follow up.")
    if response.is_error:
        raise ToolException(f"ERPNext refused to create the {doctype} (HTTP {response.status_code}): {_error_message(response)}")
    return response.json()["data"]
