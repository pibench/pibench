"""Step definitions for environment.feature.

These tests are implementation-agnostic. They import:
- A factory that creates a fresh mock environment
- A way to make tool calls and get results

The tests don't know (or care) whether these are classes,
functions, dicts, or anything else.
"""

import json

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/environment.feature")


# --- Given ---


@given("a fresh mock environment", target_fixture="env")
def fresh_mock_env():
    from pi_bench.domains.mock import get_environment

    return get_environment()


@given("another fresh mock environment", target_fixture="env2")
def another_fresh_mock_env():
    from pi_bench.domains.mock import get_environment

    return get_environment()


# --- When ---


@when(parsers.parse('I call tool "{tool_name}"'), target_fixture="result")
def call_tool(env, tool_name):
    from pi_bench.environment import make_tool_call

    return make_tool_call(env, tool_name=tool_name, call_id="test_call")


@when(
    parsers.parse(
        'I call tool "{tool_name}" with user_id "{user_id}" and title "{title}"'
    ),
    target_fixture="result",
)
def call_tool_with_user_and_title(env, tool_name, user_id, title):
    from pi_bench.environment import make_tool_call

    return make_tool_call(
        env,
        tool_name=tool_name,
        call_id="test_call",
        arguments={"user_id": user_id, "title": title},
    )


@when(
    parsers.parse('I call tool "{tool_name}" with call id "{call_id}"'),
    target_fixture="result",
)
def call_tool_with_id(env, tool_name, call_id):
    from pi_bench.environment import make_tool_call

    return make_tool_call(env, tool_name=tool_name, call_id=call_id)


@when(
    parsers.parse('I call tool "{tool_name}" with summary "{summary}"'),
    target_fixture="result",
)
def call_tool_with_summary(env, tool_name, summary):
    from pi_bench.environment import make_tool_call

    return make_tool_call(
        env,
        tool_name=tool_name,
        call_id="test_call",
        arguments={"summary": summary},
    )


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
    from pi_bench.domains.mock import get_environment
    from pi_bench.environment import get_db_hash

    fresh = get_environment()
    assert get_db_hash(env) != get_db_hash(fresh)


@then(parsers.parse('the result id is "{expected_id}"'))
def result_has_id(result, expected_id):
    assert result["id"] == expected_id


@then("both environments have the same database hash")
def same_hash(env, env2):
    from pi_bench.environment import get_db_hash

    assert get_db_hash(env) == get_db_hash(env2)


@then("the result content is a string")
def result_content_is_string(result):
    assert isinstance(result["content"], str)


# --- Determinism steps ---


@when(
    parsers.parse('I call tool "{tool_name}" again'),
    target_fixture="result2",
)
def call_tool_again(env, tool_name):
    from pi_bench.environment import make_tool_call

    return make_tool_call(env, tool_name=tool_name, call_id="test_call_2")


@then("both results have identical content")
def both_results_identical(result, result2):
    assert result["content"] == result2["content"]


@when(
    parsers.parse(
        'I call tool "{tool_name}" with user_id "{user_id}" and title "{title}" on both environments'
    ),
)
def call_tool_on_both(env, env2, tool_name, user_id, title):
    from pi_bench.environment import make_tool_call

    make_tool_call(
        env,
        tool_name=tool_name,
        call_id="test_call",
        arguments={"user_id": user_id, "title": title},
    )
    make_tool_call(
        env2,
        tool_name=tool_name,
        call_id="test_call",
        arguments={"user_id": user_id, "title": title},
    )


# --- Requestor routing steps ---


@when(
    parsers.parse('I call tool "{tool_name}" as requestor "{requestor}"'),
    target_fixture="result",
)
def call_tool_as_requestor(env, tool_name, requestor):
    from pi_bench.environment import make_tool_call

    return make_tool_call(
        env, tool_name=tool_name, call_id="test_call", requestor=requestor
    )


@given("a fresh mock environment with user tools", target_fixture="env")
def fresh_mock_env_with_user_tools():
    from pi_bench.domains.mock import get_environment_with_user_tools

    return get_environment_with_user_tools()


@when(
    parsers.parse('I call a user-only tool as requestor "{requestor}"'),
    target_fixture="result",
)
def call_user_only_tool_as_requestor(env, requestor):
    from pi_bench.environment import make_tool_call

    return make_tool_call(
        env,
        tool_name="user_only_tool",
        call_id="test_call",
        requestor=requestor,
    )


@then(parsers.parse('the result requestor is "{expected}"'))
def result_requestor_matches(result, expected):
    assert result["requestor"] == expected, (
        f"Expected requestor '{expected}' but got '{result['requestor']}'"
    )


# --- Update task status step ---


@when(
    parsers.parse(
        'I call tool "{tool_name}" with task_id "{task_id}" and status "{status}"'
    ),
    target_fixture="result",
)
def call_tool_with_task_and_status(env, tool_name, task_id, status):
    from pi_bench.environment import make_tool_call

    return make_tool_call(
        env,
        tool_name=tool_name,
        call_id="test_call",
        arguments={"task_id": task_id, "status": status},
    )


