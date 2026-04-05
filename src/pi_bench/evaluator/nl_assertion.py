"""NL_ASSERTION evaluator — delegates to llm_judge for semantic assertion checking.

Evaluates natural language assertions against a conversation trajectory
using the same LLM judge used for nl_assertion_llm_judge outcome checks.
"""

from __future__ import annotations

import logging

from pi_bench.evaluator.llm_judge import judge_nl_assertion
from pi_bench.types import extract_message_content

logger = logging.getLogger(__name__)


def evaluate_nl_assertions(
    nl_assertions: list[str],
    trajectory: list[dict],
    generate_fn=None,  # noqa: ARG001 — kept for API compat
    cache: dict[tuple[str, str], tuple[bool, str]] | None = None,
) -> float:
    """Check semantic assertions against trajectory using the LLM judge.

    Args:
        nl_assertions: Natural language assertions to evaluate.
        trajectory: Full message trajectory from the simulation.
        generate_fn: Deprecated — kept for API compatibility, ignored.

    Returns:
        1.0 if all assertions met, 0.0 if any unmet.
    """
    if not nl_assertions:
        return 1.0

    # Build assistant text from trajectory
    assistant_text = "\n\n---\n\n".join(
        extract_message_content(msg)
        for msg in trajectory
        if msg.get("role") == "assistant" and msg.get("content")
    )

    if not assistant_text:
        logger.warning("NL_ASSERTION: no assistant messages in trajectory — scoring 0.0")
        return 0.0

    # Evaluate each assertion individually via llm_judge
    for assertion in nl_assertions:
        passed, detail = judge_nl_assertion(
            assistant_text,
            assertion,
            "YES",
            cache=cache,
        )
        logger.debug("NL_ASSERTION: %s — %s", assertion[:60], detail)
        if not passed:
            return 0.0

    return 1.0


def evaluate_nl_judge_checks(
    llm_judge_outcomes: list[dict],
    messages: list[dict],
    cache: dict[tuple[str, str], tuple[bool, str]] | None = None,
) -> list[dict]:
    """Run LLM judge outcomes. Returns list of {outcome_id, type, passed, detail} dicts."""
    results = []
    for outcome in llm_judge_outcomes:
        passed, detail = _check_llm_judge(outcome, messages, cache=cache)
        results.append({
            "outcome_id": outcome.get("outcome_id", "unknown"),
            "type": "NL_JUDGE",
            "passed": passed,
            "detail": detail,
        })
    return results


def _check_llm_judge(
    outcome: dict,
    messages: list[dict],
    cache: dict[tuple[str, str], tuple[bool, str]] | None = None,
) -> tuple[bool, str]:
    """Use an LLM judge to answer a yes/no question about assistant messages.

    Outcome spec:
      judge_question: clear yes/no question about the agent's behavior
      expected_answer: "YES" or "NO"
      scope: "assistant_messages" (default) or "final_assistant_message"
    """
    scope = outcome.get("scope", "assistant_messages")
    question = outcome.get("judge_question", "")

    # B2: require expected_answer explicitly
    expected = outcome.get("expected_answer")
    if expected is None:
        return False, "nl_assertion_llm_judge: missing expected_answer"

    if not question:
        return False, "nl_assertion_llm_judge: missing judge_question"

    assistant_msgs = _get_scoped_messages(messages, scope)
    if not assistant_msgs:
        return False, "nl_assertion_llm_judge: no assistant messages found"

    assistant_text = "\n\n---\n\n".join(assistant_msgs)
    return judge_nl_assertion(assistant_text, question, expected, cache=cache)


def _get_scoped_messages(messages: list[dict], scope: str) -> list[str]:
    """Extract message content based on scope.

    Handles both string content and Anthropic-format list content blocks.
    """
    assistant_msgs = []

    if scope == "final_assistant_message":
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                assistant_msgs.append(extract_message_content(msg))
                break
    else:
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                assistant_msgs.append(extract_message_content(msg))

    return assistant_msgs
