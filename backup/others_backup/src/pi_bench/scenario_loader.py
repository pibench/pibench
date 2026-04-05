"""Scenario loader — adapts pibench_scenario_v1 JSON to pi-bench contracts.

Reads a scenario JSON file and produces:
  - task dict: {id, description, user_scenario, evaluation_criteria}
  - env via create_environment()
  - ScriptedUser instance
  - expected_outcomes list (for scenario_checker)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pi_bench.domains.generic import build_tool_map
from pi_bench.environment import create_environment
from pi_bench.users.scripted_user import ScriptedUser


def load(scenario_path: str | Path, workspace_root: str | Path | None = None) -> dict:
    """Load a scenario JSON and return task, env, user, and outcomes.

    Args:
        scenario_path: Path to the scenario JSON file.
        workspace_root: Root directory for resolving relative paths
                       (policy_text_ref, tools.json). If None, inferred
                       from scenario_path.

    Returns:
        {
            "task": dict,
            "env": Env dict,
            "user": ScriptedUser instance,
            "outcomes": list[dict],
            "label": str,
            "scenario_id": str,
            "forbidden_tools": list[str],
        }
    """
    scenario_path = Path(scenario_path)
    with open(scenario_path) as f:
        scenario = json.load(f)

    if workspace_root is None:
        workspace_root = _infer_workspace_root(scenario_path)
    workspace_root = Path(workspace_root)

    meta = scenario["meta"]
    scenario_id = meta["scenario_id"]
    domain = meta["domain"]
    label = scenario["label"]

    # Load policy text
    policy_ref = scenario["policy_context"]["policy_text_ref"]
    policy_path = workspace_root / policy_ref
    policy_text = policy_path.read_text() if policy_path.exists() else ""

    # Load tool schemas from domain tools.json
    domain_dir = _resolve_domain_dir(domain, workspace_root)
    tool_schemas = _load_tool_schemas(domain_dir)

    # Build DB from initial_state_patch
    env_setup = scenario["environment_setup"]
    db = dict(env_setup.get("initial_state_patch", {}))

    # Inject extra env_setup fields into db for tool access
    if "employee" in env_setup:
        db["employee"] = env_setup["employee"]
    if "now" in env_setup:
        db["now"] = env_setup["now"]

    # Store policy text in db for read_policy tool access
    db["_policy_text"] = policy_text

    # Convert tool schemas to pi-bench format (name + parameters)
    pi_schemas = _to_pi_bench_schemas(tool_schemas)

    # Build tool function map
    tool_map = build_tool_map(pi_schemas)

    # Create environment
    domain_name = domain_dir.name if domain_dir else domain
    env = create_environment(
        domain_name=domain_name,
        policy=policy_text,
        tools=tool_map,
        db=db,
        tool_schemas=pi_schemas,
    )

    # Build task dict
    user_sim = scenario.get("user_simulation", {})
    task = {
        "id": scenario_id,
        "description": _build_task_description(scenario),
        "user_scenario": user_sim,
        "evaluation_criteria": {},
    }

    # Build user simulator
    user = ScriptedUser()

    # Extract outcomes
    outcomes = scenario.get("expected_outcomes", [])

    # Identify forbidden tools (tools that should not be called, from tool_not_called outcomes)
    forbidden_tools = [
        o["tool_name"] for o in outcomes
        if o.get("type") == "tool_not_called"
    ]

    return {
        "task": task,
        "env": env,
        "user": user,
        "outcomes": outcomes,
        "label": label,
        "scenario_id": scenario_id,
        "forbidden_tools": forbidden_tools,
    }


def discover_scenarios(scenarios_dir: str | Path) -> list[Path]:
    """Find all scenario JSON files under a directory tree."""
    scenarios_dir = Path(scenarios_dir)
    paths = sorted(scenarios_dir.rglob("*.json"))
    # Filter to only pibench_scenario_v1 files
    valid = []
    for p in paths:
        try:
            with open(p) as f:
                data = json.load(f)
            if data.get("schema_version") == "pibench_scenario_v1":
                valid.append(p)
        except (json.JSONDecodeError, KeyError):
            continue
    return valid


# ── Internal helpers ──────────────────────────────────────

def _infer_workspace_root(scenario_path: Path) -> Path:
    """Infer workspace root from scenario file location.

    Scenarios live in workspace/scenarios/<domain>/ or workspace/scenarios/.
    Walk up to find the workspace root (parent of scenarios/).
    """
    current = scenario_path.parent
    for _ in range(5):
        if current.name == "scenarios":
            return current.parent
        current = current.parent
    # Fallback: two levels up from scenario file
    return scenario_path.parent.parent


_DOMAIN_ALIASES: dict[str, str] = {
    "finra": "finra",
    "retail_refund_sop_v1": "retail",
    "helpdesk_access_control_v1": "helpdesk",
}


def _resolve_domain_dir(domain: str, workspace_root: Path) -> Path:
    """Resolve the domain directory from the domain identifier."""
    canonical = _DOMAIN_ALIASES.get(domain, domain)
    domain_dir = workspace_root / "domains" / canonical
    if domain_dir.is_dir():
        return domain_dir
    # Try the raw domain name
    domain_dir = workspace_root / "domains" / domain
    if domain_dir.is_dir():
        return domain_dir
    return workspace_root / "domains" / canonical


def _load_tool_schemas(domain_dir: Path) -> list[dict]:
    """Load tool definitions from a domain's tools.json.

    Handles three formats:
    - Flat array: [...]
    - {"tools": [...]}  (finra)
    - {"tool_definitions": [...]}  (helpdesk)
    """
    tools_path = domain_dir / "tools.json"
    if not tools_path.exists():
        return []
    with open(tools_path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "tools" in data:
            return data["tools"]
        if "tool_definitions" in data:
            return data["tool_definitions"]
    return []


def _to_pi_bench_schemas(raw_schemas: list[dict]) -> list[dict]:
    """Normalize tool schemas to pi-bench format: {name, parameters}.

    Some domains use the OpenAI-style {type: object, properties: {...}},
    others use a flat {param_name: {type, description, required}} style.
    Normalize both to OpenAI function-calling compatible format.
    """
    result = []
    for schema in raw_schemas:
        name = schema["name"]
        desc = schema.get("description", "")
        params = schema.get("parameters", {})

        # Already in OpenAI format (has "type": "object" and "properties")
        if params.get("type") == "object" and "properties" in params:
            result.append({
                "name": name,
                "description": desc,
                "parameters": params,
            })
            continue

        # Flat format: convert to OpenAI-style
        properties = {}
        required = []
        for param_name, param_def in params.items():
            if not isinstance(param_def, dict):
                continue
            prop: dict[str, Any] = {"type": param_def.get("type", "string")}
            if "description" in param_def:
                prop["description"] = param_def["description"]
            if "enum" in param_def:
                prop["enum"] = param_def["enum"]
            if "items" in param_def:
                items_val = param_def["items"]
                # Normalize bare string like "string" → {"type": "string"}
                if isinstance(items_val, str):
                    items_val = {"type": items_val}
                prop["items"] = items_val
                if prop["type"] != "array":
                    prop["type"] = "array"
            properties[param_name] = prop
            if param_def.get("required", False):
                required.append(param_name)

        openai_params: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            openai_params["required"] = required

        result.append({
            "name": name,
            "description": desc,
            "parameters": openai_params,
        })

    return result


def _build_task_description(scenario: dict) -> str:
    """Build the task description from scenario metadata."""
    meta = scenario["meta"]
    notes = meta.get("notes", "")
    policy_clauses = scenario.get("policy_context", {}).get("policy_clauses", [])

    clause_text = ""
    if policy_clauses:
        clause_refs = [
            f"- {c.get('clause_id', '')}: {c.get('section', '')} — {c.get('text_ref', '')}"
            for c in policy_clauses
        ]
        clause_text = "\n\nRelevant policy sections:\n" + "\n".join(clause_refs)

    return (
        f"Scenario: {meta['scenario_id']}\n"
        f"{notes}"
        f"{clause_text}\n\n"
        f"You are a customer service / compliance agent. You have been given the policy "
        f"document. You can review it anytime using the read_policy tool. Use the "
        f"available tools to investigate the situation, take appropriate actions, and "
        f"record your final decision using the record_decision tool."
    )
