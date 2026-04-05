"""Step definitions for event_flags.feature."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/event_flags.feature")


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


def _policy_check(check_type: str, **params) -> dict:
    return {"type": check_type, **params}


# --- Shared fixtures ---


@pytest.fixture
def canonical_decision():
    return None


@pytest.fixture
def forbidden_tools():
    return []


@pytest.fixture
def runs():
    """List of run results for aggregation scenarios."""
    return []


# --- Given: scenario setup with expected outcomes ---


@given(
    parsers.re(
        r'an? (?P<label>DENY|ALLOW|ESCALATE) scenario with expected outcome '
        r'"(?P<ctype>[^"]+)" for "(?P<tool>[^"]+)"$'
    ),
    target_fixture="scenario_setup",
)
def scenario_with_outcome(label, ctype, tool):
    return {
        "label": label,
        "policy_checks": [_policy_check(ctype, tool_name=tool)],
        "forbidden_tools": [tool] if label == "DENY" and ctype == "tool_not_called" else [],
    }


@given(
    parsers.re(
        r'a (?P<label>DENY) scenario where "(?P<tool>[^"]+)" is forbidden$'
    ),
    target_fixture="scenario_setup",
)
def scenario_forbidden_tool(label, tool):
    return {
        "label": label,
        "policy_checks": [],
        "forbidden_tools": [tool],
    }


# --- Given: traces ---


@given(
    parsers.re(r'a trace where "(?P<tool>[^"]+)" was called$'),
    target_fixture="trace",
)
def trace_tool_called(tool):
    t = _make_trace()
    _record(t, tool)
    return t


@given(
    parsers.re(r'a trace where "(?P<tool>[^"]+)" was not called$'),
    target_fixture="trace",
)
def trace_tool_not_called(tool):
    return _make_trace()


@given(
    parsers.re(r'a trace where "(?P<tool>[^"]+)" was called and errored$'),
    target_fixture="trace",
)
def trace_tool_called_errored(tool):
    t = _make_trace()
    _record(t, tool, result_error=True, result_content="error: permission denied")
    return t


@given(
    parsers.re(
        r'a trace where "(?P<t1>[^"]+)" and "(?P<t2>[^"]+)" were called$'
    ),
    target_fixture="trace",
)
def trace_two_tools_called(t1, t2):
    t = _make_trace()
    _record(t, t1)
    _record(t, t2)
    return t


# --- Given: canonical decision ---


@given(
    parsers.re(r'a canonical decision of "(?P<decision>[^"]+)"$'),
    target_fixture="canonical_decision",
)
def set_canonical_decision(decision):
    return decision


# --- Given: aggregation runs ---


@given("4 runs where all are compliant", target_fixture="runs")
def four_compliant_runs():
    return [True, True, True, True]


@given(
    parsers.re(r"4 runs where run (?P<n>\d+) is non-compliant$"),
    target_fixture="runs",
)
def four_runs_one_noncompliant(n):
    runs = [True, True, True, True]
    runs[int(n) - 1] = False
    return runs


@given(
    parsers.re(r"4 runs where only run (?P<n>\d+) is compliant$"),
    target_fixture="runs",
)
def four_runs_one_compliant(n):
    runs = [False, False, False, False]
    runs[int(n) - 1] = True
    return runs


@given("4 runs where none are compliant", target_fixture="runs")
def four_runs_none_compliant():
    return [False, False, False, False]


@given(
    parsers.re(r"4 runs where run (?P<n>\d+) has V_r true$"),
    target_fixture="runs",
)
def four_runs_one_violation(n):
    runs = [False, False, False, False]
    runs[int(n) - 1] = True
    return runs


@given("4 runs where no run has V_r true", target_fixture="runs")
def four_runs_no_violation():
    return [False, False, False, False]


@given("4 runs where all have EA_r true", target_fixture="runs")
def four_runs_all_escalation():
    return [True, True, True, True]


@given(
    parsers.re(r"4 runs where run (?P<n>\d+) has EA_r false$"),
    target_fixture="runs",
)
def four_runs_one_escalation_false(n):
    runs = [True, True, True, True]
    runs[int(n) - 1] = False
    return runs


# --- When: compute event flags ---


@when("I compute event flags", target_fixture="flags")
def do_compute_flags(trace, scenario_setup, canonical_decision):
    from pi_bench.event_flags import compute_flags
    return compute_flags(
        scenario_label=scenario_setup["label"],
        trace=trace,
        canonical_decision=canonical_decision,
        policy_checks=scenario_setup["policy_checks"] or None,
        forbidden_tools=scenario_setup["forbidden_tools"] or None,
    )


# --- When: aggregation ---


@when("I compute PolicyPassAll^4", target_fixture="agg_result")
def compute_pass_all(runs):
    from pi_bench.event_flags import policy_pass_all
    return policy_pass_all(runs)


@when("I compute PolicyPassAny^4", target_fixture="agg_result")
def compute_pass_any(runs):
    from pi_bench.event_flags import policy_pass_any
    return policy_pass_any(runs)


@when("I compute ViolationEver^4", target_fixture="agg_result")
def compute_violation_ever(runs):
    from pi_bench.event_flags import violation_ever
    return violation_ever(runs)


@when("I compute EscalationAlways^4", target_fixture="agg_result")
def compute_escalation_always(runs):
    from pi_bench.event_flags import escalation_always
    return escalation_always(runs)


# --- Then: flag assertions ---


@then("V_r is true")
def v_r_true(flags):
    assert flags.V_r is True


@then("V_r is false")
def v_r_false(flags):
    assert flags.V_r is False


@then("UR_r is true")
def ur_r_true(flags):
    assert flags.UR_r is True


@then("UR_r is false")
def ur_r_false(flags):
    assert flags.UR_r is False


@then("OR_r is true")
def or_r_true(flags):
    assert flags.OR_r is True


@then("OR_r is false")
def or_r_false(flags):
    assert flags.OR_r is False


@then("EA_r is true")
def ea_r_true(flags):
    assert flags.EA_r is True


@then("EA_r is false")
def ea_r_false(flags):
    assert flags.EA_r is False


@then("AT_r is true")
def at_r_true(flags):
    assert flags.AT_r is True


@then("AT_r is false")
def at_r_false(flags):
    assert flags.AT_r is False


# --- Then: aggregation assertions ---


@then("PolicyPassAll^4 is true")
def pass_all_true(agg_result):
    assert agg_result is True


@then("PolicyPassAll^4 is false")
def pass_all_false(agg_result):
    assert agg_result is False


@then("PolicyPassAny^4 is true")
def pass_any_true(agg_result):
    assert agg_result is True


@then("PolicyPassAny^4 is false")
def pass_any_false(agg_result):
    assert agg_result is False


@then("ViolationEver^4 is true")
def violation_ever_true(agg_result):
    assert agg_result is True


@then("ViolationEver^4 is false")
def violation_ever_false(agg_result):
    assert agg_result is False


@then("EscalationAlways^4 is true")
def escalation_always_true(agg_result):
    assert agg_result is True


@then("EscalationAlways^4 is false")
def escalation_always_false(agg_result):
    assert agg_result is False
