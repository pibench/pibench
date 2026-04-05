Feature: Interface agent runs an LLM loop against the environment
    The interface agent sends user messages to an LLM, executes tool calls
    against the environment, and returns the final response. This is the
    agentic loop that drives evaluation.

    Scenario: Interface agent accepts a message and returns a response
        Given a fresh interface agent
        When the agent receives message "How many users are there?"
        Then the agent returns a non-empty response

    Scenario: Interface agent makes tool calls to answer questions
        Given a fresh interface agent
        When the agent receives message "List all users"
        Then the agent response mentions user data

    Scenario: Interface agent maintains message history
        Given a fresh interface agent
        When the agent receives message "List all users"
        Then the message history has more than 1 entry

    Scenario: Interface agent seed can be set
        Given a fresh interface agent
        When I set the agent seed to 42
        Then the seed is set without error
