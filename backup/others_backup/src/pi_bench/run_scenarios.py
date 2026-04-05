"""Run pi-bench scenarios against an LLM model.

Usage:
    python -m pi_bench.run_scenarios --model gpt-5.2 --scenarios-dir workspace/scenarios/
    python -m pi_bench.run_scenarios --model gpt-5.2 --scenario workspace/scenarios/retail/scen_020_standard_refund.json
    python -m pi_bench.run_scenarios --model gpt-5.2 --scenarios-dir workspace/scenarios/ --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pi_bench.agents.litellm_agent import LiteLLMAgent
from pi_bench.decision import CanonicalDecision, resolve
from pi_bench.environment import get_policy
from pi_bench.evaluator.llm_judge import clear_judge_cache, set_judge_model
from pi_bench.evaluator.scenario_checker import check_outcomes, outcomes_to_policy_checks
from pi_bench.event_flags import compute_flags
from pi_bench.metrics import compute_metrics, compute_repeatability, format_metrics_summary
from pi_bench.observer import create_observer
from pi_bench.orchestrator.core import run
from pi_bench.evaluator.scenario_validator import validate_scenario
from pi_bench.scenario_loader import discover_scenarios, load
from pi_bench.trace import TraceRecorder

logger = logging.getLogger(__name__)


def run_scenario(
    scenario_path: Path,
    agent: Any,
    workspace_root: Path,
    max_steps: int = 50,
    seed: int | None = None,
) -> dict:
    """Run a single scenario. Returns a result dict."""
    start = time.time()

    # Load scenario
    loaded = load(scenario_path, workspace_root=workspace_root)
    task = loaded["task"]
    env = loaded["env"]
    user = loaded["user"]
    outcomes = loaded["outcomes"]
    label = loaded["label"]
    scenario_id = loaded["scenario_id"]
    forbidden_tools = loaded["forbidden_tools"]

    # Validate scenario before running
    scenario_data = json.loads(Path(scenario_path).read_text())
    taxonomy_primary = scenario_data.get("taxonomy", {}).get("primary", "")
    validation_errors = validate_scenario(scenario_data)
    if validation_errors:
        for err in validation_errors:
            logger.error("Validation error in %s: %s", scenario_id, err)
        return {
            "scenario_id": scenario_id,
            "label": label,
            "status": "validation_error",
            "error": "; ".join(validation_errors),
            "duration": time.time() - start,
            "outcome_results": [],
            "all_passed": False,
        }

    # Clear LLM judge cache for this scenario
    clear_judge_cache()

    # Create trace and observer
    trace = TraceRecorder()
    observer = create_observer(
        env, trace, forbidden_tools=set(forbidden_tools), mode="audit_only"
    )

    # Run simulation
    try:
        sim = run(
            agent=agent,
            user=user,
            env=env,
            task=task,
            max_steps=max_steps,
            seed=seed,
            observer=observer,
        )
    except Exception as e:
        return {
            "scenario_id": scenario_id,
            "label": label,
            "status": "error",
            "error": str(e),
            "duration": time.time() - start,
            "outcome_results": [],
            "all_passed": False,
        }

    # Record assistant messages to trace for NL assertions
    for msg in sim.get("messages", []):
        if msg.get("role") == "assistant" and msg.get("content"):
            trace.add_message("assistant", msg["content"])
        elif msg.get("role") == "user" and msg.get("content"):
            trace.add_message("user", msg["content"])

    # Evaluate outcomes (two-tier)
    eval_result = check_outcomes(outcomes, trace, sim.get("messages", []), env)
    all_passed = eval_result["all_passed"]
    outcome_results = eval_result["outcome_results"]
    semantic_score = eval_result["semantic_score"]

    # Resolve decision
    decision_result = resolve(trace)
    canonical_decision = (
        decision_result.decision
        if isinstance(decision_result, CanonicalDecision)
        else "NONE"
    )

    # Compute event flags
    # Convert outcomes to policy_checks format for compute_flags
    policy_checks = outcomes_to_policy_checks(outcomes)
    flags = compute_flags(
        scenario_label=label,
        trace=trace,
        canonical_decision=canonical_decision,
        policy_checks=policy_checks,
        forbidden_tools=forbidden_tools,
        messages=sim.get("messages", []),
    )

    duration = time.time() - start

    # Build conversation log for observability
    conversation_log = _build_conversation_log(
        scenario_id=scenario_id,
        label=label,
        policy_text=get_policy(env),
        task_description=task["description"],
        tool_schemas=env.get("tool_schemas", []),
        messages=sim.get("messages", []),
        trace=trace,
        outcome_results=outcome_results,
        canonical_decision=canonical_decision,
        all_passed=all_passed,
    )

    return {
        "scenario_id": scenario_id,
        "label": label,
        "status": "completed",
        "termination_reason": sim.get("termination_reason", "unknown"),
        "step_count": sim.get("step_count", 0),
        "canonical_decision": canonical_decision,
        "all_passed": all_passed,
        "semantic_score": semantic_score,
        "outcome_results": outcome_results,
        "taxonomy_primary": taxonomy_primary,
        "event_flags": {
            "V_r": flags.V_r,
            "UR_r": flags.UR_r,
            "OR_r": flags.OR_r,
            "EA_r": flags.EA_r,
            "AT_r": flags.AT_r,
        },
        "duration": duration,
        "tool_calls": trace.tool_names(),
        "message_count": len(sim.get("messages", [])),
        "conversation_log": conversation_log,
    }


def _build_conversation_log(
    scenario_id: str,
    label: str,
    policy_text: str,
    task_description: str,
    tool_schemas: list[dict],
    messages: list[dict],
    trace: Any,
    outcome_results: list[dict],
    canonical_decision: str,
    all_passed: bool,
) -> dict:
    """Build a structured conversation log for observability.

    Captures everything needed to verify whether a failure is a real model
    failure or a test harness bug: system prompt, available tools, and the
    full message-by-message conversation thread.
    """
    tool_names = [t.get("name", "?") for t in tool_schemas]

    # Build the step-by-step thread
    thread = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        entry: dict[str, Any] = {"turn": i, "role": role}

        if role in ("assistant", "user"):
            if msg.get("content"):
                entry["content"] = msg["content"]
            if msg.get("tool_calls"):
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", "?"),
                        "name": tc.get("name", "?"),
                        "arguments": tc.get("arguments", {}),
                    }
                    for tc in msg["tool_calls"]
                ]
            if msg.get("cost"):
                entry["cost"] = msg["cost"]

        elif role == "tool":
            entry["tool_call_id"] = msg.get("id", "?")
            entry["tool_name"] = msg.get("name", "?")
            entry["content"] = msg.get("content", "")
            entry["error"] = msg.get("error", False)

        elif role == "multi_tool":
            entry["tool_results"] = [
                {
                    "tool_call_id": sub.get("id", "?"),
                    "tool_name": sub.get("name", "?"),
                    "content": sub.get("content", ""),
                    "error": sub.get("error", False),
                }
                for sub in msg.get("tool_messages", [])
            ]

        elif role == "system":
            entry["content"] = msg.get("content", "")

        thread.append(entry)

    # Trace entries (tool calls with state changes)
    trace_entries = [
        {
            "step": e.step_index,
            "tool": e.tool_name,
            "args": e.arguments,
            "result": e.result_content[:500],  # truncate long results
            "error": e.result_error,
            "state_changed": e.state_changed,
            "blocked": e.blocked,
        }
        for e in trace.entries
    ]

    return {
        "scenario_id": scenario_id,
        "label": label,
        "system_prompt": {
            "policy_text": policy_text[:2000],  # first 2K chars
            "task_description": task_description,
        },
        "available_tools": tool_names,
        "thread": thread,
        "trace_entries": trace_entries,
        "evaluation": {
            "canonical_decision": canonical_decision,
            "all_passed": all_passed,
            "outcome_results": outcome_results,
        },
    }


def _run_one(
    path: Path,
    model: str,
    workspace_root: Path,
    max_steps: int,
    seed: int | None,
    thinking: dict | None = None,
) -> dict:
    """Run a single scenario with its own agent instance (thread-safe)."""
    agent = LiteLLMAgent(model_name=model, thinking=thinking)
    return run_scenario(
        scenario_path=path,
        agent=agent,
        workspace_root=workspace_root,
        max_steps=max_steps,
        seed=seed,
    )


def run_all(
    scenarios: list[Path],
    model: str,
    workspace_root: Path,
    max_steps: int = 50,
    seed: int | None = None,
    dry_run: bool = False,
    concurrency: int = 10,
    thinking: dict | None = None,
) -> list[dict]:
    """Run all scenarios concurrently. Returns list of result dicts."""
    if dry_run:
        results = []
        for i, path in enumerate(scenarios, 1):
            loaded = load(path, workspace_root=workspace_root)
            scenario_id = path.stem
            print(f"\n[{i}/{len(scenarios)}] {scenario_id}", flush=True)
            print(f"  Domain: {loaded['env']['domain_name']}")
            print(f"  Label: {loaded['label']}")
            print(f"  Tools: {len(loaded['env']['tool_schemas'])}")
            print(f"  Outcomes: {len(loaded['outcomes'])}")
            results.append({
                "scenario_id": loaded["scenario_id"],
                "label": loaded["label"],
                "status": "dry_run",
                "all_passed": None,
            })
        return results

    # Run scenarios concurrently
    results: list[dict] = [{}] * len(scenarios)
    completed = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {
            executor.submit(_run_one, path, model, workspace_root, max_steps, seed, thinking): i
            for i, path in enumerate(scenarios)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            path = scenarios[idx]
            completed += 1

            try:
                result = future.result()
            except Exception as e:
                result = {
                    "scenario_id": path.stem,
                    "label": "?",
                    "status": "error",
                    "error": str(e),
                    "duration": 0,
                    "outcome_results": [],
                    "all_passed": False,
                }

            results[idx] = result

            # Print inline summary
            status_icon = "PASS" if result.get("all_passed") else "FAIL"
            if result.get("status") == "error":
                status_icon = "ERR"
            print(f"\n[{completed}/{len(scenarios)}] {result.get('scenario_id', path.stem)}", flush=True)
            print(f"  [{status_icon}] decision={result.get('canonical_decision', '?')} "
                  f"steps={result.get('step_count', '?')} "
                  f"duration={result.get('duration', 0):.1f}s")

            for oc in result.get("outcome_results", []):
                icon = "+" if oc["passed"] else "-"
                print(f"    [{icon}] {oc['outcome_id']}: {oc['detail']}")

    return results


def print_summary(results: list[dict]) -> None:
    """Print a summary table of results."""
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r.get("all_passed"))
    errors = sum(1 for r in results if r.get("status") == "error")
    failed = total - passed - errors

    # Group by label
    by_label: dict[str, list[dict]] = {}
    for r in results:
        label = r.get("label", "?")
        by_label.setdefault(label, []).append(r)

    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
    print()

    for label in ["ALLOW", "ALLOW-CONDITIONAL", "DENY", "ESCALATE"]:
        group = by_label.get(label, [])
        if not group:
            continue
        label_passed = sum(1 for r in group if r.get("all_passed"))
        print(f"  {label}: {label_passed}/{len(group)} passed")

    print()
    print(f"{'Scenario':<50} {'Label':<10} {'Decision':<10} {'Result':<8} {'Sem':<6} {'Time':<8}")
    print("-" * 92)

    for r in results:
        sid = r.get("scenario_id", "?")[:48]
        label = r.get("label", "?")
        decision = r.get("canonical_decision", "?")
        if r.get("status") == "error":
            result_str = "ERR"
        elif r.get("status") == "dry_run":
            result_str = "DRY"
        elif r.get("all_passed"):
            result_str = "PASS"
        else:
            result_str = "FAIL"
        duration = r.get("duration", 0)
        sem = r.get("semantic_score")
        sem_str = f"{sem:.1f}" if sem is not None else "-"
        print(f"  {sid:<48} {label:<10} {decision:<10} {result_str:<8} {sem_str:<6} {duration:>5.1f}s")

    # Capability profile
    metrics = compute_metrics(results)
    repeatability = compute_repeatability(results)
    print(format_metrics_summary(metrics, repeatability))



def save_report(results: list[dict], output_path: Path) -> None:
    """Save full results as JSON report + per-scenario conversation logs."""
    # Extract conversation logs before saving (keep report JSON smaller)
    conversation_logs = {}
    results_for_report = []
    for r in results:
        log = r.pop("conversation_log", None)
        if log:
            conversation_logs[r.get("scenario_id", "unknown")] = log
        results_for_report.append(r)

    # Compute metrics for the report
    metrics = compute_metrics(results_for_report)
    repeatability = compute_repeatability(results_for_report)

    task_profile = {
        task_name: {"passed": s.passed, "total": s.total, "rate": s.rate}
        for task_name, s in metrics.by_task.items()
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(results_for_report),
        "passed": sum(1 for r in results_for_report if r.get("all_passed")),
        "failed": sum(1 for r in results_for_report if r.get("status") == "completed" and not r.get("all_passed")),
        "errors": sum(1 for r in results_for_report if r.get("status") == "error"),
        "compliance_rate": metrics.compliance_rate,
        "overall_score": metrics.overall_score,
        "task_profile": task_profile,
        "by_domain": metrics.by_domain,
        "repeatability": repeatability["aggregate"] if repeatability else None,
        "results": results_for_report,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {output_path}")

    # Save conversation logs
    if conversation_logs:
        logs_dir = output_path.parent / output_path.stem.replace("scenario_run_", "logs_")
        logs_dir.mkdir(parents=True, exist_ok=True)

        for scenario_id, log in conversation_logs.items():
            log_path = logs_dir / f"{scenario_id}.json"
            with open(log_path, "w") as f:
                json.dump(log, f, indent=2, default=str)

        # Also save a combined log
        combined_path = logs_dir / "_all_conversations.json"
        with open(combined_path, "w") as f:
            json.dump(conversation_logs, f, indent=2, default=str)

        print(f"Conversation logs saved to: {logs_dir}/ ({len(conversation_logs)} scenarios)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pi-bench scenarios against an LLM model")
    parser.add_argument("--model", default="gpt-5.2", help="Model name for litellm (default: gpt-5.2)")
    parser.add_argument("--scenarios-dir", type=Path, help="Directory containing scenario JSON files")
    parser.add_argument("--scenario", type=Path, help="Single scenario JSON file to run")
    parser.add_argument("--workspace-root", type=Path, help="Workspace root (default: inferred)")
    parser.add_argument("--max-steps", type=int, default=50, help="Max simulation steps (default: 50)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--output", type=Path, help="Output JSON report path")
    parser.add_argument("--dry-run", action="store_true", help="Load scenarios without running LLM")
    parser.add_argument("--concurrency", type=int, default=10, help="Max parallel scenarios (default: 10)")
    parser.add_argument("--thinking", type=int, default=0, help="Enable extended thinking with budget_tokens (e.g. 4096)")
    parser.add_argument("--judge-model", type=str, default="gpt-4o-mini", help="Model for LLM judge NL assertions (default: gpt-4o-mini)")
    args = parser.parse_args()

    # Determine workspace root
    workspace_root = args.workspace_root
    if workspace_root is None:
        # Try to find workspace/ relative to cwd
        cwd = Path.cwd()
        if (cwd / "workspace").is_dir():
            workspace_root = cwd / "workspace"
        elif cwd.name == "workspace":
            workspace_root = cwd
        else:
            workspace_root = cwd

    # Discover scenarios
    if args.scenario:
        scenarios = [args.scenario]
    elif args.scenarios_dir:
        scenarios = discover_scenarios(args.scenarios_dir)
    else:
        # Default: look for workspace/scenarios/
        default_dir = workspace_root / "scenarios"
        if default_dir.is_dir():
            scenarios = discover_scenarios(default_dir)
        else:
            print("No scenarios found. Use --scenarios-dir or --scenario.", file=sys.stderr)
            sys.exit(1)

    if not scenarios:
        print("No valid pibench_scenario_v1 files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(scenarios)} scenarios")
    print(f"Model: {args.model}")
    print(f"Workspace: {workspace_root}")

    # Run
    thinking_config = None
    if args.thinking > 0:
        thinking_config = {"type": "enabled", "budget_tokens": args.thinking}
        print(f"Thinking: enabled (budget={args.thinking})")
    if args.judge_model != "gpt-4o-mini":
        set_judge_model(args.judge_model)
        print(f"Judge model: {args.judge_model}")
    print(f"Concurrency: {args.concurrency}")
    results = run_all(
        scenarios=scenarios,
        model=args.model,
        workspace_root=workspace_root,
        max_steps=args.max_steps,
        seed=args.seed,
        dry_run=args.dry_run,
        concurrency=args.concurrency,
        thinking=thinking_config,
    )

    # Output
    print_summary(results)

    output_path = args.output
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = workspace_root / "reports" / f"scenario_run_{args.model}_{ts}.json"

    save_report(results, output_path)


if __name__ == "__main__":
    main()
