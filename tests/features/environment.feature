Feature: Environment executes tool calls deterministically
    The environment holds an in-memory DB, dispatches tool calls,
    and returns results. Same inputs always produce same outputs.

    Scenario: Read tool returns data as JSON
        Given a fresh mock environment
        When I call tool "get_users"
        Then the result is not an error
        And the result content is valid JSON
        And the result content contains "Test User"

    Scenario: Write tool mutates database state
        Given a fresh mock environment
        When I call tool "create_task" with user_id "user_1" and title "New task"
        Then the result is not an error
        And the database hash differs from a fresh environment

    Scenario: Unknown tool returns error without crashing
        Given a fresh mock environment
        When I call tool "delete_everything"
        Then the result is an error

    Scenario: Invalid arguments return error without crashing
        Given a fresh mock environment
        When I call tool "create_task" with user_id "nonexistent" and title "Bad"
        Then the result is an error

    Scenario: Result ID matches the call ID
        Given a fresh mock environment
        When I call tool "get_users" with call id "call_abc_123"
        Then the result id is "call_abc_123"

    Scenario: Two fresh environments have the same hash
        Given a fresh mock environment
        And another fresh mock environment
        Then both environments have the same database hash

    Scenario: Tool results are always JSON strings
        Given a fresh mock environment
        When I call tool "transfer_to_human_agents" with summary "help needed"
        Then the result is not an error
        And the result content is a string

    # --- Determinism (blueprint contract #4) ---

    Scenario: Same read tool called twice returns identical results
        Given a fresh mock environment
        When I call tool "get_users"
        And I call tool "get_users" again
        Then both results have identical content

    Scenario: Same write produces same hash on independent environments
        Given a fresh mock environment
        And another fresh mock environment
        When I call tool "create_task" with user_id "user_1" and title "X" on both environments
        Then both environments have the same database hash

    # --- Requestor routing (blueprint contract #6) ---

    Scenario: Assistant tool call routes to agent tools
        Given a fresh mock environment
        When I call tool "get_users" as requestor "assistant"
        Then the result is not an error
        And the result requestor is "assistant"

    Scenario: User tool call routes to user tools
        Given a fresh mock environment with user tools
        When I call tool "get_users" as requestor "user"
        Then the result is not an error
        And the result requestor is "user"

    Scenario: Assistant cannot call user-only tools
        Given a fresh mock environment with user tools
        When I call a user-only tool as requestor "assistant"
        Then the result is an error

    # --- Write-then-read consistency ---

    Scenario: Write followed by read reflects the mutation
        Given a fresh mock environment
        When I call tool "create_task" with user_id "user_1" and title "New task"
        And I call tool "get_users"
        Then the result content contains "task_2"

    Scenario: Update task status changes the task
        Given a fresh mock environment
        When I call tool "update_task_status" with task_id "task_1" and status "completed"
        Then the result is not an error
        And the result content contains "completed"

    # --- Multiple writes compose ---

    Scenario: Two writes produce a state different from either alone
        Given a fresh mock environment
        When I call tool "create_task" with user_id "user_1" and title "First"
        And I call tool "create_task" with user_id "user_1" and title "Second"
        Then the database hash differs from a single-write environment

    # --- Error result quality ---

    Scenario: Error result contains a descriptive message
        Given a fresh mock environment
        When I call tool "delete_everything"
        Then the result is an error
        And the result content contains "delete_everything"

    Scenario: Error result preserves the call ID
        Given a fresh mock environment
        When I call tool "delete_everything" with call id "call_err_456"
        Then the result is an error
        And the result id is "call_err_456"

    # --- Identity (blueprint contracts: domain identity, policy passthrough) ---

    Scenario: Environment knows its domain name
        Given a fresh mock environment
        Then the environment domain name is "mock"

    Scenario: Environment has a non-empty policy
        Given a fresh mock environment
        Then the environment policy is not empty

    Scenario: Same domain can be loaded with a different policy
        Given a mock environment with policy "Custom policy: always escalate"
        Then the environment domain name is "mock"
        And the environment policy contains "always escalate"

    # --- Tool schema exposure (blueprint: tool collection) ---

    Scenario: Tools expose schemas for LLM function calling
        Given a fresh mock environment
        Then each tool has a name and parameter schema

    # --- Solo mode (single-turn, no user simulator) ---

    Scenario: Solo mode is off by default
        Given a fresh mock environment with user tools
        Then the environment is not in solo mode

    Scenario: Solo mode disables user tools
        Given a fresh mock environment with user tools in solo mode
        When I call a user-only tool as requestor "user"
        Then the result is an error

    Scenario: Solo mode still allows agent tools
        Given a fresh mock environment with user tools in solo mode
        When I call tool "get_users" as requestor "assistant"
        Then the result is not an error

    # --- Environment info (serializable metadata) ---

    Scenario: Environment info contains domain name and policy
        Given a fresh mock environment
        When I get the environment info
        Then the info contains key "domain_name" with value "mock"
        And the info contains key "policy"
        And the info is JSON serializable

    Scenario: Environment info includes tool schemas
        Given a fresh mock environment
        When I get the environment info
        Then the info contains key "tool_schemas"
        And the info tool schemas list is not empty

    # --- Set state (replace DB) ---

    Scenario: Setting state replaces the database
        Given a fresh mock environment
        When I set the environment state to a custom database
        Then the database hash differs from a fresh environment

    Scenario: Tools operate against the new state after set_state
        Given a fresh mock environment
        When I set the environment state to an empty-tasks database
        And I call tool "get_users"
        Then the result is not an error
        And the result content contains "Empty User"

    # --- Check DB (compare against reference) ---

    Scenario: check_db returns true for matching state
        Given a fresh mock environment
        Then check_db against the initial database returns true

    Scenario: check_db returns false after mutation
        Given a fresh mock environment
        When I call tool "create_task" with user_id "user_1" and title "New"
        Then check_db against the initial database returns false
