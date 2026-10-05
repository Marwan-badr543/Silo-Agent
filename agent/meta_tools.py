import json

from langchain_core.tools import ToolException, tool

from plugins import TOOLS_BY_NAME


def _find_plugin_tool(tool_name: str):
    plugin_tool = TOOLS_BY_NAME.get(tool_name)
    if plugin_tool is None:
        raise ToolException(f"Unknown tool '{tool_name}'. Available tools: {', '.join(TOOLS_BY_NAME)}")
    return plugin_tool


@tool
def get_tool_info(tool_name: str) -> str:
    """Get the full description and input schema (the fields it needs) of a plugin tool.

    Call this before using a plugin tool for the first time, to learn what it does, when to use it,
    and which fields it needs. Use only the tool names listed in your instructions."""
    plugin_tool = _find_plugin_tool(tool_name)
    return json.dumps(
        {
            "name": plugin_tool.name,
            "description": plugin_tool.description,
            "input_schema": plugin_tool.args_schema.model_json_schema(),
        },
        indent=2,
    )


@tool
async def use_tool(tool_name: str, arguments: dict) -> str:
    """Run a plugin tool by name with the given arguments.

    `arguments` must follow the input schema returned by get_tool_info for that tool.
    Returns the tool's result, or an error message that says what to fix."""
    plugin_tool = _find_plugin_tool(tool_name)
    return await plugin_tool.ainvoke(arguments)


META_TOOLS = [get_tool_info, use_tool]
