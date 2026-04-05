"""Step definitions for tool.feature — Tool wrapping and schema generation."""

from pytest_bdd import scenarios, given, when, then

from tau2.environment.tool import Tool, as_tool

scenarios("../features/tool.feature")


# --- Test functions ---


def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The sum of a and b.
    """
    return a + b


def greet(db: dict, name: str) -> str:
    """Greet someone by name.

    Args:
        db: The database (predefined).
        name: The person's name.

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"


# --- Given ---


@given("a tool wrapping a simple function", target_fixture="tool")
def simple_tool():
    return Tool(add_numbers)


@given("a tool wrapping a documented function", target_fixture="tool")
def documented_tool():
    return Tool(add_numbers)


@given('a tool with a predefined "db" argument', target_fixture="tool")
def tool_with_predefined():
    return as_tool(greet, db={"users": {}})


# --- When ---


@when("I call the tool with valid arguments", target_fixture="tool_result")
def call_tool(tool):
    return tool(a=2, b=3)


# --- Then ---


@then("the tool name matches the function name")
def tool_name_matches(tool):
    assert tool.name == "add_numbers"


@then('the tool schema has type "function"')
def schema_has_type(tool):
    schema = tool.openai_schema
    assert schema["type"] == "function"


@then('the tool schema has a "function" key with "name" and "parameters"')
def schema_has_function(tool):
    schema = tool.openai_schema
    fn = schema["function"]
    assert "name" in fn
    assert "parameters" in fn


@then("the tool schema parameters include descriptions")
def schema_has_descriptions(tool):
    schema = tool.openai_schema
    params = schema["function"]["parameters"]
    props = params.get("properties", {})
    # At least one param should have a description
    has_desc = any("description" in p for p in props.values())
    assert has_desc, f"No parameter descriptions found in: {props}"


@then("the tool returns the expected result")
def tool_returns_expected(tool_result):
    assert tool_result == 5


@then('the tool schema parameters do not include "db"')
def no_db_in_schema(tool):
    schema = tool.openai_schema
    params = schema["function"]["parameters"]
    props = params.get("properties", {})
    assert "db" not in props, f"'db' should be hidden but found in: {props}"


@then("the tool is still callable")
def tool_callable(tool):
    result = tool(name="World")
    assert result == "Hello, World!"
