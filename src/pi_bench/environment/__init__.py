"""Environment — deterministic tool execution against an in-memory DB."""

from typing import Any, Callable

from pi_bench.environment.execution import make_tool_call
from pi_bench.environment.state import (
    get_db_hash,
    set_state,
    check_db,
    is_solo_mode,
    set_solo_mode,
)

# Re-export type aliases
ToolFn = Callable[..., Any]
ToolMap = dict[str, ToolFn]
ToolResult = dict[str, Any]
ToolSchema = dict[str, Any]
Env = dict[str, Any]


def create_environment(
    domain_name: str,
    policy: str,
    tools: ToolMap,
    db: dict,
    user_tools: ToolMap | None = None,
    tool_schemas: list[ToolSchema] | None = None,
) -> Env:
    """Create an environment. Returns a plain dict."""
    return {
        "domain_name": domain_name,
        "policy": policy,
        "tools": tools,
        "user_tools": user_tools or {},
        "tool_schemas": tool_schemas or [],
        "db": db,
        "solo_mode": False,
    }


def get_domain_name(env: Env) -> str:
    """Get the environment's domain name."""
    return env["domain_name"]


def get_policy(env: Env) -> str:
    """Get the environment's policy text."""
    return env["policy"]


def get_tool_schemas(env: Env) -> list[ToolSchema]:
    """Get tool schemas for LLM function calling."""
    return env["tool_schemas"]


def get_info(env: Env) -> dict[str, Any]:
    """Return serializable environment metadata (no functions or DB)."""
    return {
        "domain_name": env["domain_name"],
        "policy": env["policy"],
        "tool_schemas": env["tool_schemas"],
        "solo_mode": env["solo_mode"],
    }


__all__ = [
    "create_environment",
    "make_tool_call",
    "get_db_hash",
    "get_domain_name",
    "get_policy",
    "get_tool_schemas",
    "get_info",
    "set_state",
    "check_db",
    "is_solo_mode",
    "set_solo_mode",
]
