"""Retail domain — BrightMart returns/refunds/exchange environment.

Delegates tool execution to the generic handler infrastructure.
Provides get_environment() for the runner API path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pi_bench.domains.generic import build_tool_map
from pi_bench.environment import ToolSchema, create_environment


# ── Resolve workspace paths ──────────────────────────────

def _workspace_root() -> Path:
    """Find the workspace root (parent of domains/)."""
    # Walk up from this file to find the workspace root
    here = Path(__file__).resolve().parent
    for ancestor in [here] + list(here.parents):
        if (ancestor / "domains" / "retail" / "policy.md").exists():
            return ancestor
    # Fallback: 4 levels up from src/pi_bench/domains/retail/
    return here.parents[3]


def _load_policy() -> str:
    return (_workspace_root() / "domains" / "retail" / "policy.md").read_text()


def _load_raw_schemas() -> list[dict]:
    tools_path = _workspace_root() / "domains" / "retail" / "tools.json"
    with open(tools_path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("tools", data.get("tool_definitions", []))
    return []


def _normalize_schemas(raw: list[dict]) -> list[ToolSchema]:
    """Normalize to pi-bench format {name, description, parameters}."""
    result = []
    for schema in raw:
        name = schema["name"]
        desc = schema.get("description", "")
        params = schema.get("parameters", {})
        if params.get("type") == "object" and "properties" in params:
            result.append({"name": name, "description": desc, "parameters": params})
            continue
        # Flat format → OpenAI-style
        properties: dict[str, Any] = {}
        required = []
        for pname, pdef in params.items():
            if not isinstance(pdef, dict):
                continue
            prop: dict[str, Any] = {"type": pdef.get("type", "string")}
            if "description" in pdef:
                prop["description"] = pdef["description"]
            if "enum" in pdef:
                prop["enum"] = pdef["enum"]
            if "items" in pdef:
                items_val = pdef["items"]
                if isinstance(items_val, str):
                    items_val = {"type": items_val}
                prop["items"] = items_val
                if prop["type"] != "array":
                    prop["type"] = "array"
            properties[pname] = prop
            if pdef.get("required", False):
                required.append(pname)
        oai: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            oai["required"] = required
        result.append({"name": name, "description": desc, "parameters": oai})
    return result


# ── Public API ────────────────────────────────────────────

TOOL_SCHEMAS: list[ToolSchema] = _normalize_schemas(_load_raw_schemas())
AGENT_TOOLS = build_tool_map(TOOL_SCHEMAS)


def get_environment(
    scenario: dict | None = None,
    policy: str | None = None,
) -> dict:
    """Create a retail environment, optionally seeded from a scenario."""
    if scenario is not None:
        env_setup = scenario.get("environment_setup", {})
        db: dict[str, Any] = dict(env_setup.get("initial_state_patch", {}))
        if "employee" in env_setup:
            db["employee"] = env_setup["employee"]
        if "now" in env_setup:
            db["now"] = env_setup["now"]
    else:
        db = {
            "orders": [],
            "customer_profile": {},
            "decisions": [],
        }

    return create_environment(
        domain_name="retail",
        policy=policy or _load_policy(),
        tools=AGENT_TOOLS,
        db=db,
        tool_schemas=TOOL_SCHEMAS,
    )
