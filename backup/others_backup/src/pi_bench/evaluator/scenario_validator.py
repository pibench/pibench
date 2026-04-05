"""Scenario validation — structural checks on scenario JSON files.

Validates that scenario outcomes are well-formed before running evaluation.
Catches common authoring errors early rather than producing confusing
failures at evaluation time.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_VALID_LABELS = {"ALLOW", "ALLOW-CONDITIONAL", "DENY", "ESCALATE"}

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


def validate_scenario(scenario: dict) -> list[str]:
    """Validate a scenario dict. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    # Label check
    label = scenario.get("expected_label", scenario.get("label", ""))
    if label not in _VALID_LABELS:
        errors.append(f"Invalid label '{label}': must be one of {_VALID_LABELS}")

    # Outcomes check
    outcomes = scenario.get("expected_outcomes", [])
    if not outcomes:
        errors.append("No expected_outcomes defined")
        return errors

    # Must have at least one Tier 1 outcome
    tier1_outcomes = [o for o in outcomes if o.get("type", "") in _TIER1_TYPES]
    if not tier1_outcomes:
        errors.append("No Tier 1 (deterministic) outcomes — at least one required")

    # Must have decision_equals
    has_decision = any(o.get("type") == "decision_equals" for o in outcomes)
    if not has_decision:
        errors.append("Missing decision_equals outcome — every scenario must have one")

    # Per-outcome validation
    for i, outcome in enumerate(outcomes):
        oid = outcome.get("outcome_id", f"outcome[{i}]")
        otype = outcome.get("type", "")

        if otype not in _ALL_TYPES:
            errors.append(f"{oid}: unknown outcome type '{otype}'")
            continue

        # tool_called_with: must have non-empty args
        if otype == "tool_called_with":
            args = outcome.get("args_match", outcome.get("args", {}))
            if not args:
                errors.append(
                    f"{oid}: tool_called_with has empty args_match — "
                    "use tool_called if no args needed"
                )

        # nl_assertion_llm_judge: must have expected_answer
        if otype == "nl_assertion_llm_judge":
            if not outcome.get("expected_answer"):
                errors.append(
                    f"{oid}: nl_assertion_llm_judge missing expected_answer"
                )
            if not outcome.get("judge_question"):
                errors.append(
                    f"{oid}: nl_assertion_llm_judge missing judge_question"
                )

        # decision_equals: must have equals
        if otype == "decision_equals":
            if "equals" not in outcome:
                errors.append(f"{oid}: decision_equals missing 'equals' value")

        # state_field: must have field_path and equals
        if otype == "state_field":
            if not outcome.get("field_path"):
                errors.append(f"{oid}: state_field missing field_path")
            if "equals" not in outcome:
                errors.append(f"{oid}: state_field missing 'equals' value")

        # tool_called_min_times: must have min_times > 0
        if otype == "tool_called_min_times":
            min_times = outcome.get("min_times", 0)
            if not isinstance(min_times, int) or min_times < 1:
                errors.append(
                    f"{oid}: tool_called_min_times requires min_times >= 1"
                )

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
