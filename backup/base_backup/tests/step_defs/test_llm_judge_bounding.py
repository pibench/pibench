"""Step definitions for llm_judge_bounding.feature."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import scenarios, given, when, then

from pi_bench.evaluator.llm_judge import (
    clear_judge_cache,
    judge_nl_assertion,
)

scenarios("../features/llm_judge_bounding.feature")

_TEXT = "The agent refused the refund request."
_QUESTION = "Did the agent refuse?"
_EXPECTED = "YES"


def _mock_response(content: str):
    """Create a mock litellm response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before each test."""
    clear_judge_cache()
    yield
    clear_judge_cache()


# --- Retry: success on second attempt ---

@given("the LLM judge returns an unparseable response then a valid YES")
def mock_unparseable_then_valid():
    pass


@when("I call judge_nl_assertion with retry scenario", target_fixture="result")
def call_judge_retry():
    responses = [
        _mock_response("I cannot determine this"),
        _mock_response('{"answer": "YES", "reasoning": "Agent refused"}'),
    ]
    with patch("pi_bench.evaluator.llm_judge.litellm") as mock_llm:
        mock_llm.completion = MagicMock(side_effect=responses)
        passed, detail = judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)
    return {"passed": passed, "detail": detail}


@then("the result is passed with a valid detail")
def result_passed(result):
    assert result["passed"] is True
    assert "llm_judge:" in result["detail"]


# --- Retry exhausted ---

@given("the LLM judge returns unparseable responses on both attempts")
def mock_always_unparseable():
    pass


@when("I call judge_nl_assertion with exhausted retry scenario", target_fixture="result")
def call_judge_double_fail():
    responses = [
        _mock_response("garbage output"),
        _mock_response("still garbage"),
    ]
    with patch("pi_bench.evaluator.llm_judge.litellm") as mock_llm:
        mock_llm.completion = MagicMock(side_effect=responses)
        passed, detail = judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)
    return {"passed": passed, "detail": detail}


@then('the result is failed with detail containing "unparseable after retry"')
def result_unparseable(result):
    assert result["passed"] is False
    assert "unparseable after retry" in result["detail"]


# --- Cache hit ---

@given("the LLM judge returns YES on first call")
def mock_yes():
    pass


@when("I call judge_nl_assertion twice with same text and question", target_fixture="result")
def call_judge_twice_cached():
    resp = _mock_response('{"answer": "YES", "reasoning": "Agent refused"}')
    with patch("pi_bench.evaluator.llm_judge.litellm") as mock_llm:
        mock_llm.completion = MagicMock(return_value=resp)
        judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)
        judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)
        call_ct = mock_llm.completion.call_count
    return {"call_count": call_ct}


@then("the LLM was called only once")
def called_once(result):
    assert result["call_count"] == 1


# --- Cache cleared ---

@given("I call judge_nl_assertion once to populate cache")
def populate_cache():
    resp = _mock_response('{"answer": "YES", "reasoning": "Agent refused"}')
    with patch("pi_bench.evaluator.llm_judge.litellm") as mock_llm:
        mock_llm.completion = MagicMock(return_value=resp)
        judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)


@when("I clear the judge cache and call again", target_fixture="result")
def clear_and_call():
    clear_judge_cache()
    resp = _mock_response('{"answer": "YES", "reasoning": "Agent refused"}')
    with patch("pi_bench.evaluator.llm_judge.litellm") as mock_llm:
        mock_llm.completion = MagicMock(return_value=resp)
        judge_nl_assertion(_TEXT, _QUESTION, _EXPECTED)
        call_ct = mock_llm.completion.call_count
    return {"call_count": call_ct}


@then("the LLM made a new call after cache clear")
def called_after_clear(result):
    # If cache was still active, call_count would be 0
    assert result["call_count"] == 1
