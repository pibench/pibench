"""Tests for checked-in generator families."""

from pathlib import Path

from pi_bench.evaluator.generated_scenario_checks import (
    domain_tool_names_for_domain,
    validate_generated_scenario_structure,
    validate_generated_scenario_tools,
)
from pi_bench.evaluator.scenario_validator import validate_scenario
from pi_bench.generator.catalog import generate_helpdesk_admin_password_reset_batch

WORKSPACE = Path(__file__).resolve().parents[2]


def test_helpdesk_admin_password_reset_family_generates_valid_staged_batch():
    scenarios = generate_helpdesk_admin_password_reset_batch()
    assert len(scenarios) == 18

    valid_tools = domain_tool_names_for_domain("helpdesk_access_control_v1", WORKSPACE)

    columns = {scenario["leaderboard"]["primary"] for scenario in scenarios}
    assert "Procedural Compliance" in columns
    assert "Policy Activation" in columns
    assert "Escalation / Abstention" in columns

    for scenario in scenarios:
        assert validate_generated_scenario_structure(scenario) == []
        assert validate_generated_scenario_tools(scenario, valid_tools) == []
        assert validate_scenario(scenario) == []
        assert "generated" not in scenario["meta"]["notes"].lower()
        assert "Surface request sounds routine" in scenario["meta"]["notes"]
        assert "Authorization & Access Control" in scenario["leaderboard"]["subskills"]

    assert any(
        "board presentation" in scenario["user_simulation"]["initial_user_message"]
        for scenario in scenarios
    )
