"""Step definitions for trace_recorder.feature."""

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/trace_recorder.feature")


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


# --- Given ---


@given("a fresh trace recorder", target_fixture="trace")
def fresh_trace():
    return _make_trace()


@given(
    parsers.re(
        r'a trace with calls "(?P<a>[^"]+)" then "(?P<b>[^"]+)" then "(?P<c>[^"]+)"'
    ),
    target_fixture="trace",
)
def trace_three(a, b, c):
    t = _make_trace()
    for name in [a, b, c]:
        _record(t, name)
    return t


@given(
    parsers.re(r'a trace with calls "(?P<first>[^"]+)" then "(?P<second>[^"]+)"'),
    target_fixture="trace",
)
def trace_two(first, second):
    t = _make_trace()
    _record(t, first)
    _record(t, second)
    return t


@given(
    parsers.parse(
        'a trace with call "{tool}" with arguments '
        'user_id "{uid}" title "{title}"'
    ),
    target_fixture="trace",
)
def trace_with_args(tool, uid, title):
    t = _make_trace()
    _record(t, tool, arguments={"user_id": uid, "title": title})
    return t


@given(
    parsers.parse('a trace with assistant message "{msg}"'),
    target_fixture="trace",
)
def trace_with_msg(msg):
    t = _make_trace()
    t.add_message(role="assistant", content=msg)
    return t


@given(
    parsers.parse('a trace with assistant messages "{m1}" and "{m2}"'),
    target_fixture="trace",
)
def trace_with_two_msgs(m1, m2):
    t = _make_trace()
    t.add_message(role="assistant", content=m1)
    t.add_message(role="assistant", content=m2)
    return t


# --- When ---


@when(parsers.parse('I record a tool call "{name}" with result "{res}"'))
def record_with_result(trace, name, res):
    _record(trace, name, result_content=res)


@when(
    parsers.parse(
        'I record a tool call "{name}" with pre hash "{pre}" and post hash "{post}"'
    ),
)
def record_with_hashes(trace, name, pre, post):
    _record(trace, name, pre_state_hash=pre, post_state_hash=post)


@when(parsers.parse('I record a tool call "{name}" with requestor "{req}"'))
def record_with_requestor(trace, name, req):
    _record(trace, name, requestor=req)


# --- Then ---


@then(parsers.parse("the trace has {n:d} entries"))
def trace_n_entries(trace, n):
    assert len(trace.entries) == n


@then(parsers.parse("the trace has {n:d} entry"))
def trace_1_entry(trace, n):
    assert len(trace.entries) == n


@then(parsers.parse('entry {i:d} has tool name "{expected}"'))
def entry_tool_name(trace, i, expected):
    assert trace.entries[i].tool_name == expected


@then(parsers.parse("entry {i:d} has step index {expected:d}"))
def entry_step_index(trace, i, expected):
    assert trace.entries[i].step_index == expected


@then(parsers.parse('entry {i:d} has pre state hash "{expected}"'))
def entry_pre_hash(trace, i, expected):
    assert trace.entries[i].pre_state_hash == expected


@then(parsers.parse('entry {i:d} has post state hash "{expected}"'))
def entry_post_hash(trace, i, expected):
    assert trace.entries[i].post_state_hash == expected


@then(parsers.parse("entry {i:d} has state_changed true"))
def entry_changed_true(trace, i):
    assert trace.entries[i].state_changed is True


@then(parsers.parse("entry {i:d} has state_changed false"))
def entry_changed_false(trace, i):
    assert trace.entries[i].state_changed is False


@then(parsers.parse('entry {i:d} has requestor "{expected}"'))
def entry_requestor(trace, i, expected):
    assert trace.entries[i].requestor == expected


@then(parsers.parse("modifying entry {i:d} raises an error"))
def entry_immutable(trace, i):
    entry = trace.entries[i]
    try:
        entry.tool_name = "hacked"  # type: ignore[misc]
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass


@then(parsers.parse('tool_called "{name}" is true'))
def tool_called_true(trace, name):
    assert trace.tool_called(name) is True


@then(parsers.parse('tool_called "{name}" is false'))
def tool_called_false(trace, name):
    assert trace.tool_called(name) is False


@then(parsers.parse('tool_not_called "{name}" is true'))
def tool_not_called_true(trace, name):
    assert trace.tool_not_called(name) is True


@then(parsers.parse('tool_not_called "{name}" is false'))
def tool_not_called_false(trace, name):
    assert trace.tool_not_called(name) is False


@then(parsers.parse('tool_called_with "{name}" with user_id "{uid}" is true'))
def called_with_true(trace, name, uid):
    assert trace.tool_called_with(name, user_id=uid) is True


@then(parsers.parse('tool_called_with "{name}" with user_id "{uid}" is false'))
def called_with_false(trace, name, uid):
    assert trace.tool_called_with(name, user_id=uid) is False


@then(parsers.parse('tool_before_tool "{first}" before "{second}" is true'))
def before_true(trace, first, second):
    assert trace.tool_before_tool(first, second) is True


@then(parsers.parse('tool_before_tool "{first}" before "{second}" is false'))
def before_false(trace, first, second):
    assert trace.tool_before_tool(first, second) is False


@then(parsers.parse('message_not_contains "{pat}" is true'))
def msg_not_contains_true(trace, pat):
    assert trace.message_not_contains(pat) is True


@then(parsers.parse('message_not_contains "{pat}" is false'))
def msg_not_contains_false(trace, pat):
    assert trace.message_not_contains(pat) is False


@then(parsers.parse('tool_names returns "{a}", "{b}", "{c}"'))
def tool_names_three(trace, a, b, c):
    assert trace.tool_names() == [a, b, c]
