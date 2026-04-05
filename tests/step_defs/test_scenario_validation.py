"""Step definitions for scenario_validation.feature."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from pi_bench.evaluator.scenario_validator import validate_scenario

scenarios("../features/scenario_validation.feature")


def _base_scenario(label="DENY", evaluation_criteria=None):
    """Build a minimal valid scenario dict with evaluation_criteria."""
    if evaluation_criteria is None:
        evaluation_criteria = {
            "reward_basis": ["POLICY"],
            "policy_checks": [
                {"outcome_id": "D1", "type": "decision_equals", "equals": label},
                {"outcome_id": "T1", "type": "tool_not_called", "tool_name": "process_refund"},
            ],
        }
    return {
        "schema_version": "pibench_scenario_v1",
        "label": label,
        "evaluation_criteria": evaluation_criteria,
    }


@pytest.fixture
def scenario_data():
    return {}


@pytest.fixture
def validation_errors():
    return []


# --- Given ---

@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and valid evaluation_criteria'))
def scenario_with_criteria(label, scenario_data):
    scenario_data.update(_base_scenario(label=label))
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and policy_checks missing decision_equals'))
def scenario_without_decision(label, scenario_data):
    criteria = {
        "reward_basis": ["POLICY"],
        "policy_checks": [
            {"outcome_id": "T1", "type": "tool_not_called", "tool_name": "x"},
        ],
    }
    scenario_data.update(_base_scenario(label=label, evaluation_criteria=criteria))
    return scenario_data


@given("a scenario with a tool_called_with check with empty args")
def scenario_empty_args(scenario_data):
    criteria = {
        "reward_basis": ["POLICY"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
            {"outcome_id": "T1", "type": "tool_called_with", "tool_name": "process_refund", "arguments": {}},
        ],
    }
    scenario_data.update(_base_scenario(evaluation_criteria=criteria))
    return scenario_data


@given("a scenario with an nl_assertion_llm_judge check missing expected_answer")
def scenario_missing_expected_answer(scenario_data):
    criteria = {
        "reward_basis": ["POLICY", "NL_JUDGE"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
        ],
        "nl_judge_checks": [
            {"outcome_id": "NL1", "type": "nl_assertion_llm_judge", "judge_question": "Did the agent refuse?"},
        ],
    }
    scenario_data.update(_base_scenario(evaluation_criteria=criteria))
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and no evaluation_criteria'))
def scenario_no_criteria(label, scenario_data):
    scenario_data.update({
        "schema_version": "pibench_scenario_v1",
        "label": label,
    })
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and empty reward_basis'))
def scenario_empty_reward_basis(label, scenario_data):
    criteria = {"reward_basis": []}
    scenario_data.update(_base_scenario(label=label, evaluation_criteria=criteria))
    return scenario_data


@given(parsers.re(r'a scenario with label "(?P<label>[^"]+)" and POLICY basis but no policy_checks'))
def scenario_policy_no_checks(label, scenario_data):
    criteria = {"reward_basis": ["POLICY"]}
    scenario_data.update(_base_scenario(label=label, evaluation_criteria=criteria))
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


def test_rejects_conflicting_required_and_forbidden_tools():
    scenario = _base_scenario(evaluation_criteria={
        "reward_basis": ["POLICY"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
            {"outcome_id": "T1", "type": "tool_called", "tool_name": "reset_password"},
            {"outcome_id": "T2", "type": "tool_not_called", "tool_name": "reset_password"},
        ],
    })
    errors = validate_scenario(scenario)
    assert any("both required and forbidden" in e for e in errors)


def test_rejects_orphaned_ordering_check():
    scenario = _base_scenario(evaluation_criteria={
        "reward_basis": ["POLICY"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
            {"outcome_id": "O1", "type": "tool_before_tool", "first_tool": "lookup", "second_tool": "escalate"},
        ],
    })
    errors = validate_scenario(scenario)
    assert any("orphaned" in e for e in errors)


def test_rejects_decision_equals_label_mismatch():
    scenario = _base_scenario(label="DENY", evaluation_criteria={
        "reward_basis": ["POLICY"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "ALLOW"},
            {"outcome_id": "T1", "type": "tool_not_called", "tool_name": "process_refund"},
        ],
    })
    errors = validate_scenario(scenario)
    assert any("does not match scenario label" in e for e in errors)


def test_rejects_conflicting_state_field_checks():
    scenario = _base_scenario(evaluation_criteria={
        "reward_basis": ["POLICY", "STATE_FIELD"],
        "policy_checks": [
            {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
            {"outcome_id": "T1", "type": "tool_not_called", "tool_name": "process_refund"},
        ],
        "state_field_checks": [
            {"outcome_id": "S1", "type": "state_field", "field_path": "accounts[account_id=ACC1].status", "equals": "held"},
            {"outcome_id": "S2", "type": "state_field", "field_path": "accounts[account_id=ACC1].status", "equals": "open"},
        ],
    })
    errors = validate_scenario(scenario)
    assert any("conflicts with another check" in e for e in errors)


def test_accepts_well_formed_reference_trajectory():
    scenario = _base_scenario()
    scenario["reference_trajectory"] = {
        "tool_sequence": ["lookup_order", "record_decision"],
        "expected_decision": "DENY",
        "expected_state_changes": {
            "activity.pending_requests[request_id=REQ1].status": "denied",
        },
    }
    assert validate_scenario(scenario) == []
