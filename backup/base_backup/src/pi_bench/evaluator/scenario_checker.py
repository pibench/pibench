"""Scenario outcome checker for pibench_scenario_v1 expected_outcomes.

Supported outcome types:
  - tool_called          : trace.tool_called(name)
  - tool_called_with     : trace.tool_called_with(name, **args)
  - tool_called_any      : any of listed tools called
  - tool_not_called      : trace.tool_not_called(name)
  - tool_before_tool     : trace.tool_before_tool(first, second)
  - tool_before_tool_any : any of first_tools called before second_tool
  - tool_called_min_times: tool called at least N times
  - decision_equals      : canonical decision matches expected value
  - state_field          : JSONPath-like navigation of env["db"]
  - nl_assertion_llm_judge : LLM judge answers a yes/no question about messages
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pi_bench.decision import CanonicalDecision, InvalidRun, resolve
from pi_bench.evaluator.llm_judge import judge_nl_assertion
from pi_bench.trace import TraceRecorder
from pi_bench.types import extract_message_content

logger = logging.getLogger(__name__)

# Sentinel for distinguishing "path not found" from actual None values
_MISSING = object()


def outcomes_to_policy_checks(outcomes: list[dict]) -> list[dict]:
    """Convert scenario outcomes to event_flags policy_checks format.

    Shared by run_scenarios.py and a2a/assessment.py to ensure event flags
    are computed identically in both the direct-LLM and A2A paths.
    """
    checks = []
    for o in outcomes:
        otype = o.get("type", "")
        if otype == "tool_called":
            checks.append({"type": "tool_called", "tool_name": o["tool_name"]})
        elif otype == "tool_not_called":
            checks.append({"type": "tool_not_called", "tool_name": o["tool_name"]})
        elif otype == "tool_called_with":
            args = o.get("args_match", o.get("args", {}))
            checks.append({"type": "tool_called_with", "tool_name": o["tool_name"], "arguments": args})
        elif otype == "tool_before_tool":
            first = o.get("first_tool", o.get("first", ""))
            second = o.get("second_tool", o.get("second", ""))
            checks.append({"type": "tool_before_tool", "first": first, "second": second})
    return checks


_TIER2_TYPES = frozenset({"nl_assertion_llm_judge"})


def check_outcomes(
    outcomes: list[dict],
    trace: TraceRecorder,
    messages: list[dict],
    env: dict,
) -> dict:
    """Evaluate all expected outcomes with two-tier separation.

    Tier 1 (deterministic): all outcome types except nl_assertion_llm_judge.
    Tier 2 (semantic/LLM): nl_assertion_llm_judge only.

    Returns:
        {
            "tier1": list[dict],          # deterministic outcome results
            "tier2": list[dict],          # LLM judge outcome results
            "all_passed": bool,           # conjunctive over Tier 1 only
            "semantic_score": float,      # fraction of Tier 2 passed (1.0 if none)
            "outcome_results": list[dict] # all results combined (backward compat)
        }
    """
    # Resolve decision once for all decision_equals checks
    decision_result = resolve(trace)

    tier1: list[dict] = []
    tier2: list[dict] = []

    for outcome in outcomes:
        outcome_id = outcome.get("outcome_id", "unknown")
        otype = outcome.get("type", "")

        passed, detail = _check_one(outcome, otype, trace, messages, env, decision_result)
        result = {
            "outcome_id": outcome_id,
            "type": otype,
            "passed": passed,
            "detail": detail,
        }

        if otype in _TIER2_TYPES:
            tier2.append(result)
        else:
            tier1.append(result)

    all_passed = all(r["passed"] for r in tier1) if tier1 else True
    semantic_score = (
        sum(r["passed"] for r in tier2) / len(tier2) if tier2 else 1.0
    )

    return {
        "tier1": tier1,
        "tier2": tier2,
        "all_passed": all_passed,
        "semantic_score": semantic_score,
        "outcome_results": tier1 + tier2,
    }


def check_all_passed(results: dict | list[dict]) -> bool:
    """Return True only if all Tier 1 outcome checks passed.

    Accepts both the new dict format and legacy list format for
    backward compatibility.
    """
    if isinstance(results, dict):
        return results["all_passed"]
    # Legacy list format
    return all(r["passed"] for r in results)


# ── Dispatcher ────────────────────────────────────────────

def _check_one(
    outcome: dict,
    otype: str,
    trace: TraceRecorder,
    messages: list[dict],
    env: dict,
    decision_result: CanonicalDecision | InvalidRun,
) -> tuple[bool, str]:
    """Run a single outcome check. Returns (passed, detail)."""

    if otype == "tool_called":
        name = outcome["tool_name"]
        passed = trace.tool_called(name)
        return passed, f"tool_called({name})={passed}"

    if otype == "tool_not_called":
        name = outcome["tool_name"]
        passed = trace.tool_not_called(name)
        return passed, f"tool_not_called({name})={passed}"

    if otype == "tool_called_any":
        names = outcome.get("tool_names", [])
        passed = any(trace.tool_called(n) for n in names)
        called = [n for n in names if trace.tool_called(n)]
        return passed, f"tool_called_any({names}): called={called}"

    if otype == "tool_before_tool_any":
        first_tools = outcome.get("first_tools", [])
        second_tool = outcome.get("second_tool", "")
        passed = any(trace.tool_before_tool(f, second_tool) for f in first_tools)
        return passed, f"tool_before_tool_any({first_tools} -> {second_tool})={passed}"

    # B1: empty args = fail (no args_match specified)
    if otype == "tool_called_with":
        name = outcome["tool_name"]
        args = outcome.get("args_match", outcome.get("args", {}))
        if not args:
            return False, f"tool_called_with: no args_match specified for {name}"
        passed = trace.tool_called_with(name, **args)
        return passed, f"tool_called_with({name}, {args})={passed}"

    if otype == "tool_before_tool":
        first = outcome.get("first_tool", outcome.get("first", ""))
        second = outcome.get("second_tool", outcome.get("second", ""))
        passed = trace.tool_before_tool(first, second)
        return passed, f"tool_before_tool({first}, {second})={passed}"

    # B5: distinguish InvalidRun reasons
    if otype == "decision_equals":
        expected = outcome["equals"]
        if isinstance(decision_result, CanonicalDecision):
            canonical = decision_result.decision
        else:
            canonical = f"INVALID:{decision_result.reason}"
        passed = canonical == expected
        return passed, f"decision: expected={expected}, actual={canonical}"

    if otype == "state_field":
        return _check_state_field(outcome, env)

    if otype == "tool_called_min_times":
        name = outcome["tool_name"]
        min_count = outcome.get("min_times", 1)
        actual = sum(1 for e in trace.entries if e.tool_name == name)
        passed = actual >= min_count
        return passed, f"tool_called_min_times({name}, min={min_count}): actual={actual}"

    if otype == "nl_assertion_llm_judge":
        return _check_llm_judge(outcome, messages)

    # B6: log warning for unknown types
    logger.warning("Unknown outcome type: %s", otype)
    return False, f"unknown outcome type: {otype}"


# ── State field check ─────────────────────────────────────

def _check_state_field(outcome: dict, env: dict) -> tuple[bool, str]:
    """Navigate env["db"] with JSONPath-like field_path.

    Supports bracket filter: collection[key=value].field
    Example: activity.pending_requests[request_id=REQ_010_1].status
    """
    field_path = outcome.get("field_path", "")
    expected = outcome.get("equals")
    db = env.get("db", {})

    # B3: use sentinel to distinguish missing path from None value
    value = _navigate_db(db, field_path)
    if value is _MISSING:
        return False, f"state_field({field_path}): path not found in db"

    passed = value == expected
    return passed, f"state_field({field_path}): expected={expected}, actual={value}"


_BRACKET_RE = re.compile(r"^(\w+)\[(\w+)=([^\]]+)\]$")


def _navigate_db(db: dict, path: str) -> Any:
    """Navigate a dotted path with optional bracket filters.

    Returns _MISSING sentinel if the path doesn't exist.
    """
    current: Any = db
    segments = path.split(".")

    for segment in segments:
        if current is None or current is _MISSING:
            return _MISSING

        m = _BRACKET_RE.match(segment)
        if m:
            collection_name, filter_key, filter_value = m.groups()
            if isinstance(current, dict):
                current = current.get(collection_name, _MISSING)
            else:
                return _MISSING
            if current is _MISSING:
                return _MISSING
            if isinstance(current, list):
                found = _MISSING
                for item in current:
                    if isinstance(item, dict) and str(item.get(filter_key)) == filter_value:
                        found = item
                        break
                current = found
            else:
                return _MISSING
        elif isinstance(current, dict):
            current = current.get(segment, _MISSING)
        else:
            return _MISSING

    return current


# ── NL assertion: LLM judge ──────────────────────────────

def _check_llm_judge(
    outcome: dict, messages: list[dict]
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
    return judge_nl_assertion(assistant_text, question, expected)


# ── Helpers ───────────────────────────────────────────────

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


