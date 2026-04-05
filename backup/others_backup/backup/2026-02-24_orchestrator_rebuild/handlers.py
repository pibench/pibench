"""Handlers — generate messages and execute tool calls. No routing logic."""

import copy
from typing import Union

from pi_bench.environment import make_tool_call, get_tool_schemas, get_db_hash
from pi_bench.protocols import AgentProtocol, UserProtocol
from pi_bench.types import validate_message
from pi_bench.orchestrator.transitions import Role, Event, classify_event, classify_env_event
from pi_bench.orchestrator.helpers import unwrap_env, is_observed, snapshot_db


# --- Role names ---

ROLE_NAMES = {"agent": "assistant", "user": "user"}
STATE_KEYS = {"agent": "agent_state", "user": "user_state"}


def handle_generate(state: dict, protocol: Union[AgentProtocol, UserProtocol], role: Role) -> tuple[dict, Event]:
    """Handle agent or user message generation. Unified for both roles.

    Calls protocol.generate(), validates the result, appends to trajectory,
    and classifies the event. Does NOT decide the next routing target.

    Args:
        state: Current orchestrator state dict.
        protocol: Agent or user protocol with generate/is_stop methods.
        role: "agent" or "user".

    Returns:
        (state, event) where event is one of: "error", "stop",
        "tool_calls", "text_solo", "text".
    """
    role_name = ROLE_NAMES[role]
    state_key = STATE_KEYS[role]

    # Generate
    try:
        msg, new_role_state = protocol.generate(
            state["current_message"], state[state_key]
        )
    except Exception:
        return state, "error"

    # Validate
    if not validate_message(msg):
        return state, "error"

    # Update state
    state[state_key] = new_role_state
    state["trajectory"].append(msg)
    state["current_message"] = msg
    state["from_role"] = role_name

    # Classify
    event = classify_event(msg, role, protocol, state["solo"])
    return state, event


def handle_env(state: dict, env: dict) -> tuple[dict, Event]:
    """Handle tool call execution against the environment.

    Loops over tool_calls, executes each, constructs tool result message,
    appends to trajectory. Preserves observer trace and DB snapshot logic
    (these move to hooks in a later sprint).

    Args:
        state: Current orchestrator state dict.
        env: Environment dict (possibly observer-wrapped).

    Returns:
        (state, event) where event is "from_agent" or "from_user".
    """
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

    # Wrap results into a message
    if len(results) == 1:
        tool_msg = {"role": "tool", **results[0]}
    else:
        tool_msg = {
            "role": "multi_tool",
            "tool_messages": [{"role": "tool", **r} for r in results],
        }

    state["trajectory"].append(tool_msg)
    state["current_message"] = tool_msg

    # Sync tools — environment may have changed available tools
    state["tools"] = get_tool_schemas(raw_env)

    # Classify
    event = classify_env_event(requestor)
    return state, event
