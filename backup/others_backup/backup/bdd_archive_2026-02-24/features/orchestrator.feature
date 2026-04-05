Feature: Orchestrator routes messages between agent, user, and environment
    The orchestrator is a state machine with three roles: Agent (LLM under
    test), User Simulator (LLM), and Environment (deterministic tool
    execution). It routes one message at a time between them.

    # --- Fresh start initialization ---

    Scenario: Fresh start sends greeting then routes to user
        Given a stub agent that always responds with text "I can help"
        And a stub user that always responds with text "Hi, I need help"
        And a mock environment
        When I run the orchestrator for 1 step
        Then the first message is from agent to user
        And the first message content is "Hi! How can I help you today?"

    Scenario: Fresh start with seed sets agent and user seeds
        Given a stub agent that records its seed
        And a stub user that records its seed
        And a mock environment
        When I initialize the orchestrator with seed 42
        Then the agent seed is 42
        And the user seed is 42

    # --- Text message routing ---

    Scenario: User text response routes to agent
        Given a stub agent that always responds with text "Sure, let me check"
        And a stub user that responds with text then stops
        And a mock environment
        When I run the orchestrator to completion
        Then the trajectory alternates between agent and user messages

    Scenario: Agent text response routes to user
        Given a stub agent that responds with text then stops
        And a stub user that always responds with text "Thanks"
        And a mock environment
        When I run the orchestrator to completion
        Then at least one user message follows an agent text message

    # --- Tool call routing ---

    Scenario: Agent tool calls route to environment then back to agent
        Given a stub agent that calls tool "get_users" then responds with text
        And a stub user that responds with text then stops
        And a mock environment
        When I run the orchestrator to completion
        Then the trajectory contains a tool result for "get_users"
        And the tool result requestor is "assistant"

    Scenario: User tool calls route to environment then back to user
        Given a stub agent that always responds with text "How can I help?"
        And a stub user that calls tool "get_users" then stops
        And a mock environment with user tools
        When I run the orchestrator to completion
        Then the trajectory contains a tool result for "get_users"
        And the tool result requestor is "user"

    Scenario: Tool results go back to the caller not the other role
        Given a stub agent that calls tool "get_users" then responds with text
        And a stub user that responds with text then stops
        And a mock environment
        When I run the orchestrator to completion
        Then the message after the tool result goes to agent not user

    Scenario: Multiple tool calls in one message produce multi-tool result
        Given a stub agent that calls tools "get_users" and "export_records" simultaneously
        And a stub user that responds with text then stops
        And a mock environment
        When I run the orchestrator to completion
        Then the trajectory contains tool results for both "get_users" and "export_records"

    # --- Termination: stop signals ---

    Scenario: Agent stop signal ends simulation
        Given a stub agent that sends stop signal after 2 exchanges
        And a stub user that always responds with text "ok"
        And a mock environment
        When I run the orchestrator to completion
        Then the termination reason is "agent_stop"

    Scenario: User stop signal ends simulation
        Given a stub agent that always responds with text "anything else?"
        And a stub user that sends stop signal after 1 exchange
        And a mock environment
        When I run the orchestrator to completion
        Then the termination reason is "user_stop"

    Scenario: User transfer signal ends simulation
        Given a stub agent that always responds with text "let me transfer you"
        And a stub user that sends transfer signal
        And a mock environment
        When I run the orchestrator to completion
        Then the termination reason is "user_stop"

    # --- Termination: limits ---

    Scenario: Max steps reached ends simulation
        Given a stub agent that always responds with text "ok"
        And a stub user that always responds with text "more"
        And a mock environment
        When I run the orchestrator with max_steps 4
        Then the termination reason is "max_steps"

    Scenario: Max errors reached ends simulation
        Given a stub agent that always calls nonexistent tool "fake_tool"
        And a stub user that always responds with text "try again"
        And a mock environment
        When I run the orchestrator with max_errors 3
        Then the termination reason is "too_many_errors"

    # --- Termination: errors ---

    Scenario: Agent generation error ends simulation
        Given a stub agent that raises an error on generate
        And a stub user that always responds with text "hi"
        And a mock environment
        When I run the orchestrator to completion
        Then the termination reason is "agent_error"

    Scenario: User generation error ends simulation
        Given a stub agent that always responds with text "hello"
        And a stub user that raises an error on generate
        And a mock environment
        When I run the orchestrator to completion
        Then the termination reason is "user_error"

    # --- Step counting ---

    Scenario: Limit checks do not fire after environment steps
        Given a stub agent that calls tool "get_users" then responds with text then stops
        And a stub user that always responds with text "ok"
        And a mock environment
        When I run the orchestrator to completion
        Then the simulation completes normally despite environment steps counting toward total

    # --- Trajectory ---

    Scenario: Full trajectory is returned in message order
        Given a stub agent that responds with text then stops
        And a stub user that always responds with text "thanks"
        And a mock environment
        When I run the orchestrator to completion
        Then the trajectory has at least 3 messages
        And messages are ordered by turn index

    Scenario: Simulation output contains required metadata
        Given a stub agent that responds with text then stops
        And a stub user that always responds with text "ok"
        And a mock environment
        When I run the orchestrator to completion
        Then the result has a task_id
        And the result has start and end timestamps
        And the result has a termination reason
        And the result has the full message trajectory

    # --- Solo mode ---

    Scenario: Solo mode skips user simulator
        Given a stub agent that calls tool "get_users" then responds with stop
        And a mock environment in solo mode
        When I run the orchestrator in solo mode
        Then no user messages appear in the trajectory
        And tool calls still execute normally

    # --- Observer integration ---

    Scenario: Observer wraps environment and records trace
        Given a stub agent that calls tool "get_users" then responds with text then stops
        And a stub user that always responds with text "ok"
        And a mock environment with observer in audit-only mode
        When I run the orchestrator to completion
        Then the observer trace has entries for all tool calls
        And the observer trace entry count matches the trajectory tool call count
