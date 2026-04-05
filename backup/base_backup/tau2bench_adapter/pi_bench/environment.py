"""Adapter: maps pi_bench.environment interface to tau2's Environment class."""

from tau2.data_model.message import ToolCall
from tau2.environment.environment import Environment


def make_tool_call(
    env: Environment,
    tool_name: str,
    call_id: str = "",
    arguments: dict | None = None,
    requestor: str = "assistant",
) -> dict:
    """Execute a tool call and return a plain dict result."""
    tc = ToolCall(
        id=call_id,
        name=tool_name,
        arguments=arguments or {},
        requestor=requestor,
    )
    tool_msg = env.get_response(tc)
    return {
        "id": tool_msg.id,
        "content": tool_msg.content,
        "requestor": tool_msg.requestor,
        "error": tool_msg.error,
    }


def get_db_hash(env: Environment) -> str:
    """Get the database hash."""
    return env.get_db_hash()


def get_domain_name(env: Environment) -> str:
    """Get the domain name."""
    return env.get_domain_name()


def get_policy(env: Environment) -> str:
    """Get the policy text."""
    return env.get_policy()


def get_tool_schemas(env: Environment) -> list[dict]:
    """Get tool schemas in a format with 'name' and 'parameters' keys."""
    tools = env.get_tools()
    schemas = []
    for tool in tools:
        schema = tool.openai_schema
        fn = schema.get("function", {})
        schemas.append({
            "name": fn.get("name", tool.name),
            "parameters": fn.get("parameters", {}),
        })
    return schemas


def is_solo_mode(env: Environment) -> bool:
    """Check if the environment is in solo mode."""
    return env.solo_mode


def set_solo_mode(env: Environment, solo: bool) -> None:
    """Toggle solo mode."""
    env.set_solo_mode(solo)


def get_info(env: Environment) -> dict:
    """Return serializable environment metadata."""
    info = env.get_info(include_tool_info=True)
    return {
        "domain_name": info.domain_name,
        "policy": info.policy,
        "tool_schemas": [
            {"name": fn.get("name", t.name), "parameters": fn.get("parameters", {})}
            for t in env.get_tools()
            for fn in [t.openai_schema.get("function", {})]
        ],
        "solo_mode": env.solo_mode,
    }


def set_state(env: Environment, db_data: dict) -> None:
    """Replace the environment's database state by updating the toolkit's DB."""
    env.tools.update_db(db_data)
    env.sync_tools()


def check_db(env: Environment, reference_db) -> bool:
    """Check if environment DB matches a reference."""
    return env.check_db(reference_db)
