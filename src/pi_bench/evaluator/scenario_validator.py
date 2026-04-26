"""Scenario validation — structural checks on scenario JSON files.

Validates that scenario evaluation_criteria are well-formed before running
evaluation. Catches common authoring errors early rather than producing
confusing failures at evaluation time.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_VALID_LABELS = {"ALLOW", "ALLOW-CONDITIONAL", "DENY", "ESCALATE"}
_VALID_REWARD_BASIS = {
    "ACTION",
    "COMMUNICATE",
    "DB",
    "ENV_ASSERTION",
    "NL_ASSERTION",
    "NL_JUDGE",
    "POLICY",
    "STATE_FIELD",
}
_HARD_REWARD_BASIS = {
    "ACTION",
    "COMMUNICATE",
    "DB",
    "ENV_ASSERTION",
    "POLICY",
    "STATE_FIELD",
}

_TIER1_TYPES = {
    "tool_called",
    "tool_not_called",
    "tool_called_with",
    "tool_called_any",
    "tool_called_min_times",
    "tool_before_tool",
    "tool_before_tool_any",
    "decision_equals",
    "state_field",
}

_TIER2_TYPES = {"nl_assertion_llm_judge"}

_ALL_TYPES = _TIER1_TYPES | _TIER2_TYPES

_POLICY_CHECK_TYPES = {
    "tool_called", "tool_not_called", "tool_called_with", "tool_called_any",
    "tool_called_min_times", "tool_before_tool", "tool_before_tool_any",
    "decision_equals", "message_not_contains", "escalation_attempted",
}

_BRACKET_RE = re.compile(r"^(\w+)\[(\w+)=([^\]]+)\]$")


def validate_scenario(scenario: dict) -> list[str]:
    """Validate a scenario dict. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    # Label check
    label = scenario.get("expected_label", scenario.get("label", ""))
    if label not in _VALID_LABELS:
        errors.append(f"Invalid label '{label}': must be one of {_VALID_LABELS}")

    # Support both new evaluation_criteria and legacy expected_outcomes
    criteria = scenario.get("evaluation_criteria")
    if criteria:
        errors.extend(_validate_evaluation_criteria(criteria, label=label))
    else:
        # Fall back to legacy expected_outcomes validation
        outcomes = scenario.get("expected_outcomes", [])
        if not outcomes:
            errors.append("No evaluation_criteria defined")
            return errors
        errors.extend(_validate_legacy_outcomes(outcomes))

    reference_trajectory = scenario.get("reference_trajectory")
    if reference_trajectory:
        errors.extend(_validate_reference_trajectory(reference_trajectory, label))

    return errors


