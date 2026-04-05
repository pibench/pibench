#!/usr/bin/env python3
"""Convert expected_outcomes → evaluation_criteria in scenario JSON files.

Groups expected_outcomes entries into policy_checks, state_field_checks,
and nl_judge_checks, computes reward_basis, and replaces the key in-place.

Usage:
    python scripts/convert_outcomes_to_criteria.py --dry-run
    python scripts/convert_outcomes_to_criteria.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Types that map to each evaluation bucket
_POLICY_TYPES = {
    "tool_called",
    "tool_not_called",
    "tool_called_with",
    "tool_called_any",
    "tool_called_min_times",
    "tool_before_tool",
    "tool_before_tool_any",
    "decision_equals",
}

_STATE_FIELD_TYPES = {"state_field"}

_NL_JUDGE_TYPES = {"nl_assertion_llm_judge"}


def convert_outcome(outcome: dict) -> dict:
    """Convert a single outcome entry, renaming fields as needed."""
    converted = dict(outcome)
    # Rename args_match → arguments for tool_called_with
    if converted.get("type") == "tool_called_with" and "args_match" in converted:
        converted["arguments"] = converted.pop("args_match")
    return converted


def convert_scenario(scenario: dict) -> dict | None:
    """Convert a scenario's expected_outcomes to evaluation_criteria.

    Returns the modified scenario dict, or None if no conversion needed.
    """
    outcomes = scenario.get("expected_outcomes")
    if outcomes is None:
        return None
    if "evaluation_criteria" in scenario and scenario["evaluation_criteria"]:
        return None  # Already converted

    policy_checks = []
    state_field_checks = []
    nl_judge_checks = []

    for outcome in outcomes:
        otype = outcome.get("type", "")
        converted = convert_outcome(outcome)

        if otype in _POLICY_TYPES:
            policy_checks.append(converted)
        elif otype in _STATE_FIELD_TYPES:
            state_field_checks.append(converted)
        elif otype in _NL_JUDGE_TYPES:
            nl_judge_checks.append(converted)
        else:
            # Unknown type — put in policy_checks as fallback
            policy_checks.append(converted)

    # Compute reward_basis in priority order
    reward_basis = []
    if policy_checks:
        reward_basis.append("POLICY")
    if state_field_checks:
        reward_basis.append("STATE_FIELD")
    if nl_judge_checks:
        reward_basis.append("NL_JUDGE")

    evaluation_criteria: dict = {"reward_basis": reward_basis}
    if policy_checks:
        evaluation_criteria["policy_checks"] = policy_checks
    if state_field_checks:
        evaluation_criteria["state_field_checks"] = state_field_checks
    if nl_judge_checks:
        evaluation_criteria["nl_judge_checks"] = nl_judge_checks

    # Replace in scenario
    del scenario["expected_outcomes"]
    scenario["evaluation_criteria"] = evaluation_criteria
    return scenario


def find_scenarios(root: Path) -> list[Path]:
    """Find all pibench_scenario_v1 JSON files (excluding archive)."""
    paths = []
    for p in sorted(root.rglob("*.json")):
        if "archive" in p.parts:
            continue
        try:
            data = json.loads(p.read_text())
            if data.get("schema_version") == "pibench_scenario_v1":
                paths.append(p)
        except (json.JSONDecodeError, KeyError):
            continue
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert expected_outcomes to evaluation_criteria"
    )
    parser.add_argument(
        "--scenarios-dir",
        default="scenarios",
        help="Root directory for scenario files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without modifying files",
    )
    args = parser.parse_args()

    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_dir():
        print(f"Error: {scenarios_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    paths = find_scenarios(scenarios_dir)
    print(f"Found {len(paths)} scenario files")

    converted = 0
    skipped = 0
    for path in paths:
        data = json.loads(path.read_text())
        result = convert_scenario(data)
        if result is None:
            skipped += 1
            if args.dry_run:
                print(f"  SKIP {path.name} (no expected_outcomes or already converted)")
            continue

        converted += 1
        if args.dry_run:
            criteria = result["evaluation_criteria"]
            basis = criteria["reward_basis"]
            n_policy = len(criteria.get("policy_checks", []))
            n_state = len(criteria.get("state_field_checks", []))
            n_judge = len(criteria.get("nl_judge_checks", []))
            print(
                f"  CONVERT {path.name}: "
                f"reward_basis={basis}, "
                f"policy={n_policy}, state_field={n_state}, nl_judge={n_judge}"
            )
        else:
            path.write_text(json.dumps(result, indent=2) + "\n")
            print(f"  Converted {path.name}")

    print(f"\nDone: {converted} converted, {skipped} skipped")


if __name__ == "__main__":
    main()
