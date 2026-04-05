"""Shared message types, factory functions, and validation for pi-bench."""

import uuid
from typing import Any


# --- Factory functions ---


def make_assistant_msg(
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    cost: float = 0.0,
    usage: dict | None = None,
) -> dict:
    """Create an assistant message dict."""
    msg: dict[str, Any] = {"role": "assistant", "cost": cost, "usage": usage}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return msg


def make_user_msg(
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    cost: float = 0.0,
    usage: dict | None = None,
) -> dict:
    """Create a user message dict."""
    msg: dict[str, Any] = {"role": "user", "cost": cost, "usage": usage}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return msg


def make_tool_msg(
    call_id: str,
    content: str,
    requestor: str,
    error: bool = False,
    name: str | None = None,
) -> dict:
    """Create a tool result message dict."""
    msg: dict[str, Any] = {
        "role": "tool",
        "id": call_id,
        "content": content,
        "requestor": requestor,
        "error": error,
    }
    if name is not None:
        msg["name"] = name
    return msg


def make_system_msg(content: str) -> dict:
    """Create a system message dict."""
    return {"role": "system", "content": content}


def build_tool_call(
    name: str,
    arguments: dict | None = None,
    requestor: str = "assistant",
    call_id: str | None = None,
) -> dict:
    """Create a tool call dict (for embedding in assistant/user messages)."""
    return {
        "id": call_id or str(uuid.uuid4()),
        "name": name,
        "arguments": arguments or {},
        "requestor": requestor,
    }


# --- Validation ---


def validate_message(msg: dict) -> bool:
    """Check that a message has content XOR tool_calls (not both, not neither).

    Only applies to assistant and user messages.
    """
    if msg.get("role") not in ("assistant", "user"):
        return True
    has_content = "content" in msg and msg["content"] is not None
    has_tools = "tool_calls" in msg and msg["tool_calls"] is not None
    return has_content != has_tools


def is_stop_signal(msg: dict) -> bool:
    """Check if a message contains a stop, transfer, or out-of-scope signal."""
    content = msg.get("content", "")
    return content in ("###STOP###", "###TRANSFER###", "###OUT-OF-SCOPE###")


# --- Content extraction ---


def extract_message_content(msg: dict) -> str:
    """Extract text content from a message, handling string and list formats.

    Handles both plain string content and Anthropic-format list content blocks
    (e.g., [{"type": "text", "text": "..."}]).
    """
    content = msg.get("content", "")
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict)
        )
    return content if isinstance(content, str) else ""
