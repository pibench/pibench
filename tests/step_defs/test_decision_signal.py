"""Step definitions for decision_signal.feature."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/decision_signal.feature")


def _make_trace():
    from pi_bench.trace import TraceRecorder
    return TraceRecorder()


def _record(trace, name, **overrides):
    defaults = dict(
        tool_name=name, arguments={}, result_content="ok",
        result_error=False, pre_state_hash="aaa", post_state_hash="aaa",
    )
    defaults.update(overrides)
    return trace.record(**defaults)


# --- Shared fixtures ---


@pytest.fixture
def trace():
    """Default empty trace — overridden by Given steps with target_fixture."""
    return _make_trace()


# --- Given: traces with record_decision tool calls ---


@given(
    parsers.re(
        r'a trace where assistant called record_decision with decision "(?P<decision>[^"]+)"$'
    ),
    target_fixture="trace",
)
def trace_with_decision_tool(decision):
    t = _make_trace()
    _record(t, "record_decision", arguments={"decision": decision, "reason": "test"})
    return t


@given(
    parsers.re(
        r'a trace where assistant called record_decision twice '
        r'with "(?P<d1>[^"]+)" and "(?P<d2>[^"]+)"'
    ),
    target_fixture="trace",
)
def trace_with_two_decisions(d1, d2):
    t = _make_trace()
    _record(t, "record_decision", arguments={"decision": d1, "reason": "first"})
    _record(t, "record_decision", arguments={"decision": d2, "reason": "second"})
    return t


@given("a trace with no record_decision calls", target_fixture="trace")
def trace_no_decision_tool():
    return _make_trace()


@given(
    parsers.re(
        r'a trace where assistant said "(?P<msg>[^"]+)"$'
    ),
    target_fixture="trace",
)
def trace_with_said_message(msg):
    t = _make_trace()
    t.add_message(role="assistant", content=msg)
    return t


# --- Given: JSON decision blocks in messages (append to trace) ---


@given(
    parsers.re(
        r'assistant message contains a fenced JSON block with decision "(?P<decision>[^"]+)"$'
    ),
)
def add_json_decision_block(trace, decision):
    content = f'```json\n{{"decision": "{decision}", "reason": "test"}}\n```'
    trace.add_message(role="assistant", content=content)


@given(
    parsers.re(
        r'assistant messages contain two fenced JSON blocks '
        r'with decisions "(?P<d1>[^"]+)" and "(?P<d2>[^"]+)"'
    ),
)
def add_two_json_blocks(trace, d1, d2):
    content1 = f'```json\n{{"decision": "{d1}", "reason": "first"}}\n```'
    trace.add_message(role="assistant", content=content1)
    content2 = f'```json\n{{"decision": "{d2}", "reason": "second"}}\n```'
    trace.add_message(role="assistant", content=content2)


@given("no JSON decision blocks in assistant messages")
def no_json_blocks(trace):
    # Trace already has no messages with JSON blocks — nothing to do.
    pass


@given("assistant message contains a fenced block with invalid JSON")
def add_invalid_json_block(trace):
    content = "```json\n{not valid json\n```"
    trace.add_message(role="assistant", content=content)


@given(
    parsers.re(
        r'assistant message contains a fenced JSON block '
        r'with key "(?P<key>[^"]+)" value "(?P<val>[^"]+)"'
    ),
)
def add_json_block_with_key(trace, key, val):
    content = f'```json\n{{"{key}": "{val}"}}\n```'
    trace.add_message(role="assistant", content=content)


@given("no record_decision calls")
def no_record_decision(trace):
    # Already no record_decision calls — nothing to do.
    pass


@given("no JSON decision blocks")
def no_json_decision_blocks(trace):
    # Already no JSON blocks — nothing to do.
    pass


# --- When ---


@when("I resolve the canonical decision", target_fixture="resolution")
def do_resolve(trace):
    from pi_bench.decision import resolve
    return resolve(trace)


@when("I check compliance for a DENY scenario", target_fixture="compliance_result")
def check_deny_compliance(trace):
    from pi_bench.decision import resolve, check_compliance_missing_decision
    result = resolve(trace)
    compliant, evidence = check_compliance_missing_decision(result)
    return {"compliant": compliant, "evidence": evidence, "resolution": result}


# --- Then ---


@then(parsers.re(r'the canonical decision is "(?P<expected>[^"]+)"'))
def canonical_decision_is(resolution, expected):
    from pi_bench.decision import CanonicalDecision
    assert isinstance(resolution, CanonicalDecision), f"Expected CanonicalDecision, got {resolution}"
    assert resolution.decision == expected


@then(parsers.re(r'the result is InvalidRun with reason "(?P<reason>[^"]+)"'))
def invalid_run_with_reason(resolution, reason):
    from pi_bench.decision import InvalidRun
    assert isinstance(resolution, InvalidRun), f"Expected InvalidRun, got {resolution}"
    assert resolution.reason == reason


@then("the run is non-compliant")
def run_non_compliant(compliance_result):
    assert compliance_result["compliant"] is False


@then("evidence points to missing decision")
def evidence_missing_decision(compliance_result):
    assert compliance_result["evidence"] == "missing_decision"
