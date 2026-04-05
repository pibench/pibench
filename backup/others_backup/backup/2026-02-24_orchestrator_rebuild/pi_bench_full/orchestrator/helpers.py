"""Orchestrator helpers — shared utilities for env wrapping, snapshots, cost."""

import copy

from pi_bench.environment import get_db_hash


def unwrap_env(env: dict) -> dict:
    """If env is observer-wrapped, return the inner env. Otherwise return as-is."""
    if "env" in env and "observer" in env:
        return env["env"]
    return env


def is_observed(env: dict) -> bool:
    """Check if env is wrapped with an observer."""
    return "env" in env and "observer" in env


def snapshot_db(env: dict, trigger: str, turn_idx: int) -> dict:
    """Capture full DB state snapshot."""
    raw_env = unwrap_env(env)
    return {
        "trigger": trigger,
        "turn_idx": turn_idx,
        "db_hash": get_db_hash(raw_env),
        "db_state": copy.deepcopy(raw_env["db"]),
    }


def get_trajectory(state: dict) -> list[dict]:
    """Assign turn indices and return the ordered trajectory."""
    for i, msg in enumerate(state["trajectory"]):
        msg["turn_index"] = i
    return state["trajectory"]


def sum_cost(trajectory: list[dict], role: str) -> float:
    """Sum up costs for a specific role."""
    return sum(m.get("cost", 0.0) for m in trajectory if m.get("role") == role)
