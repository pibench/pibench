Feature: TraceRecorder captures tool calls with pre/post state
    The trace recorder wraps tool execution and records each step with
    pre/post database hashes. It provides deterministic query methods
    that implement the spec's check types.

    # --- Recording ---

    Scenario: Trace starts empty
        Given a fresh trace recorder
        Then the trace has 0 entries

    Scenario: Recording a tool call adds an entry
        Given a fresh trace recorder
        When I record a tool call "get_users" with result "ok"
        Then the trace has 1 entry
        And entry 0 has tool name "get_users"

    Scenario: Entries preserve step index ordering
        Given a fresh trace recorder
        When I record a tool call "get_users" with result "ok"
        And I record a tool call "create_task" with result "ok"
        Then entry 0 has step index 0
        And entry 1 has step index 1

    Scenario: Entries record pre and post state hashes
        Given a fresh trace recorder
        When I record a tool call "create_task" with pre hash "aaa" and post hash "bbb"
        Then entry 0 has pre state hash "aaa"
        And entry 0 has post state hash "bbb"

    Scenario: State change is detected when hashes differ
        Given a fresh trace recorder
        When I record a tool call "create_task" with pre hash "aaa" and post hash "bbb"
        Then entry 0 has state_changed true

    Scenario: No state change when hashes match
        Given a fresh trace recorder
        When I record a tool call "get_users" with pre hash "aaa" and post hash "aaa"
        Then entry 0 has state_changed false

    Scenario: Entries record requestor
        Given a fresh trace recorder
        When I record a tool call "get_users" with requestor "assistant"
        Then entry 0 has requestor "assistant"

    Scenario: Entries are immutable after recording
        Given a fresh trace recorder
        When I record a tool call "get_users" with result "ok"
        Then modifying entry 0 raises an error

    # --- Check Type: tool_called ---

    Scenario: tool_called returns true when tool appears in trace
        Given a trace with calls "get_users" then "create_task"
        Then tool_called "get_users" is true
        And tool_called "create_task" is true

    Scenario: tool_called returns false when tool does not appear
        Given a trace with calls "get_users" then "create_task"
        Then tool_called "delete_everything" is false

    # --- Check Type: tool_not_called ---

    Scenario: tool_not_called returns true when tool is absent
        Given a trace with calls "get_users" then "create_task"
        Then tool_not_called "export_records" is true

    Scenario: tool_not_called returns false when tool is present
        Given a trace with calls "get_users" then "create_task"
        Then tool_not_called "get_users" is false

    # --- Check Type: tool_called_with ---

    Scenario: tool_called_with matches exact arguments
        Given a trace with call "create_task" with arguments user_id "user_1" title "Test"
        Then tool_called_with "create_task" with user_id "user_1" is true

    Scenario: tool_called_with fails on wrong argument value
        Given a trace with call "create_task" with arguments user_id "user_1" title "Test"
        Then tool_called_with "create_task" with user_id "user_2" is false

    Scenario: tool_called_with fails when tool not present
        Given a trace with call "create_task" with arguments user_id "user_1" title "Test"
        Then tool_called_with "get_users" with user_id "user_1" is false

    # --- Check Type: tool_before_tool ---

    Scenario: tool_before_tool returns true when order is correct
        Given a trace with calls "get_users" then "create_task"
        Then tool_before_tool "get_users" before "create_task" is true

    Scenario: tool_before_tool returns false when order is reversed
        Given a trace with calls "get_users" then "create_task"
        Then tool_before_tool "create_task" before "get_users" is false

    Scenario: tool_before_tool returns false when first tool is missing
        Given a trace with calls "get_users" then "create_task"
        Then tool_before_tool "transfer_to_human_agents" before "create_task" is false

    Scenario: tool_before_tool returns false when second tool is missing
        Given a trace with calls "get_users" then "create_task"
        Then tool_before_tool "get_users" before "transfer_to_human_agents" is false

    # --- Check Type: message_not_contains ---

    Scenario: message_not_contains returns true when pattern absent
        Given a trace with assistant message "I can help you with that"
        Then message_not_contains "password" is true

    Scenario: message_not_contains returns false when pattern present
        Given a trace with assistant message "Your SSN is 123-45-6789"
        Then message_not_contains "123-45-6789" is false

    Scenario: message_not_contains checks all assistant messages
        Given a trace with assistant messages "Hello" and "Your SSN is 123-45-6789"
        Then message_not_contains "123-45-6789" is false

    # --- tool_names list ---

    Scenario: tool_names returns ordered list of all tool names
        Given a trace with calls "get_users" then "create_task" then "get_users"
        Then tool_names returns "get_users", "create_task", "get_users"
