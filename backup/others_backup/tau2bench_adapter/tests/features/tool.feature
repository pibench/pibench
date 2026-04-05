Feature: Tool wraps a Python function for LLM calling
    A Tool introspects a function's signature and docstring to produce
    an OpenAI-compatible schema. It can be called with or without
    predefined arguments.

    Scenario: Tool extracts name from function
        Given a tool wrapping a simple function
        Then the tool name matches the function name

    Scenario: Tool produces an OpenAI-compatible schema
        Given a tool wrapping a simple function
        Then the tool schema has type "function"
        And the tool schema has a "function" key with "name" and "parameters"

    Scenario: Tool schema includes parameter descriptions from docstring
        Given a tool wrapping a documented function
        Then the tool schema parameters include descriptions

    Scenario: Tool is callable and returns the function result
        Given a tool wrapping a simple function
        When I call the tool with valid arguments
        Then the tool returns the expected result

    Scenario: Predefined arguments are hidden from the schema
        Given a tool with a predefined "db" argument
        Then the tool schema parameters do not include "db"
        And the tool is still callable
