Feature: Scenario validation catches authoring errors before evaluation
    scenario_validator.py validates scenario JSON files and rejects
    scenarios with structural errors that would cause confusing failures
    during evaluation.

    Scenario: Valid scenario passes validation
        Given a scenario with label "DENY" and a decision_equals outcome
        When I validate the scenario
        Then validation passes with no errors

    Scenario: Missing decision_equals is rejected
        Given a scenario with label "DENY" and no decision_equals outcome
        When I validate the scenario
        Then validation fails with error containing "Missing decision_equals"

    Scenario: Empty args_match on tool_called_with is rejected
        Given a scenario with a tool_called_with outcome with empty args_match
        When I validate the scenario
        Then validation fails with error containing "empty args_match"

    Scenario: Missing expected_answer on nl_assertion_llm_judge is rejected
        Given a scenario with an nl_assertion_llm_judge outcome missing expected_answer
        When I validate the scenario
        Then validation fails with error containing "missing expected_answer"

    Scenario: Invalid label is rejected
        Given a scenario with label "MAYBE" and a decision_equals outcome
        When I validate the scenario
        Then validation fails with error containing "Invalid label"

    Scenario: No outcomes is rejected
        Given a scenario with label "DENY" and no outcomes
        When I validate the scenario
        Then validation fails with error containing "No expected_outcomes"
