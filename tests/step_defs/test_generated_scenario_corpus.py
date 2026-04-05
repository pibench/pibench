"""Corpus-level checks for checked-in scenario files."""

from __future__ import annotations

from pathlib import Path

import pytest

from pi_bench.evaluator.generated_scenario_checks import (
    validate_generated_scenario_file,
)
from pi_bench.scenario_loader import discover_scenarios

WORKSPACE = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = WORKSPACE / "scenarios"


@pytest.mark.parametrize(
    "scenario_path",
    discover_scenarios(SCENARIOS_DIR),
    ids=lambda p: p.stem,
)
def test_checked_in_scenarios_are_structurally_sound_and_tool_valid(
    scenario_path: Path,
):
    errors = validate_generated_scenario_file(scenario_path, WORKSPACE)
    assert errors == [], f"{scenario_path.name}: {errors}"
