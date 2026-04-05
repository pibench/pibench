Feature: Toolkit collects tools with type classification
    A Toolkit groups related tools, tracks their types (READ/WRITE/THINK),
    and dispatches calls by name. It owns a DB reference for stateful tools.

    Scenario: Toolkit discovers decorated tools
        Given a fresh mock toolkit
        Then the toolkit has at least 3 tools

    Scenario: Tools have type classifications
        Given a fresh mock toolkit
        Then "get_users" is a READ tool
        And "create_task" is a WRITE tool

    Scenario: Toolkit dispatches tool calls by name
        Given a fresh mock toolkit
        When I use the toolkit to call "get_users"
        Then the toolkit call succeeds

    Scenario: Toolkit rejects unknown tool names
        Given a fresh mock toolkit
        When I use the toolkit to call "nonexistent_tool"
        Then the toolkit call raises an error

    Scenario: Toolkit provides tool statistics
        Given a fresh mock toolkit
        Then the toolkit statistics include read and write counts

    Scenario: Toolkit produces Tool objects with schemas
        Given a fresh mock toolkit
        When I get the toolkit's Tool objects
        Then each Tool object has an openai_schema

    Scenario: Toolkit tracks database hash
        Given a fresh mock toolkit
        Then the toolkit database hash is a non-empty string

    Scenario: GenericToolKit provides think and calculate tools
        Given a generic toolkit
        Then the toolkit has a "think" tool
        And the toolkit has a "calculate" tool

    Scenario: Calculate tool evaluates math expressions
        Given a generic toolkit
        When I use the toolkit to calculate "2 + 3 * 4"
        Then the calculation result is "14.0"

    Scenario: Calculate tool rejects invalid expressions
        Given a generic toolkit
        When I use the toolkit to calculate "import os"
        Then the toolkit call raises an error
