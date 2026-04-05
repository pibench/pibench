"""Step definitions for communicate_evaluator.feature."""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from pi_bench.evaluator.communicate import evaluate_communicate

scenarios("../features/communicate_evaluator.feature")


@pytest.fixture
def trajectory():
    return []


@pytest.fixture
def score():
    return 0.0


@given(parsers.re(r'assistant messages with string content containing "(?P<text>[^"]+)"'))
def string_messages(trajectory, text):
    trajectory.append({"role": "assistant", "content": f"Our {text} states that returns are accepted within 30 days."})
    return trajectory


@given(parsers.re(r'assistant messages in Anthropic list format containing "(?P<text>[^"]+)"'))
def list_messages(trajectory, text):
    trajectory.append({
        "role": "assistant",
        "content": [
            {"type": "text", "text": f"Our {text} states that returns are accepted within 30 days."},
        ],
    })
    return trajectory


@when(parsers.re(r'COMMUNICATE evaluates for "(?P<required>[^"]+)"'), target_fixture="score")
def evaluate(trajectory, required):
    return evaluate_communicate([required], trajectory)


@then("the COMMUNICATE score is 1.0")
def score_is_one(score):
    assert score == 1.0


@then("the COMMUNICATE score is 0.0")
def score_is_zero(score):
    assert score == 0.0