def _validate_evaluation_criteria(criteria: dict, label: str | None = None) -> list[str]:
    """Validate the evaluation_criteria structure."""
    errors: list[str] = []

    reward_basis = criteria.get("reward_basis", [])
    if not reward_basis:
        errors.append("Empty reward_basis in evaluation_criteria")
        return errors

    unknown_basis = [basis for basis in reward_basis if basis not in _VALID_REWARD_BASIS]
    for basis in unknown_basis:
        errors.append(f"Unknown reward_basis entry '{basis}'")

    # Validate each reward_basis type has corresponding checks
    if "POLICY" in reward_basis:
        policy_checks = criteria.get("policy_checks", [])
        if not policy_checks:
            errors.append("POLICY in reward_basis but no policy_checks defined")
        else:
            decision_checks = [c for c in policy_checks if c.get("type") == "decision_equals"]
            if not decision_checks:
                errors.append("Missing decision_equals in policy_checks — every scenario must have one")
            elif len(decision_checks) > 1:
                errors.append("Multiple decision_equals checks in policy_checks — exactly one required")
            elif label is not None and decision_checks[0].get("equals") != label:
                errors.append(
                    "decision_equals does not match scenario label "
                    f"('{decision_checks[0].get('equals')}' vs '{label}')"
                )
            # Per-check validation
            for i, check in enumerate(policy_checks):
                errors.extend(_validate_check(check, i))
            errors.extend(_validate_policy_consistency(policy_checks))

    if "STATE_FIELD" in reward_basis:
        state_checks = criteria.get("state_field_checks", [])
        if not state_checks:
            errors.append("STATE_FIELD in reward_basis but no state_field_checks defined")
        else:
            for i, check in enumerate(state_checks):
                errors.extend(_validate_check(check, i))
            errors.extend(_validate_state_checks(state_checks))

    if "NL_JUDGE" in reward_basis:
        nl_checks = criteria.get("nl_judge_checks", [])
        if not nl_checks:
            errors.append("NL_JUDGE in reward_basis but no nl_judge_checks defined")
        else:
            for i, check in enumerate(nl_checks):
                errors.extend(_validate_check(check, i))

    if "ACTION" in reward_basis:
        expected_actions = criteria.get("expected_actions", [])
        if not expected_actions:
            errors.append("ACTION in reward_basis but no expected_actions defined")
        elif not isinstance(expected_actions, list):
            errors.append("expected_actions must be a list")
        else:
            for i, action in enumerate(expected_actions):
                if not isinstance(action, dict):
                    errors.append(f"expected_actions[{i}] must be an object")
                    continue
                if not action.get("name"):
                    errors.append(f"expected_actions[{i}] missing required 'name'")

    if "DB" in reward_basis:
        expected_db = criteria.get("expected_db")
        if not isinstance(expected_db, dict) or not expected_db:
            errors.append("DB in reward_basis but expected_db is missing or empty")

    if "COMMUNICATE" in reward_basis:
        communicate_info = criteria.get("communicate_info", [])
        if not isinstance(communicate_info, list) or not communicate_info:
            errors.append("COMMUNICATE in reward_basis but no communicate_info defined")
        elif not all(isinstance(item, str) and item.strip() for item in communicate_info):
            errors.append("communicate_info must be a non-empty list of strings")

    if "ENV_ASSERTION" in reward_basis:
        env_assertions = criteria.get("env_assertions", [])
        if not isinstance(env_assertions, list) or not env_assertions:
            errors.append("ENV_ASSERTION in reward_basis but no env_assertions defined")
        elif not all(isinstance(item, dict) for item in env_assertions):
            errors.append("env_assertions must be a non-empty list of objects")

    if "NL_ASSERTION" in reward_basis:
        nl_assertions = criteria.get("nl_assertions", [])
        if not isinstance(nl_assertions, list) or not nl_assertions:
            errors.append("NL_ASSERTION in reward_basis but no nl_assertions defined")
        elif not all(isinstance(item, str) and item.strip() for item in nl_assertions):
            errors.append("nl_assertions must be a non-empty list of strings")

    if not any(basis in _HARD_REWARD_BASIS for basis in reward_basis):
        errors.append("No Tier 1 (deterministic) checks — at least one required")

    return errors


def _validate_policy_consistency(policy_checks: list[dict]) -> list[str]:
    """Validate cross-check consistency for policy checks."""
    errors: list[str] = []

    required_tools = {
        c.get("tool_name")
        for c in policy_checks
        if c.get("type") in {"tool_called", "tool_called_with", "tool_called_min_times"}
        and c.get("tool_name")
    }
    forbidden_tools = {
        c.get("tool_name")
        for c in policy_checks
        if c.get("type") == "tool_not_called" and c.get("tool_name")
    }

    for tool_name in sorted(required_tools & forbidden_tools):
        errors.append(
            f"Conflicting checks for tool '{tool_name}': both required and forbidden"
        )

    for check in policy_checks:
        otype = check.get("type")
        oid = check.get("outcome_id", "unknown")

        if otype == "tool_called_any":
            tool_names = [t for t in check.get("tool_names", []) if t]
            if tool_names and all(t in forbidden_tools for t in tool_names):
                errors.append(
                    f"{oid}: tool_called_any is impossible because all candidate tools are forbidden"
                )

        if otype == "tool_before_tool":
            first = check.get("first_tool", check.get("first", ""))
            second = check.get("second_tool", check.get("second", ""))
            if first and first not in required_tools:
                errors.append(
                    f"{oid}: tool_before_tool orphaned — first tool '{first}' is not otherwise required"
                )
            if second and second not in required_tools:
                errors.append(
                    f"{oid}: tool_before_tool orphaned — second tool '{second}' is not otherwise required"
                )

        if otype == "tool_before_tool_any":
            first_tools = [t for t in check.get("first_tools", []) if t]
            second = check.get("second_tool", "")
            if first_tools and not any(t in required_tools for t in first_tools):
                errors.append(
                    f"{oid}: tool_before_tool_any orphaned — none of the first_tools are otherwise required"
                )
            if second and second not in required_tools:
                errors.append(
                    f"{oid}: tool_before_tool_any orphaned — second tool '{second}' is not otherwise required"
                )

    return errors


