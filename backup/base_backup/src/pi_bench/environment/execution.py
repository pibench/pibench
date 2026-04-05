"""Tool execution — route and execute tool calls against the environment."""

import json
from typing import Any, Callable

ToolFn = Callable[..., Any]
ToolMap = dict[str, ToolFn]
ToolResult = dict[str, Any]
ToolSchema = dict[str, Any]
Env = dict[str, Any]


def make_tool_call(
    env: Env,
    tool_name: str,
    call_id: str = "call",
    arguments: dict | None = None,
    requestor: str = "assistant",
) -> ToolResult:
    """Execute a tool call against an environment.

    Routes by requestor: "assistant" -> agent tools, "user" -> user tools.
    Never raises — errors are returned in the result.
    """
    if arguments is None:
        arguments = {}

    tool_fn, error_msg = _resolve_tool(env, tool_name, requestor)

    if tool_fn is None:
        return _error_result(call_id, requestor, error_msg)

    try:
        raw_result = tool_fn(env["db"], **arguments)
        content = _to_json_string(raw_result)
        return {"id": call_id, "content": content, "requestor": requestor, "error": False}
    except Exception as e:
        return _error_result(call_id, requestor, str(e))


def _resolve_tool(
    env: Env, tool_name: str, requestor: str
) -> tuple[ToolFn | None, str]:
    """Find the tool function for this requestor and tool name.

    Returns (tool_fn, "") on success, or (None, error_message) on failure.
    """
    agent_tools: ToolMap = env["tools"]
    user_tools: ToolMap = env["user_tools"]

    if requestor == "assistant":
        if tool_name in agent_tools:
            return agent_tools[tool_name], ""
        if tool_name in user_tools:
            return None, f"Tool '{tool_name}' is not available to assistant."

    elif requestor == "user":
        if env["solo_mode"]:
            return None, "User tools are disabled in solo mode."
        if tool_name in user_tools:
            return user_tools[tool_name], ""
        if tool_name in agent_tools:
            return agent_tools[tool_name], ""

    return None, f"Tool '{tool_name}' not found."


def _error_result(call_id: str, requestor: str, message: str) -> ToolResult:
    """Build an error result dict."""
    return {
        "id": call_id,
        "content": json.dumps(f"Error: {message}"),
        "requestor": requestor,
        "error": True,
    }


def _to_json_string(value: Any) -> str:
    """Convert any value to a JSON string."""
    if isinstance(value, str):
        return json.dumps(value)
    return json.dumps(value, default=str)
