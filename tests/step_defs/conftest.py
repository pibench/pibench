"""Shared fixtures for BDD step definitions."""

import pytest

from pi_bench.evaluator import llm_judge


@pytest.fixture(autouse=True)
def _offline_judge_model():
    """Keep tests offline: judge tests mock litellm, so pin a litellm judge model.

    The real default routes the judge through OmniGent (a live model call).
    """
    previous = llm_judge.get_judge_model()
    llm_judge.set_judge_model("gpt-5.2")
    yield
    llm_judge.set_judge_model(previous)
