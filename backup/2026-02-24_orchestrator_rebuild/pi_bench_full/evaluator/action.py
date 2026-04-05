"""ACTION evaluator — check expected tool calls appear in trajectory."""


def evaluate_actions(expected_actions: list[dict], trajectory: list[dict]) -> float:
    """Check that all expected tool calls appear in the trajectory.

    Matches by name + requestor + compared arguments.
    Returns 1.0 if all found, 0.0 if any missing.
    """
    if not expected_actions:
        return 1.0

    actual_calls = _extract_tool_calls(trajectory)

    matched = 0
    for expected in expected_actions:
        for actual in actual_calls:
            if _action_matches(expected, actual):
                matched += 1
                break

    return 1.0 if matched == len(expected_actions) else 0.0


def _extract_tool_calls(trajectory: list[dict]) -> list[dict]:
    """Extract all tool calls from a trajectory."""
    calls = []
    for msg in trajectory:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tc_with_role = dict(tc)
                tc_with_role["requestor"] = (
                    "assistant" if msg.get("role") == "assistant" else "user"
                )
                calls.append(tc_with_role)
    return calls


def _action_matches(expected: dict, actual: dict) -> bool:
    """Check if an actual tool call matches an expected action."""
    if expected.get("name") != actual.get("name"):
        return False
    if expected.get("requestor") != actual.get("requestor"):
        return False

    compare_keys = expected.get("compare_args")
    expected_args = expected.get("arguments", {})
    actual_args = actual.get("arguments", {})

    if compare_keys is None:
        return expected_args == actual_args
    else:
        for key in compare_keys:
            if expected_args.get(key) != actual_args.get(key):
                return False
        return True
