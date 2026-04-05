"""Orchestrator core — simulation loop and data-driven step."""

import time
import uuid

from pi_bench.protocols import AgentProtocol, UserProtocol
from pi_bench.orchestrator.init import init
from pi_bench.orchestrator.transitions import TRANSITIONS, TERMINATION_REASONS
from pi_bench.orchestrator.handlers import handle_generate, handle_env
from pi_bench.orchestrator.helpers import get_trajectory, sum_cost


# Handler dispatch table — maps role to (state, context) -> (state, event)
_HANDLERS = {
    "agent":       lambda state, ctx: handle_generate(state, ctx["agent"], "agent"),
    "user":        lambda state, ctx: handle_generate(state, ctx["user"], "user"),
    "environment": lambda state, ctx: handle_env(state, ctx["env"]),
}


def run(
    agent: AgentProtocol,
    user: UserProtocol | None,
    env: dict,
    task: dict,
    max_steps: int = 50,
    max_errors: int = 10,
    seed: int | None = None,
    solo: bool = False,
) -> dict:
    """Run a full simulation. Returns a SimulationRun dict."""
    start_time = time.time()

    state = init(agent, user, env, task, seed=seed, solo=solo)

    while not state["done"]:
        state = step(state, agent, user, env)
        if not state["done"]:
            state = _check_limits(state, max_steps, max_errors)

    # Cleanup
    try:
        agent.stop(state["current_message"], state["agent_state"])
    except Exception:
        pass
    if not solo and user is not None:
        try:
            user.stop(state["current_message"], state["user_state"])
        except Exception:
            pass

    end_time = time.time()
    trajectory = get_trajectory(state)

    return {
        "id": str(uuid.uuid4()),
        "task_id": task["id"],
        "start_time": start_time,
        "end_time": end_time,
        "duration": end_time - start_time,
        "termination_reason": state["termination_reason"],
        "messages": trajectory,
        "trial": state.get("trial", 0),
        "seed": state.get("seed"),
        "agent_cost": sum_cost(trajectory, "assistant"),
        "user_cost": sum_cost(trajectory, "user"),
        "step_count": state["step_count"],
        "agent_system_prompt": state.get("agent_system_prompt"),
        "user_system_prompt": state.get("user_system_prompt"),
        "db_snapshots": state.get("db_snapshots", []),
    }


def step(state: dict, agent: AgentProtocol, user: UserProtocol | None, env: dict) -> dict:
    """Execute one routing step. Data-driven via transition table.

    1. Look up handler for current role
    2. Call handler → get (state, event)
    3. Look up next role from transition table
    """
    role = state["to_role"]
    ctx = {"agent": agent, "user": user, "env": env}

    handler = _HANDLERS[role]
    state, event = handler(state, ctx)

    next_role = TRANSITIONS.get((role, event))
    if next_role is None:
        state["done"] = True
        state["termination_reason"] = TERMINATION_REASONS.get(
            (role, event), "unknown"
        )
    else:
        state["to_role"] = next_role

    state["step_count"] += 1
    return state


def _check_limits(state: dict, max_steps: int, max_errors: int) -> dict:
    """Check termination conditions. Only fires when to_role != environment."""
    if state["to_role"] == "environment":
        return state

    if state["step_count"] >= max_steps:
        state["done"] = True
        state["termination_reason"] = "max_steps"
    elif state["error_count"] >= max_errors:
        state["done"] = True
        state["termination_reason"] = "too_many_errors"

    return state
