"""Step definitions for toolkit.feature — tool collection and dispatch."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from tau2.domains.mock.data_model import MockDB
from tau2.domains.mock.tools import MockTools
from tau2.domains.mock.utils import MOCK_DB_PATH
from tau2.environment.toolkit import GenericToolKit, ToolType

scenarios("../features/toolkit.feature")


# --- Given ---


@given("a fresh mock toolkit", target_fixture="toolkit")
def fresh_mock_toolkit():
    db = MockDB.load(MOCK_DB_PATH)
    return MockTools(db)


@given("a generic toolkit", target_fixture="toolkit")
def generic_toolkit():
    return GenericToolKit()


# --- When ---


@when(parsers.parse('I use the toolkit to call "{tool_name}"'), target_fixture="toolkit_result")
def use_toolkit(toolkit, tool_name):
    try:
        result = toolkit.use_tool(tool_name)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": e}


@when("I get the toolkit's Tool objects", target_fixture="tool_objects")
def get_tool_objects(toolkit):
    return toolkit.get_tools()


@when(parsers.parse('I use the toolkit to calculate "{expression}"'), target_fixture="toolkit_result")
def use_toolkit_calculate(toolkit, expression):
    try:
        result = toolkit.use_tool("calculate", expression=expression)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": e}


# --- Then ---


@then("the toolkit has at least 3 tools")
def toolkit_has_tools(toolkit):
    tools = toolkit.get_tools()
    assert len(tools) >= 3, f"Expected at least 3 tools, got {len(tools)}: {list(tools.keys())}"


@then(parsers.parse('"{tool_name}" is a READ tool'))
def tool_is_read(toolkit, tool_name):
    assert toolkit.tool_type(tool_name) == ToolType.READ


@then(parsers.parse('"{tool_name}" is a WRITE tool'))
def tool_is_write(toolkit, tool_name):
    assert toolkit.tool_type(tool_name) == ToolType.WRITE


@then("the toolkit call succeeds")
def toolkit_call_succeeds(toolkit_result):
    assert toolkit_result["error"] is None, f"Unexpected error: {toolkit_result['error']}"


@then("the toolkit call raises an error")
def toolkit_call_raises(toolkit_result):
    assert toolkit_result["error"] is not None, "Expected an error but call succeeded"


@then("the toolkit statistics include read and write counts")
def toolkit_has_statistics(toolkit):
    stats = toolkit.get_statistics()
    assert "num_read_tools" in stats
    assert "num_write_tools" in stats
    assert stats["num_tools"] > 0


@then("each Tool object has an openai_schema")
def tools_have_schemas(tool_objects):
    assert len(tool_objects) > 0
    for name, tool in tool_objects.items():
        schema = tool.openai_schema
        assert "type" in schema, f"Tool '{name}' missing 'type' in schema"
        assert "function" in schema, f"Tool '{name}' missing 'function' in schema"


@then("the toolkit database hash is a non-empty string")
def toolkit_db_hash(toolkit):
    h = toolkit.get_db_hash()
    assert isinstance(h, str) and len(h) > 0


@then(parsers.parse('the toolkit has a "{tool_name}" tool'))
def toolkit_has_tool(toolkit, tool_name):
    assert toolkit.has_tool(tool_name), f"Toolkit missing tool '{tool_name}'"


@then(parsers.parse('the calculation result is "{expected}"'))
def calculation_result(toolkit_result, expected):
    assert toolkit_result["error"] is None, f"Calculation error: {toolkit_result['error']}"
    assert toolkit_result["result"] == expected
