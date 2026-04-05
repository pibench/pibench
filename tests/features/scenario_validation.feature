Feature: Scenario validation catches authoring errors before evaluation
    scenario_validator.py validates scenario JSON files and rejects
    scenarios with structural errors that would cause confusing failures
    during evaluation.

    Scenario: Valid scenario with evaluation_criteria passes validation
        Given a scenario with label "DENY" and valid evaluation_criteria
        When I validate the scenario
        Then validation passes with no errors

    Scenario: Missing decision_equals in policy_checks is rejected
        Given a scenario with label "DENY" and policy_checks missing decision_equals
        When I validate the scenario
        Then validation fails with error containing "Missing decision_equals"

    Scenario: Empty args on tool_called_with is rejected
        Given a scenario with a tool_called_with check with empty args
        When I validate the scenario
        Then validation fails with error containing "empty args"

    Scenario: Missing expected_answer on nl_assertion_llm_judge is rejected
        Given a scenario with an nl_assertion_llm_judge check missing expected_answer
        When I validate the scenario
        Then validation fails with error containing "missing expected_answer"

    Scenario: Invalid label is rejected
        Given a scenario with label "MAYBE" and valid evaluation_criteria
        When I validate the scenario
        Then validation fails with error containing "Invalid label"

    Scenario: No evaluation_criteria is rejected
        Given a scenario with label "DENY" and no evaluation_criteria
        When I validate the scenario
        Then validation fails with error containing "No evaluation_criteria"

    Scenario: Empty reward_basis is rejected
        Given a scenario with label "DENY" and empty reward_basis
        When I validate the scenario
        Then validation fails with error containing "Empty reward_basis"

    Scenario: POLICY in reward_basis with no policy_checks is rejected
        Given a scenario with label "DENY" and POLICY basis but no policy_checks
        When I validate the scenario
        Then validation fails with error containing "no policy_checks"
