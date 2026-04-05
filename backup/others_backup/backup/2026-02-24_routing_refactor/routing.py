"""Orchestrator routing — route messages to agent, user, or environment."""

import copy
from typing import Any

from pi_bench.environment import make_tool_call, get_tool_schemas, get_db_hash
from pi_bench.types import is_stop_signal, validate_message
from pi_bench.orchestrator.helpers import unwrap_env, is_observed, snapshot_db


def route_to_agent(state: dict, agent: Any) -> dict:
    """Route current message to the agent."""
    try:
        msg, agent_state = agent.generate(state["current_message"], state["agent_state"])
    except Exception:
        state["done"] = True
        state["termination_reason"] = "agent_error"
        return state

    if not validate_message(msg):
        state["done"] = True
        state["termination_reason"] = "agent_error"
        return state

    state["agent_state"] = agent_state
    state["trajectory"].append(msg)
    state["current_message"] = msg
    state["from_role"] = "assistant"

    if agent.is_stop(msg) or is_stop_signal(msg):
        state["done"] = True
        state["termination_reason"] = "agent_stop"
    elif msg.get("tool_calls"):
        state["to_role"] = "environment"
    elif state["solo"]:
        state["to_role"] = "agent"
    else:
        state["to_role"] = "user"

    return state


def route_to_user(state: dict, user: Any) -> dict:
    """Route current message to the user."""
    try:
        msg, user_state = user.generate(state["current_message"], state["user_state"])
    except Exception:
        state["done"] = True
        state["termination_reason"] = "user_error"
        return state

    if not validate_message(msg):
        state["done"] = True
        state["termination_reason"] = "user_error"
        return state

    state["user_state"] = user_state
    state["trajectory"].append(msg)
    state["current_message"] = msg
    state["from_role"] = "user"

    if user.is_stop(msg) or is_stop_signal(msg):
        state["done"] = True
        state["termination_reason"] = "user_stop"
    elif msg.get("tool_calls"):
        state["to_role"] = "environment"
    else:
        state["to_role"] = "agent"

    return state


def route_to_env(state: dict, env: dict) -> dict:
    """Route tool calls to the environment, return results to caller."""
    msg = state["current_message"]
    tool_calls = msg.get("tool_calls", [])
    requestor = state["from_role"]
    requestor_str = "assistant" if requestor == "assistant" else "user"
    raw_env = unwrap_env(env)
    observed = is_observed(env)

    results = []
    for tc in tool_calls:
        # Capture pre-state hash for observer
        pre_hash = ""
        if observed:
            pre_hash = get_db_hash(raw_env)

        result = make_tool_call(
            raw_env,
            tool_name=tc["name"],
            call_id=tc.get("id", "call"),
            arguments=tc.get("arguments", {}),
            requestor=requestor_str,
        )
        result["name"] = tc["name"]
        if result.get("error"):
            state["error_count"] += 1
        results.append(result)

        # Record in observer trace if present
        if observed:
            trace = env.get("trace")
            if trace is not None:
                post_hash = get_db_hash(raw_env)
                db_state = copy.deepcopy(raw_env["db"])
                trace.record(
                    tool_name=tc["name"],
                    arguments=tc.get("arguments", {}),
                    result_content=result.get("content", ""),
                    result_error=result.get("error", False),
                    pre_state_hash=pre_hash,
                    post_state_hash=post_hash,
                    requestor=requestor_str,
                    db_state=db_state,
                )

        # DB snapshot after every tool call
        turn_idx = len(state["trajectory"])
        state.setdefault("db_snapshots", []).append(
            snapshot_db(env, f"tool:{tc['name']}", turn_idx)
        )

    # Wrap results
    if len(results) == 1:
        tool_msg = {
            "role": "tool",
            **results[0],
        }
    else:
        tool_msg = {
            "role": "multi_tool",
            "tool_messages": [{"role": "tool", **r} for r in results],
        }

    state["trajectory"].append(tool_msg)
    state["current_message"] = tool_msg

    # Sync tools — environment may have changed available tools
    state["tools"] = get_tool_schemas(raw_env)

    # Route back to whoever made the calls
    if requestor == "assistant":
        state["to_role"] = "agent"
    else:
        state["to_role"] = "user"

    return state
