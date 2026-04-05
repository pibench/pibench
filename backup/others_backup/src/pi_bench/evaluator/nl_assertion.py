"""NL_ASSERTION evaluator — delegates to llm_judge for semantic assertion checking.

Evaluates natural language assertions against a conversation trajectory
using the same LLM judge used by scenario_checker's nl_assertion_llm_judge.
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
        passed, detail = judge_nl_assertion(assistant_text, assertion, "YES")
        logger.debug("NL_ASSERTION: %s — %s", assertion[:60], detail)
        if not passed:
            return 0.0

    return 1.0


