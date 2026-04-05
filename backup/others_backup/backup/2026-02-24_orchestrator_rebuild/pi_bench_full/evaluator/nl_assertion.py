"""NL_ASSERTION evaluator — LLM-based semantic assertion checking."""

import json
from collections.abc import Callable

SYSTEM_PROMPT = """
TASK
- You will be given a list of expected outcomes and a conversation trajectory.
- The conversation is between an agent and a customer (user).
- Your job is to evaluate whether the agent satisfies each of the expected outcomes.
- Grade each expected outcome individually.

FORMAT
- Your response must be a JSON object with a "results" array.
- Each result has:
  - "expectedOutcome": repeat the expectation from the input
  - "reasoning": a short explanation for your classification
  - "metExpectation": true if the agent satisfies the expected outcome, false otherwise

Example:
{
    "results": [
        {
            "expectedOutcome": "Agent explains the refund policy",
            "reasoning": "The agent clearly stated the 30-day refund window",
            "metExpectation": true
        }
    ]
}
""".strip()


def evaluate_nl_assertions(
    nl_assertions: list[str],
    trajectory: list[dict],
    generate_fn: Callable[[list[dict]], str],
) -> float:
    """Check semantic assertions against trajectory using an LLM judge.

    Args:
        nl_assertions: Natural language assertions to evaluate.
        trajectory: Full message trajectory from the simulation.
        generate_fn: Callable that takes (messages: list[dict]) -> str.
            Returns the raw text response from the LLM.

    Returns:
        1.0 if all assertions met, 0.0 if any unmet.
    """
    if not nl_assertions:
        return 1.0

    checks = _call_judge(nl_assertions, trajectory, generate_fn)

    if not checks:
        return 0.0

    all_met = all(c.get("metExpectation", False) for c in checks)
    return 1.0 if all_met else 0.0


def _call_judge(
    nl_assertions: list[str],
    trajectory: list[dict],
    generate_fn: Callable[[list[dict]], str],
) -> list[dict]:
    """Send trajectory + assertions to LLM, parse structured response."""
    trajectory_str = "\n".join(
        f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
        for msg in trajectory
        if msg.get("content")
    )

    user_prompt = (
        f"conversation:\n{trajectory_str}\n\n"
        f"expectedOutcomes:\n{nl_assertions}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response_text = generate_fn(messages)
        result_data = json.loads(response_text)
        return result_data.get("results", [])
    except (json.JSONDecodeError, TypeError, KeyError):
        return []
