"""Mock domain — minimal domain for testing the environment layer."""

from copy import deepcopy
from pathlib import Path

from pi_bench.environment import ToolSchema, create_environment

_DOMAIN_DIR = Path(__file__).parent
_POLICY_PATH = _DOMAIN_DIR / "policy.md"


def _load_policy() -> str:
    """Load the default mock policy from policy.md."""
    return _POLICY_PATH.read_text()

INITIAL_DB = {
    "users": {
        "user_1": {"name": "Test User", "tasks": ["task_1"]},
        "user_2": {"name": "Another User", "tasks": []},
    },
    "tasks": {
        "task_1": {
            "title": "Test task",
            "status": "pending",
            "user_id": "user_1",
        },
    },
    "next_task_id": 2,
}

TOOL_SCHEMAS: list[ToolSchema] = [
    {
        "name": "get_users",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_task",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The ID of the user"},
                "title": {"type": "string", "description": "The title of the task"},
                "description": {"type": "string", "description": "Optional description"},
            },
            "required": ["user_id", "title"],
        },
    },
    {
        "name": "update_task_status",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The ID of the task"},
                "status": {"type": "string", "enum": ["pending", "completed"]},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "transfer_to_human_agents",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Summary of the issue"},
            },
            "required": ["summary"],
        },
    },
    {
        "name": "export_records",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]


# --- Agent tools ---


def get_users(db: dict) -> list[dict]:
    """Get all users."""
    return [
        {"user_id": uid, "name": data["name"], "tasks": data["tasks"]}
        for uid, data in db["users"].items()
    ]


def create_task(db: dict, user_id: str, title: str, description: str = "") -> dict:
    """Create a new task for a user."""
    if user_id not in db["users"]:
        raise ValueError(f"User '{user_id}' not found.")
    task_id = f"task_{db['next_task_id']}"
    db["next_task_id"] += 1
    task = {"title": title, "status": "pending", "user_id": user_id}
    if description:
        task["description"] = description
    db["tasks"][task_id] = task
    db["users"][user_id]["tasks"].append(task_id)
    return {"task_id": task_id, **task}


def update_task_status(db: dict, task_id: str, status: str) -> dict:
    """Update the status of a task."""
    if task_id not in db["tasks"]:
        raise ValueError(f"Task '{task_id}' not found.")
    if status not in ("pending", "completed"):
        raise ValueError(f"Invalid status '{status}'. Must be 'pending' or 'completed'.")
    db["tasks"][task_id]["status"] = status
    return {"task_id": task_id, **db["tasks"][task_id]}


def transfer_to_human_agents(db: dict, summary: str) -> str:
    """Transfer to a human agent with a summary."""
    return "Transfer successful"


def export_records(db: dict) -> list[dict]:
    """Export all records (used as 'forbidden' tool in DENY scenarios)."""
    return [
        {"user_id": uid, **data}
        for uid, data in db["users"].items()
    ]


# --- User-only tools ---


def user_only_tool(db: dict) -> str:
    """A tool only available to user requestors."""
    return "user only result"


# --- Factories ---


AGENT_TOOLS = {
    "get_users": get_users,
    "create_task": create_task,
    "update_task_status": update_task_status,
    "transfer_to_human_agents": transfer_to_human_agents,
    "export_records": export_records,
}

USER_TOOLS = {
    "get_users": get_users,
    "user_only_tool": user_only_tool,
}


def get_environment(policy: str | None = None) -> dict:
    """Create a fresh mock environment, optionally with a custom policy."""
    return create_environment(
        domain_name="mock",
        policy=policy if policy is not None else _load_policy(),
        tools=AGENT_TOOLS,
        db=deepcopy(INITIAL_DB),
        tool_schemas=TOOL_SCHEMAS,
    )


def get_environment_with_user_tools() -> dict:
    """Create a mock environment with both agent and user tool collections."""
    return create_environment(
        domain_name="mock",
        policy=_load_policy(),
        tools=AGENT_TOOLS,
        user_tools=USER_TOOLS,
        db=deepcopy(INITIAL_DB),
        tool_schemas=TOOL_SCHEMAS,
    )
