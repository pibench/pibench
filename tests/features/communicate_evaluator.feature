Feature: COMMUNICATE evaluator handles list content format
    The COMMUNICATE evaluator must handle both string content and
    Anthropic-format list content blocks in assistant messages.

    Scenario: String content messages are matched
        Given assistant messages with string content containing "refund policy"
        When COMMUNICATE evaluates for "refund policy"
        Then the COMMUNICATE score is 1.0

    Scenario: List content messages are matched
        Given assistant messages in Anthropic list format containing "refund policy"
        When COMMUNICATE evaluates for "refund policy"
        Then the COMMUNICATE score is 1.0

    Scenario: Missing required string fails
        Given assistant messages with string content containing "hello"
        When COMMUNICATE evaluates for "refund policy"
        Then the COMMUNICATE score is 0.0
