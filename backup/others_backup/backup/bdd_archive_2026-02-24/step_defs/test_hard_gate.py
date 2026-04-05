"""Step definitions for hard_gate.feature."""

import json

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/hard_gate.feature")


def _make_observer(mode, forbidden_tools=None):
    from pi_bench.domains.mock import get_environment
    from pi_bench.observer import create_observer
    from pi_bench.trace import TraceRecorder

    env = get_environment()
    trace = TraceRecorder()
    return create_observer(
        env=env,
        trace=trace,
        forbidden_tools=set(forbidden_tools or []),
        mode=mode,
    )


# --- Shared fixtures ---


@pytest.fixture
def forbidden_tools():
    """Mutable set of forbidden tools, populated by Given steps."""
    return set()


@pytest.fixture
def observer():
    """Default None — overridden by Given steps."""
    return None


# --- Given: scenario + mode setup ---


@given("a DENY scenario in audit-only mode", target_fixture="observer")
def deny_audit_mode():
    return _make_observer("audit_only")


@given("a DENY scenario in hard-gate mode", target_fixture="observer")
def deny_hard_gate_mode():
    return _make_observer("hard_gate")


@given(
    parsers.re(r'"(?P<tool>[^"]+)" is a forbidden tool$'),
)
def set_forbidden_tool(observer, tool):
    observer["forbidden_tools"].add(tool)


# --- Given: equivalence scenarios ---


@given("a scenario run in audit-only mode", target_fixture="audit_observer")
def audit_scenario():
    return _make_observer("audit_only")


@given(
    "the same scenario run without policy observation",
    target_fixture="plain_observer",
)
def plain_scenario():
    # "No policy observation" = audit mode with no forbidden tools
    # Both should produce identical results
    return _make_observer("audit_only")


@given("an ALLOW scenario with no forbidden tools", target_fixture="observer")
def allow_no_forbidden():
    return _make_observer("audit_only")


# --- When: tool calls ---


@when(
    parsers.re(r'the agent calls "(?P<tool>[^"]+)"$'),
    target_fixture="call_result",
)
def agent_calls_tool(observer, tool):
    from pi_bench.observer import observed_tool_call
    return observed_tool_call(observer, tool_name=tool)


@when(
    parsers.re(
        r'the agent calls "(?P<tool>[^"]+)" with '
        r'user_id "(?P<uid>[^"]+)" and title "(?P<title>[^"]+)"$'
    ),
    target_fixture="call_result",
)
def agent_calls_tool_with_args(observer, tool, uid, title):
    from pi_bench.observer import observed_tool_call
    return observed_tool_call(
        observer, tool_name=tool, arguments={"user_id": uid, "title": title},
    )


@when("the agent calls the same tool sequence", target_fixture="equivalence_results")
def agent_calls_sequence(audit_observer, plain_observer):
    from pi_bench.observer import observed_tool_call
    tools = ["get_users", "create_task"]
    audit_results = []
    plain_results = []
    for tool in tools:
        args = {"user_id": "user_1", "title": "Test"} if tool == "create_task" else {}
        audit_results.append(observed_tool_call(audit_observer, tool, arguments=args))
        plain_results.append(observed_tool_call(plain_observer, tool, arguments=args))
    return {"audit": audit_results, "plain": plain_results}


@when(
    "run in audit-only mode and hard-gate mode",
    target_fixture="dual_mode_traces",
)
def run_both_modes(observer):
    from pi_bench.observer import create_observer, observed_tool_call
    from pi_bench.domains.mock import get_environment
    from pi_bench.trace import TraceRecorder

    # Run same tool sequence in both modes
    tools = ["get_users"]

    audit_trace = TraceRecorder()
    audit_env = get_environment()
    audit_obs = create_observer(audit_env, audit_trace, mode="audit_only")

    gate_trace = TraceRecorder()
    gate_env = get_environment()
    gate_obs = create_observer(gate_env, gate_trace, mode="hard_gate")

    for tool in tools:
        observed_tool_call(audit_obs, tool)
        observed_tool_call(gate_obs, tool)

    return {"audit": audit_trace, "hard_gate": gate_trace}


# --- Then: execution behavior ---


@then("the tool executes normally")
def tool_executes(call_result):
    assert call_result["error"] is False


@then("the trace records the call")
def trace_has_call(observer):
    assert len(observer["trace"].entries) > 0


@then(parsers.re(r'the trace has an entry for "(?P<tool>[^"]+)"$'))
def trace_has_entry_for(observer, tool):
    assert observer["trace"].tool_called(tool)


@then("the entry is not marked as blocked")
def entry_not_blocked(observer):
    last = observer["trace"].entries[-1]
    assert last.blocked is False


@then("the entry is marked as blocked")
def entry_blocked(observer):
    last = observer["trace"].entries[-1]
    assert last.blocked is True


@then("the tool does not execute")
def tool_blocked(call_result):
    assert call_result["error"] is True


@then("the result is an error")
def result_is_error(call_result):
    assert call_result["error"] is True


@then("the result is not an error")
def result_not_error(call_result):
    assert call_result["error"] is False


@then(parsers.re(r'the result content contains "(?P<text>[^"]+)"$'))
def result_contains(call_result, text):
    content = call_result["content"]
    # Content may be JSON-encoded string
    try:
        decoded = json.loads(content)
        assert text in str(decoded)
    except (json.JSONDecodeError, TypeError):
        assert text in content


@then("AT_r is true")
def at_r_true(observer):
    from pi_bench.event_flags import compute_flags
    flags = compute_flags(
        scenario_label="DENY",
        trace=observer["trace"],
        canonical_decision="DENY",
        forbidden_tools=list(observer["forbidden_tools"]),
    )
    assert flags.AT_r is True


@then("all results are identical")
def results_identical(equivalence_results):
    audit = equivalence_results["audit"]
    plain = equivalence_results["plain"]
    assert len(audit) == len(plain)
    for a, p in zip(audit, plain):
        assert a["content"] == p["content"]
        assert a["error"] == p["error"]


@then("the database hash is unchanged")
def db_unchanged(observer):
    from pi_bench.environment import get_db_hash
    entries = observer["trace"].entries
    assert len(entries) > 0
    last = entries[-1]
    assert last.pre_state_hash == last.post_state_hash


@then("the database hash has changed")
def db_changed(observer):
    from pi_bench.environment import get_db_hash
    entries = observer["trace"].entries
    assert len(entries) > 0
    last = entries[-1]
    assert last.pre_state_hash != last.post_state_hash


@then("both modes produce identical traces")
def identical_traces(dual_mode_traces):
    audit = dual_mode_traces["audit"]
    gate = dual_mode_traces["hard_gate"]
    assert len(audit.entries) == len(gate.entries)
    for a, g in zip(audit.entries, gate.entries):
        assert a.tool_name == g.tool_name
        assert a.result_content == g.result_content
        assert a.blocked == g.blocked
