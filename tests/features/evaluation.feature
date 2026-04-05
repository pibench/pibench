Feature: Evaluation pipeline checks traces and computes rewards
    The check engine evaluates expected outcomes deterministically.
    Reward composition combines evaluator results.

    # Spec contract 7
    Scenario: Check engine produces correct verdicts
        Given a trace where "get_users" was called then "export_records" was called
        And expected outcomes: tool_called "get_users", tool_not_called "export_records"
        When I evaluate the expected outcomes
        Then "get_users" called verdict is pass
        And "export_records" not called verdict is fail with evidence pointing to the call

    # Spec contract 8
    Scenario: Reward composition works
        Given a simulation that terminated abnormally
        Then the reward is 0.0
        Given a simulation with no evaluation criteria
        Then the reward is 1.0
        Given a simulation where action evaluator returns 1.0 and db evaluator returns 0.0
        Then the reward is 0.0
