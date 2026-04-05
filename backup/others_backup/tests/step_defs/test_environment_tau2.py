"""Step definitions for environment.feature — running against tau2-bench.

Same behavioral contracts, different implementation.
Adapts tau2's Environment + ToolCall → ToolMessage into the plain-dict
interface our Then-steps expect.

Some scenarios are skipped because tau2's mock domain doesn't expose
user tools, custom policies, solo mode, set_state with plain dicts,
or check_db with plain dicts. Those are pi-bench extensions.
"""

import json

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

try:
    from tau2.domains.mock.environment import get_environment as tau2_get_environment
    from tau2.domains.mock.data_model import MockDB
    from tau2.data_model.message import ToolCall
except ImportError:
    pytest.skip("tau2-bench not installed", allow_module_level=True)

scenarios("../features/environment.feature")


# --- Helpers ---


def _to_dict(msg) -> dict:
    """Adapt tau2 ToolMessage to the plain dict our Then-steps expect."""
    return {
        "id": msg.id,
        "content": msg.content,
        "requestor": msg.requestor,
        "error": msg.error,
    }


def _call(env, tool_name, call_id="test_call", arguments=None, requestor="assistant"):
    tc = ToolCall(id=call_id, name=tool_name, arguments=arguments or {},
                  requestor=requestor)
    return _to_dict(env.get_response(tc))


# --- Given ---


@given("a fresh mock environment", target_fixture="env")
def fresh_mock_env():
    return tau2_get_environment()


@given("another fresh mock environment", target_fixture="env2")
def another_fresh_mock_env():
    return tau2_get_environment()


@given("a fresh mock environment with user tools", target_fixture="env")
def fresh_mock_env_with_user_tools():
    pytest.skip("tau2 mock domain does not expose user tools")


@given(
    parsers.parse('a mock environment with policy "{policy_text}"'),
    target_fixture="env",
)
def mock_env_with_custom_policy(policy_text):
    pytest.skip("tau2 mock factory does not accept custom policy text")


@given("a fresh mock environment with user tools in solo mode", target_fixture="env")
def fresh_mock_env_solo():
    pytest.skip("tau2 mock domain does not expose user tools for solo mode testing")


# --- When ---


@when(parsers.parse('I call tool "{tool_name}"'), target_fixture="result")
def call_tool(env, tool_name):
    return _call(env, tool_name)


@when(
    parsers.parse(
        'I call tool "{tool_name}" with user_id "{user_id}" and title "{title}"'
    ),
    target_fixture="result",
)
def call_tool_with_user_and_title(env, tool_name, user_id, title):
    return _call(env, tool_name, arguments={"user_id": user_id, "title": title})


@when(
    parsers.parse('I call tool "{tool_name}" with call id "{call_id}"'),
    target_fixture="result",
)
def call_tool_with_id(env, tool_name, call_id):
    return _call(env, tool_name, call_id=call_id)


@when(
    parsers.parse('I call tool "{tool_name}" with summary "{summary}"'),
    target_fixture="result",
)
def call_tool_with_summary(env, tool_name, summary):
    return _call(env, tool_name, arguments={"summary": summary})


@when(parsers.parse('I call tool "{tool_name}" again'), target_fixture="result2")
def call_tool_again(env, tool_name):
    return _call(env, tool_name, call_id="test_call_2")


@when(
    parsers.parse(
        'I call tool "{tool_name}" with user_id "{user_id}" and title "{title}" on both environments'
    ),
)
def call_tool_on_both(env, env2, tool_name, user_id, title):
    _call(env, tool_name, arguments={"user_id": user_id, "title": title})
    _call(env2, tool_name, arguments={"user_id": user_id, "title": title})


@when(
    parsers.parse('I call tool "{tool_name}" as requestor "{requestor}"'),
    target_fixture="result",
)
def call_tool_as_requestor(env, tool_name, requestor):
    return _call(env, tool_name, requestor=requestor)


@when(
    parsers.parse('I call a user-only tool as requestor "{requestor}"'),
    target_fixture="result",
)
def call_user_only_tool(env, requestor):
    pytest.skip("tau2 mock domain does not have user-only tools")


