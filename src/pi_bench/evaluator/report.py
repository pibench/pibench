"""Failure report generator — builds structured per-scenario reports.

Classifies evaluation checks into 5 dimensions and produces a
human-readable failure report showing exactly where and why the
agent failed.

Designed to be bolt-on: the evaluator produces raw results, this
module structures them for reporting. Can feed into dashboards,
JSON exports, or terminal output.
"""

from __future__ import annotations

from typing import Any


# Check type → evaluation dimension
_DIMENSION_MAP = {
    "decision_equals": "decision",
    "tool_not_called": "permissibility",
    "tool_called": "outcomes",
    "tool_called_with": "outcomes",
    "tool_called_any": "outcomes",
    "tool_called_min_times": "outcomes",
    "tool_before_tool": "ordering",
    "tool_before_tool_any": "ordering",
    "communicate": "communication",
    "db_replay": "state",
    "env_assertion": "state",
    "state_field": "state",
    "state_count": "state",
    "message_not_contains": "permissibility",
    "escalation_attempted": "outcomes",
    "nl_assertion_llm_judge": "semantic",
    "NL_JUDGE": "semantic",
    "NL_ASSERTION": "semantic",
}

_DIMENSION_LABELS = {
    "decision": "Decision Correctness",
    "permissibility": "Action Permissibility",
    "outcomes": "Required Outcomes",
    "ordering": "Temporal Constraints",
    "state": "State Correctness",
    "communication": "Communication",
    "semantic": "Semantic Quality",
}

_DIMENSION_ORDER = [
    "decision",
    "permissibility",
    "outcomes",
    "ordering",
    "state",
    "communication",
    "semantic",
]


# ── Outcome / procedure layers ───────────────────────────
#
# Every check result is tagged with a layer:
#   outcome   — what the world looks like at the end (decision, final state)
#   procedure — how the agent got there (which tools, in what order, what it said)
# A check may set "layer" explicitly; otherwise the default below applies.

VALID_LAYERS = frozenset({"outcome", "procedure"})

_OUTCOME_LAYER_TYPES = frozenset({
    "decision_equals",
    "state_field",
    "state_count",
    "db_replay",
    "env_assertion",
})

# Result types that are Tier-2 (semantic) and excluded from layer aggregation.
_LAYER_TIER2_TYPES = frozenset({"NL_ASSERTION", "NL_JUDGE"})


def default_layer(check_type: str) -> str:
    """Default layer for a check/result type."""
    return "outcome" if check_type in _OUTCOME_LAYER_TYPES else "procedure"


def layer_fields(check: dict | None, result_type: str) -> dict[str, str]:
    """Return {"layer", "layer_source"} for a check, honoring an explicit layer."""
    explicit = (check or {}).get("layer")
    if explicit in VALID_LAYERS:
        return {"layer": explicit, "layer_source": "explicit"}
    check_type = result_type or (check or {}).get("type", "")
    return {"layer": default_layer(check_type), "layer_source": "default"}


def classify_layers(outcome_results: list[dict]) -> dict[str, dict[str, Any]]:
    """Aggregate Tier-1 results per layer.

    Returns {"outcome": {...}, "procedure": {...}} where each entry is
    {"passed": bool | None, "total": n, "passed_count": k}; passed is None
    when the layer has no Tier-1 checks.
    """
    layers: dict[str, dict[str, Any]] = {}
    for layer in ("outcome", "procedure"):
        members = [
            r for r in outcome_results
            if r.get("type") not in _LAYER_TIER2_TYPES
            and r.get("layer", default_layer(r.get("type", ""))) == layer
        ]
        passed_count = sum(1 for r in members if r.get("passed"))
        layers[layer] = {
            "passed": (passed_count == len(members)) if members else None,
            "total": len(members),
            "passed_count": passed_count,
        }
    return layers


def is_unsafe_success(layers: dict[str, dict[str, Any]]) -> bool:
    """Outcome layer passed while the procedure layer failed (both non-empty)."""
    outcome = layers.get("outcome", {})
    procedure = layers.get("procedure", {})
    return (
        outcome.get("total", 0) > 0
        and procedure.get("total", 0) > 0
        and outcome.get("passed") is True
        and procedure.get("passed") is False
    )


def classify_dimensions(outcome_results: list[dict]) -> dict[str, dict[str, Any]]:
    """Group raw outcome results into reporting dimensions."""
    dimensions: dict[str, dict[str, Any]] = {}
    for dim in _DIMENSION_ORDER:
        dimensions[dim] = {
            "name": _DIMENSION_LABELS[dim],
            "passed": True,
            "checks": [],
            "failed_checks": [],
        }

    for check in outcome_results:
        check_type = check.get("type", "")
        dim = _DIMENSION_MAP.get(check_type, "outcomes")
        dimensions[dim]["checks"].append(check)
        if not check.get("passed", False):
            dimensions[dim]["passed"] = False
            dimensions[dim]["failed_checks"].append(check)

    return dimensions