# --- Multiple writes step ---


@then("the database hash differs from a single-write environment")
def hash_differs_from_single_write(env):
    from pi_bench.domains.mock import get_environment
    from pi_bench.environment import get_db_hash, make_tool_call

    single = get_environment()
    make_tool_call(
        single,
        tool_name="create_task",
        call_id="setup",
        arguments={"user_id": "user_1", "title": "First"},
    )
    assert get_db_hash(env) != get_db_hash(single)


# --- Domain identity steps ---


@then(parsers.parse('the environment domain name is "{expected}"'))
def env_domain_name(env, expected):
    from pi_bench.environment import get_domain_name

    assert get_domain_name(env) == expected


@then("the environment policy is not empty")
def env_policy_not_empty(env):
    from pi_bench.environment import get_policy

    policy = get_policy(env)
    assert policy and len(policy.strip()) > 0


@given(
    parsers.parse('a mock environment with policy "{policy_text}"'),
    target_fixture="env",
)
def mock_env_with_custom_policy(policy_text):
    from pi_bench.domains.mock import get_environment

    return get_environment(policy=policy_text)


@then(parsers.parse('the environment policy contains "{text}"'))
def env_policy_contains(env, text):
    from pi_bench.environment import get_policy

    policy = get_policy(env)
    assert text in policy, f"Expected '{text}' in policy: {policy}"


# --- Tool schema steps ---


@then("each tool has a name and parameter schema")
def tools_have_schemas(env):
    from pi_bench.environment import get_tool_schemas

    schemas = get_tool_schemas(env)
    assert len(schemas) > 0, "No tools found"
    for schema in schemas:
        assert "name" in schema, f"Tool missing 'name': {schema}"
        assert "parameters" in schema, f"Tool '{schema.get('name')}' missing 'parameters'"


# --- Solo mode steps ---


@then("the environment is not in solo mode")
def env_not_solo(env):
    from pi_bench.environment import is_solo_mode

    assert not is_solo_mode(env)


@given("a fresh mock environment with user tools in solo mode", target_fixture="env")
def fresh_mock_env_solo():
    from tau2.domains.mock.data_model import MockDB
    from tau2.domains.mock.tools import MockTools
    from tau2.domains.mock.utils import MOCK_DB_PATH, MOCK_POLICY_PATH
    from tau2.environment.environment import Environment

    from pi_bench.domains.mock import UserOnlyToolsNoOverlap

    db = MockDB.load(MOCK_DB_PATH)
    agent_tools = MockTools(db)
    user_tools = UserOnlyToolsNoOverlap(db)
    with open(MOCK_POLICY_PATH, "r") as fp:
        policy = fp.read()
    env = Environment(
        domain_name="mock",
        policy=policy,
        tools=agent_tools,
        user_tools=user_tools,
    )
    env.set_solo_mode(True)
    return env


# --- Environment info steps ---


@when("I get the environment info", target_fixture="info")
def get_env_info(env):
    from pi_bench.environment import get_info

    return get_info(env)


@then(parsers.parse('the info contains key "{key}" with value "{value}"'))
def info_has_key_value(info, key, value):
    assert key in info, f"Info missing key '{key}': {info.keys()}"
    assert info[key] == value, f"Expected '{value}' but got '{info[key]}'"


@then(parsers.parse('the info contains key "{key}"'))
def info_has_key(info, key):
    assert key in info, f"Info missing key '{key}': {info.keys()}"


@then("the info is JSON serializable")
def info_serializable(info):
    json.dumps(info)


@then("the info tool schemas list is not empty")
def info_schemas_not_empty(info):
    assert len(info["tool_schemas"]) > 0


# --- Set state steps ---


@when("I set the environment state to a custom database", target_fixture="_")
def set_custom_state(env):
    from pi_bench.environment import set_state

    custom_db = {
        "users": {"user_99": {"user_id": "user_99", "name": "Custom", "tasks": []}},
        "tasks": {},
    }
    set_state(env, custom_db)


@when("I set the environment state to an empty-tasks database", target_fixture="_")
def set_empty_tasks_state(env):
    from pi_bench.environment import set_state

    set_state(env, {
        "users": {"user_empty": {"user_id": "user_empty", "name": "Empty User", "tasks": []}},
        "tasks": {},
    })


# --- Check DB steps ---


@then("check_db against the initial database returns true")
def check_db_matches(env):
    from pi_bench.domains.mock import get_initial_db
    from pi_bench.environment import check_db

    assert check_db(env, get_initial_db())


@then("check_db against the initial database returns false")
def check_db_differs(env):
    from pi_bench.domains.mock import get_initial_db
    from pi_bench.environment import check_db

    assert not check_db(env, get_initial_db())
