#!/usr/bin/env python3
"""Quick scenario test harness — run one scenario, show detailed results.

Usage:
    # Test with a real model (solo mode)
    python scripts/test_scenario.py scenarios/finra/scen_011_cooperative_structuring.json --model gpt-4o

    # Test with Claude
    python scripts/test_scenario.py scenarios/helpdesk/scen_030_standard_password_reset.json --model anthropic/claude-haiku-4-5-20251001

    # Dry run — just load and validate checks (no LLM call)
    python scripts/test_scenario.py scenarios/finra/scen_011_cooperative_structuring.json --dry-run

    # Run N times for reproducibility check
    python scripts/test_scenario.py scenarios/finra/scen_011_cooperative_structuring.json --model gpt-4o --repeat 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from pi_bench.evaluator.report import build_report, format_report
from pi_bench.scenario_loader import load
from pi_bench.environment import get_tool_schemas


def dry_run(scenario_path: str) -> None:
    """Load scenario, validate checks, show structure. No LLM call."""
    loaded = load(scenario_path)
    task = loaded["task"]
    env = loaded["env"]
    tools = get_tool_schemas(env)
    tool_names = {t["name"] for t in tools}

    sid = loaded["scenario_id"]
    label = loaded["label"]
    col = task.get("leaderboard_primary", "?")
    criteria = task.get("evaluation_criteria", {})
    checks = criteria.get("policy_checks", [])
    state_checks = criteria.get("state_field_checks", [])
    nl_checks = criteria.get("nl_judge_checks", [])

    print(f"Scenario: {sid}")
    print(f"Label: {label}  Column: {col}")
    print(f"Tools available ({len(tools)}): {sorted(tool_names)}")
    print(f"Checks: {len(checks)} policy + {len(state_checks)} state + {len(nl_checks)} NL judge")
    print()

    # Validate checks reference real tools
    issues = []
    for c in checks:
        ctype = c.get("type", "")
        if ctype in ("tool_called", "tool_not_called", "tool_called_with", "tool_called_min_times"):
            tn = c.get("tool_name", "")
            if tn and tn not in tool_names:
                issues.append(f"  {c['outcome_id']}: tool '{tn}' not in domain tools")
        elif ctype == "tool_called_any":
            for tn in c.get("tool_names", []):
                if tn not in tool_names:
                    issues.append(f"  {c['outcome_id']}: tool '{tn}' not in domain tools")
        elif ctype == "tool_before_tool":
            for key in ("first_tool", "second_tool"):
                tn = c.get(key, "")
                if tn and tn not in tool_names:
                    issues.append(f"  {c['outcome_id']}: tool '{tn}' not in domain tools")

    # Check for conflicting checks
    called = {c["tool_name"] for c in checks if c.get("type") == "tool_called"}
    not_called = {c["tool_name"] for c in checks if c.get("type") == "tool_not_called"}
    conflicts = called & not_called
    if conflicts:
        issues.append(f"  CONFLICT: tools both called and not_called: {conflicts}")

    # Check ordering references exist
    for c in checks:
        if c.get("type") == "tool_before_tool":
            first = c.get("first_tool", "")
            second = c.get("second_tool", "")
            if first and first not in called:
                issues.append(f"  {c['outcome_id']}: ordering references '{first}' but no tool_called check for it")
            if second and second not in called:
                issues.append(f"  {c['outcome_id']}: ordering references '{second}' but no tool_called check for it")

    # Print check summary by dimension
    dim_map = {
        "decision_equals": "Decision",
        "tool_not_called": "Permissibility",
        "tool_called": "Outcomes",
        "tool_called_with": "Outcomes",
        "tool_called_any": "Outcomes",
        "tool_called_min_times": "Outcomes",
        "tool_before_tool": "Ordering",
    }

    dims = {}
    for c in checks:
        dim = dim_map.get(c.get("type", ""), "Other")
        dims.setdefault(dim, []).append(c)

    print("Check breakdown:")
    for dim in ["Decision", "Permissibility", "Outcomes", "Ordering", "Other"]:
        if dim in dims:
            print(f"  {dim}: {len(dims[dim])}")
            for c in dims[dim]:
                print(f"    {c['outcome_id']}: {c['type']} {c.get('tool_name', c.get('first_tool', c.get('equals', '')))}")
    if state_checks:
        print(f"  State: {len(state_checks)}")
    if nl_checks:
        print(f"  Semantic: {len(nl_checks)}")

    print()
    if issues:
        print(f"ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(issue)
    else:
        print("No issues found. Checks are consistent.")


def run_scenario(scenario_path: str, model: str, max_steps: int, seed: int) -> dict:
    """Run one scenario and return the report."""
    from pi_bench.agents.litellm_agent import LiteLLMAgent
    from pi_bench.evaluator import evaluate
    from pi_bench.observer import create_observer
    from pi_bench.orchestrator.core import run as orchestrator_run
    from pi_bench.trace import TraceRecorder

    loaded = load(scenario_path)
    task = loaded["task"]
    env = loaded["env"]
    label = loaded["label"]
    sid = loaded["scenario_id"]
    forbidden = loaded["forbidden_tools"]

    agent = LiteLLMAgent(model_name=model)
    trace = TraceRecorder()
    observer = create_observer(
        env, trace,
        forbidden_tools=set(forbidden) if forbidden else None,
        mode="audit_only",
    )

    start = time.time()
    sim = orchestrator_run(
        agent=agent, user=None, env=env, task=task,
        max_steps=max_steps, seed=seed, solo=True, observer=observer,
    )
    duration = time.time() - start

    sim["trace"] = trace
    sim["env"] = env

    # Populate trace messages for decision fallback
    for msg in sim.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content")
        if role == "assistant" and content:
            trace.add_message("assistant", content)
        elif role == "user" and content:
            trace.add_message("user", content)

    eval_result = evaluate(task, sim, domain={
        "get_environment": lambda t=None, p=scenario_path: load(p)["env"]
    })

    report = build_report(
        scenario_id=sid,
        label=label,
        leaderboard_primary=task.get("leaderboard_primary", ""),
        eval_result=eval_result,
        termination_reason=sim.get("termination_reason", ""),
        step_count=sim.get("step_count", 0),
        tool_calls=trace.tool_names(),
    )
    report["duration"] = round(duration, 2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Test a single pi-bench scenario")
    parser.add_argument("scenario", help="Path to scenario JSON")
    parser.add_argument("--model", default=None, help="LLM model (omit for dry-run)")
    parser.add_argument("--max-steps", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true", help="Just validate, no LLM call")
    parser.add_argument("--repeat", type=int, default=1, help="Run N times for reproducibility")
    args = parser.parse_args()

    if args.dry_run or args.model is None:
        dry_run(args.scenario)
        return

    results = []
    for trial in range(args.repeat):
        seed = args.seed + trial * 7919
        print(f"{'='*70}")
        print(f"Trial {trial + 1}/{args.repeat} (seed={seed})")
        print(f"{'='*70}")

        report = run_scenario(args.scenario, args.model, args.max_steps, seed)
        results.append(report)

        print(format_report(report))
        print(f"  Duration: {report['duration']}s")
        print()

    if args.repeat > 1:
        passed = sum(1 for r in results if r["all_passed"])
        print(f"{'='*70}")
        print(f"REPRODUCIBILITY: {passed}/{args.repeat} passed ({passed/args.repeat*100:.0f}%)")
        print(f"{'='*70}")

    sys.exit(0 if all(r["all_passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
