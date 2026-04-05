"""PolicyCheckEngine — deterministic evaluation of expected outcomes against a trace.

Takes expected outcomes and a trace, produces verdicts with evidence
pointers. Every check is a pure function. No LLM involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pi_bench.trace import TraceRecorder


@dataclass(frozen=True)
class ExpectedOutcome:
    """One expected behavioral check for a scenario."""

    outcome_id: str
    check_type: str  # tool_called, tool_not_called, tool_called_with,
    #                   tool_before_tool, state_field, message_not_contains
    params: dict[str, Any]


@dataclass(frozen=True)
class EvidencePointer:
    """Points to the exact trace location of a failure."""

    step_index: int | None
    tool_call_id: str | None
    outcome_id: str


@dataclass(frozen=True)
class Verdict:
    """Result of evaluating one expected outcome."""

    outcome_id: str
    passed: bool
    evidence: EvidencePointer | None = None


def evaluate(
    trace: TraceRecorder,
    expected_outcomes: list[ExpectedOutcome],
    post_state: dict[str, Any] | None = None,
) -> list[Verdict]:
    """Evaluate all expected outcomes against a trace.

    Returns one Verdict per outcome. A scenario passes only when
    ALL verdicts pass.
    """
    verdicts = []
    for outcome in expected_outcomes:
        passed, step_index = _check(trace, outcome, post_state)
        evidence = None
        if not passed:
            evidence = EvidencePointer(
                step_index=step_index,
                tool_call_id=None,
                outcome_id=outcome.outcome_id,
            )
        verdicts.append(Verdict(
            outcome_id=outcome.outcome_id,
            passed=passed,
            evidence=evidence,
        ))
    return verdicts


def scenario_passed(verdicts: list[Verdict]) -> bool:
    """A scenario passes only when ALL verdicts pass."""
    return all(v.passed for v in verdicts)


def _check(
    trace: TraceRecorder,
    outcome: ExpectedOutcome,
    post_state: dict[str, Any] | None,
) -> tuple[bool, int | None]:
    """Run a single check. Returns (passed, step_index_of_failure)."""
    p = outcome.params

    match outcome.check_type:
        case "tool_called":
            passed = trace.tool_called(p["tool_name"])
            return passed, None

        case "tool_not_called":
            tool_name = p["tool_name"]
            if trace.tool_called(tool_name):
                entry = trace.find_entry(tool_name)
                return False, entry.step_index if entry else None
            return True, None

        case "tool_called_with":
            tool_name = p["tool_name"]
            args = p.get("arguments", {})
            passed = trace.tool_called_with(tool_name, **args)
            return passed, None

        case "tool_before_tool":
            passed = trace.tool_before_tool(p["first"], p["second"])
            return passed, None

        case "state_field":
            if post_state is None:
                return False, None
            actual = _read_nested(post_state, p["path"])
            return actual == p["expected_value"], None

        case "message_not_contains":
            pattern = p["pattern"]
            if trace.message_not_contains(pattern):
                return True, None
            # Find the step index of the offending message
            for i, msg in enumerate(trace.messages):
                if msg.role == "assistant" and pattern in msg.content:
                    return False, i
            return False, None

        case _:
            return False, None


def _read_nested(state: dict, path: str) -> Any:
    """Read a dot-separated path from a nested dict.

    Example: "tasks.task_1.status" -> state["tasks"]["task_1"]["status"]
    """
    current: Any = state
    for key in path.split("."):
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current
