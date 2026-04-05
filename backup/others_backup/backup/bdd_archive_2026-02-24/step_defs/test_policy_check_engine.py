"""Step definitions for policy_check_engine.feature.

Outcomes accumulate in a mutable list via the `outcomes` fixture.
Each `Given an expected outcome ...` appends to it.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/policy_check_engine.feature")


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


def _outcome(oid, check_type, **params):
    from pi_bench.check_engine import ExpectedOutcome
    return ExpectedOutcome(outcome_id=oid, check_type=check_type, params=params)


# --- Shared fixtures ---


@pytest.fixture
def outcomes():
    """Mutable list that accumulates expected outcomes across Given steps."""
    return []


@pytest.fixture
def post_state():
    """Default post_state is None. Overridden by state-specific Given steps."""
    return None


# --- Given: traces ---


@given(parsers.re(r'a trace with call "(?P<tool>[^"]+)"$'), target_fixture="trace")
def trace_one_call(tool):
    t = _make_trace()
    _record(t, tool)
    return t


@given(
    parsers.re(r'a trace with calls "(?P<a>[^"]+)" then "(?P<b>[^"]+)"'),
    target_fixture="trace",
)
def trace_two_calls(a, b):
    t = _make_trace()
    _record(t, a)
    _record(t, b)
    return t


@given("an empty trace", target_fixture="trace")
def empty_trace():
    return _make_trace()


@given(
    parsers.parse('a trace with call "{tool}" at step {idx:d}'),
    target_fixture="trace",
)
def trace_call_at_step(tool, idx):
    t = _make_trace()
    _record(t, tool)
    return t


@given(
    parsers.parse(
        'a trace with call "{tool}" with arguments user_id "{uid}" title "{title}"'
    ),
    target_fixture="trace",
)
def trace_call_with_args(tool, uid, title):
    t = _make_trace()
    _record(t, tool, arguments={"user_id": uid, "title": title})
    return t


@given(
    parsers.parse('a post-run state where {tid} status is "{status}"'),
    target_fixture="post_state",
)
def given_post_state(tid, status):
    return {"tasks": {tid: {"status": status}}}


@given(
    parsers.parse('a trace with assistant message "{msg}"'),
    target_fixture="trace",
)
def trace_with_message(msg):
    t = _make_trace()
    t.add_message(role="assistant", content=msg)
    return t


# --- Given: expected outcomes (append to list) ---


@given(
    parsers.re(
        r'an expected outcome "(?P<oid>[^"]+)" of type "(?P<ctype>[^"]+)" for "(?P<tool>[^"]+)"$'
    ),
)
def outcome_simple(outcomes, oid, ctype, tool):
    outcomes.append(_outcome(oid, ctype, tool_name=tool))


@given(
    parsers.re(
        r'an expected outcome "(?P<oid>[^"]+)" of type "tool_called_with" '
        r'for "(?P<tool>[^"]+)" with user_id "(?P<uid>[^"]+)"'
    ),
)
def outcome_called_with(outcomes, oid, tool, uid):
    outcomes.append(_outcome(
        oid, "tool_called_with", tool_name=tool, arguments={"user_id": uid},
    ))


@given(
    parsers.parse(
        'an expected outcome "{oid}" of type "tool_before_tool" '
        'with first "{first}" second "{second}"'
    ),
)
def outcome_before(outcomes, oid, first, second):
    outcomes.append(_outcome(oid, "tool_before_tool", first=first, second=second))


@given(
    parsers.parse(
        'an expected outcome "{oid}" of type "state_field" '
        'for {tid} status "{expected}"'
    ),
)
def outcome_state_field(outcomes, oid, tid, expected):
    outcomes.append(_outcome(
        oid, "state_field", path=f"tasks.{tid}.status", expected_value=expected,
    ))


@given(
    parsers.parse(
        'an expected outcome "{oid}" of type "message_not_contains" '
        'for pattern "{pattern}"'
    ),
)
def outcome_msg_not_contains(outcomes, oid, pattern):
    outcomes.append(_outcome(oid, "message_not_contains", pattern=pattern))


# --- When ---


@when("I evaluate the expected outcomes", target_fixture="verdicts")
def do_evaluate(trace, outcomes, post_state):
    from pi_bench.check_engine import evaluate
    return evaluate(trace, outcomes, post_state)


@when("I evaluate the expected outcomes twice", target_fixture="verdict_pair")
def evaluate_twice(trace, outcomes, post_state):
    from pi_bench.check_engine import evaluate
    v1 = evaluate(trace, list(outcomes), post_state)
    v2 = evaluate(trace, list(outcomes), post_state)
    return (v1, v2)


# --- Then ---


def _find(verdicts, oid):
    for v in verdicts:
        if v.outcome_id == oid:
            return v
    raise AssertionError(f"No verdict for '{oid}'")


@then(parsers.parse('verdict "{oid}" is pass'))
def verdict_pass(verdicts, oid):
    assert _find(verdicts, oid).passed is True


@then(parsers.parse('verdict "{oid}" is fail'))
def verdict_fail(verdicts, oid):
    assert _find(verdicts, oid).passed is False


@then("the scenario result is pass")
def scenario_pass(verdicts):
    from pi_bench.check_engine import scenario_passed
    assert scenario_passed(verdicts) is True


@then("the scenario result is fail")
def scenario_fail(verdicts):
    from pi_bench.check_engine import scenario_passed
    assert scenario_passed(verdicts) is False


@then(parsers.parse('verdict "{oid}" has evidence'))
def has_evidence(verdicts, oid):
    assert _find(verdicts, oid).evidence is not None


@then(parsers.parse('verdict "{oid}" has no evidence'))
def no_evidence(verdicts, oid):
    assert _find(verdicts, oid).evidence is None


@then(parsers.parse("the evidence points to step index {idx:d}"))
def evidence_step(verdicts, idx):
    for v in verdicts:
        if v.evidence and v.evidence.step_index is not None:
            assert v.evidence.step_index == idx
            return
    raise AssertionError("No evidence with step_index")


@then(parsers.parse('the evidence references outcome "{oid}"'))
def evidence_outcome(verdicts, oid):
    for v in verdicts:
        if v.evidence and v.evidence.outcome_id == oid:
            return
    raise AssertionError(f"No evidence for '{oid}'")


@then("both evaluation results are identical")
def identical(verdict_pair):
    v1, v2 = verdict_pair
    assert len(v1) == len(v2)
    for a, b in zip(v1, v2):
        assert a.outcome_id == b.outcome_id
        assert a.passed == b.passed
