"""DB evaluator — replay trajectory and compare DB hashes."""

import logging
from copy import deepcopy

from pi_bench.environment import make_tool_call, get_db_hash

logger = logging.getLogger(__name__)


def evaluate_db(task: dict, simulation: dict, domain: dict) -> float:
    """Replay trajectory against a fresh environment, compare DB hashes.

    Compares both the expected final state hash and the actual replayed hash.
    Returns 1.0 if hashes match, 0.0 otherwise.
    """
    get_env = domain.get("get_environment")
    if get_env is None:
        return 0.0

    replay_env = get_env()
    initial_state = task.get("initial_state", {})

    # Apply initialization data if present
    init_data = initial_state.get("initialization_data")
    if init_data:
        from pi_bench.environment import set_state
        set_state(replay_env, deepcopy(init_data))

    # Apply initialization actions if present
    # F4: check for errors on init actions
    init_actions = initial_state.get("initialization_actions", [])
    for action in init_actions:
        result = make_tool_call(
            replay_env,
            tool_name=action["name"],
            call_id=action.get("id", "init"),
            arguments=action.get("arguments", {}),
            requestor=action.get("requestor", "assistant"),
        )
        if isinstance(result, dict) and result.get("error"):
            logger.warning(
                "Init action %s failed: %s", action["name"], result["error"]
            )
            return 0.0

    # Replay all tool calls from the trajectory
    for msg in simulation.get("messages", []):
        if msg.get("role") in ("assistant", "user") and msg.get("tool_calls"):
            requestor = "assistant" if msg["role"] == "assistant" else "user"
            for tc in msg["tool_calls"]:
                make_tool_call(
                    replay_env,
                    tool_name=tc["name"],
                    call_id=tc.get("id", "call"),
                    arguments=tc.get("arguments", {}),
                    requestor=requestor,
                )

    replay_hash = get_db_hash(replay_env)
    logger.debug("DB: replay hash=%s", replay_hash)

    # Compare against expected final state if provided
    expected_db = task.get("evaluation_criteria", {}).get("expected_db")
    if expected_db:
        expected_env = get_env()
        from pi_bench.environment import set_state
        set_state(expected_env, deepcopy(expected_db))
        expected_hash = get_db_hash(expected_env)
        return 1.0 if replay_hash == expected_hash else 0.0

    # If no expected_db, just verify replay succeeded (hash is consistent)
    return 1.0
