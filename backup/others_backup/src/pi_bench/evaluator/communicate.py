"""COMMUNICATE evaluator — check required info strings in agent messages.

Matches tau2-bench behavior: all-or-nothing scoring. All required
information strings must appear in agent messages for the evaluator
to return 1.0. Any missing string → 0.0.
"""

import logging

from pi_bench.types import extract_message_content

logger = logging.getLogger(__name__)


def evaluate_communicate(communicate_info: list[str], trajectory: list[dict]) -> float:
    """Check that required information strings appear in agent messages.

    Case-insensitive substring matching. Commas stripped before comparison.
    Returns 1.0 if ALL required strings found, 0.0 if any missing.
    """
    if not communicate_info:
        return 1.0

    agent_text = ""
    for msg in trajectory:
        if msg.get("role") == "assistant" and msg.get("content"):
            agent_text += " " + extract_message_content(msg)

    agent_text_clean = agent_text.replace(",", "").lower()

    for info in communicate_info:
        info_clean = info.replace(",", "").lower()
        if info_clean not in agent_text_clean:
            logger.info("COMMUNICATE: missing required string: '%s'", info[:80])
            return 0.0

    logger.debug("COMMUNICATE: all %d required strings found", len(communicate_info))
    return 1.0