def build_report(
    scenario_id: str,
    label: str,
    leaderboard_primary: str,
    eval_result: dict,
    termination_reason: str = "",
    step_count: int = 0,
    tool_calls: list[str] | None = None,
) -> dict:
    """Build a structured failure report from evaluation results.

    Returns a dict with:
    - summary: one-line pass/fail
    - dimensions: per-dimension pass/fail with failed checks
    - trajectory: tool call sequence
    - all_checks: full list of check results
    """
    outcome_results = eval_result.get("outcome_results", [])
    all_passed = eval_result.get("all_passed", False)
    deterministic_score = eval_result.get("deterministic_score", 1.0 if all_passed else 0.0)
    semantic_score = eval_result.get("semantic_score", 1.0)

    dimensions = eval_result.get("dimensions") or classify_dimensions(outcome_results)

    # Build summary
    failed_dims = [d for d in _DIMENSION_ORDER if not dimensions[d]["passed"] and dimensions[d]["checks"]]
    passed_dims = [d for d in _DIMENSION_ORDER if dimensions[d]["passed"] and dimensions[d]["checks"]]

    has_semantic_failures = semantic_score < 1.0

    if all_passed and not has_semantic_failures:
        summary = f"PASS — all checks passed across {len(passed_dims)} dimensions"
    elif all_passed and has_semantic_failures:
        summary = f"PASS (with semantic warnings) — tier-1 passed but semantic checks failed ({semantic_score:.0%})"
    elif failed_dims:
        summary = f"FAIL — failed in: {', '.join(_DIMENSION_LABELS[d] for d in failed_dims)}"
    else:
        summary = "FAIL — run did not complete enough deterministic checks to score"

    return {
        "scenario_id": scenario_id,
        "label": label,
        "leaderboard_primary": leaderboard_primary,
        "all_passed": all_passed,
        "deterministic_score": deterministic_score,
        "layers": eval_result.get("layers"),
        "unsafe_success": eval_result.get("unsafe_success"),
        "semantic_score": semantic_score,
        "summary": summary,
        "termination_reason": termination_reason,
        "step_count": step_count,
        "tool_calls": tool_calls or [],
        "dimensions": dimensions,
        "total_checks": len(outcome_results),
        "passed_checks": sum(1 for c in outcome_results if c.get("passed")),
        "failed_checks": sum(1 for c in outcome_results if not c.get("passed")),
    }


def format_report(report: dict) -> str:
    """Format a report as human-readable text for terminal output."""
    lines = []

    # Header
    status = "PASS" if report["all_passed"] else "FAIL"
    lines.append(f"[{status}] {report['scenario_id']}")
    lines.append(f"  Label: {report['label']}  Column: {report['leaderboard_primary']}")
    lines.append(f"  Termination: {report['termination_reason']}  Steps: {report['step_count']}")
    lines.append(f"  Checks: {report['passed_checks']}/{report['total_checks']} passed")
    lines.append(
        f"  Deterministic: {report.get('deterministic_score', 0.0):.2f}"
        f"  Semantic: {report['semantic_score']:.2f}"
    )
    layers = report.get("layers") or {}
    if any((layers.get(name) or {}).get("total") for name in ("outcome", "procedure")):
        parts = []
        for name in ("outcome", "procedure"):
            layer = layers.get(name) or {}
            if layer.get("total"):
                parts.append(f"{name.capitalize()}: {layer.get('passed_count', 0)}/{layer['total']}")
        if report.get("unsafe_success"):
            parts.append("UNSAFE SUCCESS")
        lines.append("  " + "  ".join(parts))

    # Tool call trajectory
    if report["tool_calls"]:
        lines.append(f"  Trajectory: {' → '.join(report['tool_calls'])}")

    # Per-dimension results
    lines.append("")
    for dim in _DIMENSION_ORDER:
        d = report["dimensions"][dim]
        if not d["checks"]:
            continue

        tag = "PASS" if d["passed"] else "FAIL"
        total = len(d["checks"])
        passed = sum(1 for c in d["checks"] if c.get("passed"))
        lines.append(f"  [{tag}] {d['name']} ({passed}/{total})")

        # Show failed checks with details
        for check in d["failed_checks"]:
            oid = check.get("outcome_id", "?")
            detail = check.get("detail", "")
            notes = check.get("notes", "")
            lines.append(f"    ✗ {oid}: {detail}")
            if notes:
                lines.append(f"      Why: {notes}")

    return "\n".join(lines)


def format_batch_summary(reports: list[dict]) -> str:
    """Format a summary of multiple scenario reports."""
    lines = []

    total = len(reports)
    passed = sum(1 for r in reports if r["all_passed"])
    failed = total - passed

    lines.append(f"\n{'='*70}")
    lines.append(f"FAILURE ANALYSIS — {failed}/{total} scenarios failed")
    lines.append(f"{'='*70}")

    if not failed:
        lines.append("  All scenarios passed.")
        return "\n".join(lines)

    # Aggregate failure dimensions
    dim_failures: dict[str, int] = {d: 0 for d in _DIMENSION_ORDER}
    for r in reports:
        if r["all_passed"]:
            continue
        for dim in _DIMENSION_ORDER:
            if not r["dimensions"][dim]["passed"] and r["dimensions"][dim]["checks"]:
                dim_failures[dim] += 1

    lines.append("")
    lines.append("  Failure breakdown by dimension:")
    for dim in _DIMENSION_ORDER:
        count = dim_failures[dim]
        if count > 0:
            lines.append(f"    {_DIMENSION_LABELS[dim]:<30} {count:>3} scenarios failed")

    # Show each failed scenario
    lines.append("")
    lines.append("  Failed scenarios:")
    for r in reports:
        if r["all_passed"]:
            continue
        failed_dims = [
            _DIMENSION_LABELS[d]
            for d in _DIMENSION_ORDER
            if not r["dimensions"][d]["passed"] and r["dimensions"][d]["checks"]
        ]
        lines.append(f"    {r['scenario_id']:<45} {', '.join(failed_dims)}")

    return "\n".join(lines)