def _validate_state_checks(state_checks: list[dict]) -> list[str]:
    """Validate cross-check consistency for state checks."""
    errors: list[str] = []
    seen: dict[str, object] = {}

    for check in state_checks:
        oid = check.get("outcome_id", "unknown")
        field_path = check.get("field_path", "")
        expected = check.get("equals")

        if field_path:
            for segment in field_path.split("."):
                if not segment:
                    errors.append(f"{oid}: state_field has empty path segment in '{field_path}'")
                    break
                if "[" in segment and not _BRACKET_RE.match(segment):
                    errors.append(
                        f"{oid}: state_field has unsupported bracket segment '{segment}'"
                    )
                    break

        if field_path in seen and seen[field_path] != expected:
            errors.append(
                f"{oid}: state_field conflicts with another check on '{field_path}'"
            )
        elif field_path:
            seen[field_path] = expected

    return errors


def _validate_reference_trajectory(reference_trajectory: dict, label: str) -> list[str]:
    """Validate optional authoring-time reference trajectory structure."""
    errors: list[str] = []

    tool_sequence = reference_trajectory.get("tool_sequence", [])
    if not isinstance(tool_sequence, list) or not all(isinstance(t, str) and t for t in tool_sequence):
        errors.append("reference_trajectory.tool_sequence must be a non-empty list of tool names")
    elif not tool_sequence:
        errors.append("reference_trajectory.tool_sequence must not be empty")

    expected_decision = reference_trajectory.get("expected_decision")
    if expected_decision is not None and expected_decision != label:
        errors.append(
            "reference_trajectory.expected_decision does not match scenario label "
            f"('{expected_decision}' vs '{label}')"
        )

    expected_state_changes = reference_trajectory.get("expected_state_changes", {})
    if expected_state_changes and not isinstance(expected_state_changes, dict):
        errors.append("reference_trajectory.expected_state_changes must be an object")

    return errors


def _validate_check(check: dict, index: int) -> list[str]:
    """Validate a single check entry."""
    errors: list[str] = []
    oid = check.get("outcome_id", f"check[{index}]")
    otype = check.get("type", "")

    if otype not in _ALL_TYPES and otype not in _POLICY_CHECK_TYPES:
        errors.append(f"{oid}: unknown check type '{otype}'")
        return errors

    if otype == "tool_called_with":
        args = check.get("arguments", check.get("args_match", check.get("args", {})))
        if not args:
            errors.append(
                f"{oid}: tool_called_with has empty args — "
                "use tool_called if no args needed"
            )

    if otype == "nl_assertion_llm_judge":
        if not check.get("expected_answer"):
            errors.append(f"{oid}: nl_assertion_llm_judge missing expected_answer")
        if not check.get("judge_question"):
            errors.append(f"{oid}: nl_assertion_llm_judge missing judge_question")

    if otype == "decision_equals":
        if "equals" not in check:
            errors.append(f"{oid}: decision_equals missing 'equals' value")

    if otype == "state_field":
        if not check.get("field_path"):
            errors.append(f"{oid}: state_field missing field_path")
        if "equals" not in check:
            errors.append(f"{oid}: state_field missing 'equals' value")

    if otype == "tool_called_min_times":
        min_times = check.get("min_times", 0)
        if not isinstance(min_times, int) or min_times < 1:
            errors.append(f"{oid}: tool_called_min_times requires min_times >= 1")

    return errors


def _validate_legacy_outcomes(outcomes: list[dict]) -> list[str]:
    """Validate legacy expected_outcomes format (backward compat)."""
    errors: list[str] = []

    tier1_outcomes = [o for o in outcomes if o.get("type", "") in _TIER1_TYPES]
    if not tier1_outcomes:
        errors.append("No Tier 1 (deterministic) outcomes — at least one required")

    has_decision = any(o.get("type") == "decision_equals" for o in outcomes)
    if not has_decision:
        errors.append("Missing decision_equals outcome — every scenario must have one")

    for i, outcome in enumerate(outcomes):
        errors.extend(_validate_check(outcome, i))

    return errors


def validate_scenario_file(path: Path) -> list[str]:
    """Validate a scenario JSON file. Returns list of error strings."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return [f"Cannot read scenario file: {exc}"]

    if data.get("schema_version") != "pibench_scenario_v1":
        return [f"Not a pibench_scenario_v1 file: {path.name}"]

    return validate_scenario(data)


def validate_all(scenarios_dir: Path) -> dict[str, list[str]]:
    """Validate all scenario files in a directory.

    Returns:
        Dict mapping scenario filename to list of errors.
        Only files with errors are included.
    """
    results: dict[str, list[str]] = {}

    for path in sorted(scenarios_dir.rglob("*.json")):
        errors = validate_scenario_file(path)
        if errors:
            results[path.name] = errors

    return results