@when(
    parsers.parse(
        'I call tool "{tool_name}" with task_id "{task_id}" and status "{status}"'
    ),
    target_fixture="result",
)
def call_tool_with_task_and_status(env, tool_name, task_id, status):
    return _call(env, tool_name, arguments={"task_id": task_id, "status": status})


@when("I get the environment info", target_fixture="info")
def get_env_info(env):
    info = env.get_info(include_tool_info=True)
    tool_defs = info.tool_defs or {}
    return {
        "domain_name": info.domain_name,
        "policy": info.policy,
        "tool_schemas": [
            {"name": sig.name, "parameters": sig.params}
            for sig in tool_defs.values()
        ],
    }


@when("I set the environment state to a custom database", target_fixture="_")
def set_custom_state(env):
    pytest.skip("tau2 set_state requires InitializationData + message history, not a plain dict")


@when("I set the environment state to an empty-tasks database", target_fixture="_")
def set_empty_tasks_state(env):
    pytest.skip("tau2 set_state requires InitializationData + message history, not a plain dict")


# --- Then ---


@then("the result is not an error")
def result_not_error(result):
    assert not result["error"], f"Expected success but got error: {result['content']}"


@then("the result is an error")
def result_is_error(result):
    assert result["error"], f"Expected error but got success: {result['content']}"


@then("the result content is valid JSON")
def result_is_valid_json(result):
    json.loads(result["content"])


@then(parsers.parse('the result content contains "{text}"'))
def result_contains(result, text):
    assert text in result["content"], (
        f"Expected '{text}' in result content: {result['content']}"
    )


@then("the database hash differs from a fresh environment")
def hash_differs(env):
    fresh = tau2_get_environment()
    assert env.get_db_hash() != fresh.get_db_hash()


@then(parsers.parse('the result id is "{expected_id}"'))
def result_has_id(result, expected_id):
    assert result["id"] == expected_id


@then("both environments have the same database hash")
def same_hash(env, env2):
    assert env.get_db_hash() == env2.get_db_hash()


@then("the result content is a string")
def result_content_is_string(result):
    assert isinstance(result["content"], str)


@then("both results have identical content")
def both_results_identical(result, result2):
    assert result["content"] == result2["content"]


@then(parsers.parse('the result requestor is "{expected}"'))
def result_requestor_matches(result, expected):
    assert result["requestor"] == expected


@then("the database hash differs from a single-write environment")
def hash_differs_from_single_write(env):
    single = tau2_get_environment()
    _call(single, "create_task", arguments={"user_id": "user_1", "title": "First"})
    assert env.get_db_hash() != single.get_db_hash()


@then(parsers.parse('the environment domain name is "{expected}"'))
def env_domain_name(env, expected):
    assert env.get_domain_name() == expected


@then("the environment policy is not empty")
def env_policy_not_empty(env):
    assert env.get_policy() and len(env.get_policy().strip()) > 0


@then(parsers.parse('the environment policy contains "{text}"'))
def env_policy_contains(env, text):
    assert text in env.get_policy()


@then("each tool has a name and parameter schema")
def tools_have_schemas(env):
    tools = env.get_tools()
    assert len(tools) > 0
    for tool in tools:
        assert tool.name, f"Tool missing name"
        assert tool.params is not None, f"Tool '{tool.name}' missing params"


@then("the environment is not in solo mode")
def env_not_solo(env):
    assert not env.solo_mode


@then(parsers.parse('the info contains key "{key}" with value "{value}"'))
def info_has_key_value(info, key, value):
    assert key in info, f"Info missing key '{key}'"
    assert info[key] == value


@then(parsers.parse('the info contains key "{key}"'))
def info_has_key(info, key):
    assert key in info, f"Info missing key '{key}'"


@then("the info is JSON serializable")
def info_serializable(info):
    json.dumps(info)


@then("the info tool schemas list is not empty")
def info_schemas_not_empty(info):
    assert len(info["tool_schemas"]) > 0


@then("check_db against the initial database returns true")
def check_db_matches(env):
    from tau2.domains.mock.utils import MOCK_DB_PATH
    reference = MockDB.load(MOCK_DB_PATH)
    assert env.check_db(reference)


@then("check_db against the initial database returns false")
def check_db_differs(env):
    from tau2.domains.mock.utils import MOCK_DB_PATH
    reference = MockDB.load(MOCK_DB_PATH)
    assert not env.check_db(reference)
