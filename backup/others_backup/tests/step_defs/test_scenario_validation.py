"""Step definitions for scenario_validation.feature."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from pi_bench.evaluator.scenario_validator import validate_scenario

scenarios("../features/scenario_validation.feature")


def _base_scenario(label="DENY", outcomes=None):
    """Build a minimal valid scenario dict."""
    if outcomes is None:
        outcomes = [
            {"outcome_id": "D1", "type": "decision_equals", "equals": label},
            {"outcome_id": "T1", "type": "tool_not_called", "tool_name": "process_refund"},
        ]
    return {
        "schema_version": "pibench_scenario_v1",
        "label": label,
        "expected_outcomes": outcomes,
    }


@pytest.fixture
def scenario_data():
    return {}


@pytest.fixture
def validation_errors():
    return []


# --- Given ---

@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and a decision_equals outcome'))
def scenario_with_decision(label, scenario_data):
    scenario_data.update(_base_scenario(label=label))
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and no decision_equals outcome'))
def scenario_without_decision(label, scenario_data):
    outcomes = [{"outcome_id": "T1", "type": "tool_not_called", "tool_name": "x"}]
    scenario_data.update(_base_scenario(label=label, outcomes=outcomes))
    return scenario_data


@given("a scenario with a tool_called_with outcome with empty args_match")
def scenario_empty_args(scenario_data):
    outcomes = [
        {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
        {"outcome_id": "T1", "type": "tool_called_with", "tool_name": "process_refund", "args_match": {}},
    ]
    scenario_data.update(_base_scenario(outcomes=outcomes))
    return scenario_data


@given("a scenario with an nl_assertion_llm_judge outcome missing expected_answer")
def scenario_missing_expected_answer(scenario_data):
    outcomes = [
        {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
        {"outcome_id": "NL1", "type": "nl_assertion_llm_judge", "judge_question": "Did the agent refuse?"},
    ]
    scenario_data.update(_base_scenario(outcomes=outcomes))
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and no outcomes'))
def scenario_no_outcomes(label, scenario_data):
    scenario_data.update(_base_scenario(label=label, outcomes=[]))
    return scenario_data


# --- When ---

@when("I validate the scenario", target_fixture="validation_errors")
def validate(scenario_data):
    return validate_scenario(scenario_data)


# --- Then ---

@then("validation passes with no errors")
def no_errors(validation_errors):
    assert validation_errors == [], f"Expected no errors, got: {validation_errors}"


@then(parsers.re(r'validation fails with error containing "(?P<substring>[^"]+)"'))
def has_error_containing(validation_errors, substring):
    assert validation_errors, "Expected validation errors but got none"
    joined = " | ".join(validation_errors)
    assert substring.lower() in joined.lower(), (
        f"Expected error containing '{substring}', got: {validation_errors}"
    )
