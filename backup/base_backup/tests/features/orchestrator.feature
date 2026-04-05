Feature: Orchestrator routes messages between agent, user, and environment
    The orchestrator is a state machine that routes one message at a time
    between three roles: agent, user, and environment.

    # Spec contract 4
    Scenario: Messages route correctly
        Given a stub agent that calls tool "get_users" then responds with text
        And a stub user that responds with text then stops
        And a mock environment
        When I run the orchestrator to completion
        Then the trajectory contains agent text, user text, and tool results
        And tool results were routed back to the agent who called them

    # Spec contract 5
    Scenario: Simulation terminates
        Given a stub agent that always responds with text "ok"
        And a stub user that always responds with text "more"
        And a mock environment
        When I run the orchestrator with max_steps 4
        Then the simulation ends with termination reason "max_steps"
        And running with agent stop produces "agent_stop"
        And running with user stop produces "user_stop"
        And running with agent error produces "agent_error"
        And running with max errors produces "too_many_errors"
        And solo mode agent sending text produces "agent_error"

    # Spec contract 6
    Scenario: Trajectory is captured
        Given a stub agent that calls tool "get_users" then responds with text then stops
        And a stub user that always responds with text "ok"
        And a mock environment
        When I run the orchestrator to completion
        Then the result contains ordered messages with turn indices
        And the result has task_id, timestamps, termination reason, and costs
