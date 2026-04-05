"""Run pi-bench scenarios against an LLM model or custom agent.

Usage:
    # Model testing (backward compat):
    python -m pi_bench.run_scenarios --model gpt-5.2 --scenarios-dir workspace/scenarios/

    # Custom agent:
    python -m pi_bench.run_scenarios --agent-class my_module:MyAgent --scenarios-dir workspace/scenarios/

    # Dry run:
    python -m pi_bench.run_scenarios --model gpt-5.2 --scenarios-dir workspace/scenarios/ --dry-run
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pi_bench.evaluator.llm_judge import set_judge_model
from pi_bench.evaluator.scenario_validator import validate_scenario
from pi_bench.metrics import compute_metrics, compute_repeatability, format_metrics_summary
from pi_bench.runner.core import run_domain
from pi_bench.scenario_loader import discover_scenarios, load

logger = logging.getLogger(__name__)


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
    """Build a structured conversation log for observability."""
    tool_names = [t.get("name", "?") for t in tool_schemas]

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

    trace_entries = []
    if trace is not None:
        trace_entries = [
            {
                "step": e.step_index,
                "tool": e.tool_name,
                "args": e.arguments,
                "result": e.result_content[:500],
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
            "policy_text": policy_text[:2000],
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


def _load_agent(agent_class_str: str, agent_args: list[str] | None = None) -> Any:
    """Dynamically import and instantiate an agent from 'module:ClassName' string."""
    if ":" not in agent_class_str:
        print(f"Error: --agent-class must be 'module:ClassName', got '{agent_class_str}'",
              file=sys.stderr)
        sys.exit(1)

    module_path, class_name = agent_class_str.rsplit(":", 1)
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error: cannot import module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)

    cls = getattr(mod, class_name, None)
    if cls is None:
        print(f"Error: class '{class_name}' not found in '{module_path}'", file=sys.stderr)
        sys.exit(1)

    # Parse agent args
    kwargs = {}
    if agent_args:
        for arg in agent_args:
            if "=" not in arg:
                print(f"Error: --agent-arg must be key=value, got '{arg}'", file=sys.stderr)
                sys.exit(1)
            key, value = arg.split("=", 1)
            kwargs[key] = value

    return cls(**kwargs)


def print_summary(results: list[dict]) -> None:
    """Print a summary table of results."""
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r.get("all_passed"))
    errors = sum(1 for r in results if r.get("status") == "error")
    failed = total - passed - errors

    by_label: dict[str, list[dict]] = {}
    for r in results:
        label = r.get("label", "?")
        by_label.setdefault(label, []).append(r)

    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
    print()

    for label in ["ALLOW", "DENY", "ESCALATE"]:
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

    metrics = compute_metrics(results)
    repeatability = compute_repeatability(results)
    print(format_metrics_summary(metrics, repeatability))


def save_report(results: list[dict], output_path: Path) -> None:
    """Save full results as JSON report + per-scenario conversation logs."""
    conversation_logs = {}
    results_for_report = []
    for r in results:
        log = r.pop("conversation_log", None)
        if log:
            conversation_logs[r.get("scenario_id", "unknown")] = log
        results_for_report.append(r)

    metrics = compute_metrics(results_for_report)
    repeatability = compute_repeatability(results_for_report)

    capability_profile = {
        axis_id: {"passed": s.passed, "total": s.total, "rate": s.rate}
        for axis_id, s in metrics.by_axis.items()
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(results_for_report),
        "passed": sum(1 for r in results_for_report if r.get("all_passed")),
        "failed": sum(1 for r in results_for_report if r.get("status") == "completed" and not r.get("all_passed")),
        "errors": sum(1 for r in results_for_report if r.get("status") == "error"),
        "compliance_rate": metrics.compliance_rate,
        "capability_profile": capability_profile,
        "by_domain": metrics.by_domain,
        "repeatability": repeatability["aggregate"] if repeatability else None,
        "results": results_for_report,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {output_path}")

    if conversation_logs:
        logs_dir = output_path.parent / output_path.stem.replace("scenario_run_", "logs_")
        logs_dir.mkdir(parents=True, exist_ok=True)

        for scenario_id, log in conversation_logs.items():
            log_path = logs_dir / f"{scenario_id}.json"
            with open(log_path, "w") as f:
                json.dump(log, f, indent=2, default=str)

        combined_path = logs_dir / "_all_conversations.json"
        with open(combined_path, "w") as f:
            json.dump(conversation_logs, f, indent=2, default=str)

        print(f"Conversation logs saved to: {logs_dir}/ ({len(conversation_logs)} scenarios)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pi-bench scenarios against an LLM model or custom agent")
    parser.add_argument("--model", default=None, help="Model name for litellm")
    parser.add_argument("--agent-class", help="module:ClassName (e.g., my_agents:MyAgent)")
    parser.add_argument("--agent-arg", action="append", help="key=value args passed to agent constructor")
    parser.add_argument("--scenarios-dir", type=Path, help="Directory containing scenario JSON files")
    parser.add_argument("--scenario", type=Path, help="Single scenario JSON file to run")
    parser.add_argument("--workspace-root", type=Path, help="Workspace root (default: inferred)")
    parser.add_argument("--max-steps", type=int, default=50, help="Max simulation steps (default: 50)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--num-trials", type=int, default=1, help="Trials per scenario (default: 1)")
    parser.add_argument("--output", type=Path, help="Output JSON report path")
    parser.add_argument("--dry-run", action="store_true", help="Load scenarios without running LLM")
    parser.add_argument("--concurrency", type=int, default=10, help="Max parallel scenarios (default: 10)")
    parser.add_argument("--thinking", type=int, default=0, help="Enable extended thinking with budget_tokens")
    parser.add_argument("--judge-model", type=str, default="gpt-4o-mini", help="Model for LLM judge (default: gpt-4o-mini)")
    args = parser.parse_args()

    # Resolve agent
    if args.agent_class and args.model:
        print("Error: specify --agent-class or --model, not both.", file=sys.stderr)
        sys.exit(1)
    if not args.agent_class and not args.model:
        # Default to model for backward compat
        args.model = "gpt-5.2"

    # Determine workspace root
    workspace_root = args.workspace_root
    if workspace_root is None:
        cwd = Path.cwd()
        if (cwd / "workspace").is_dir():
            workspace_root = cwd / "workspace"
        elif cwd.name == "workspace":
            workspace_root = cwd
        else:
            workspace_root = cwd

    # Discover scenarios
    if args.scenario:
        scenario_paths = [args.scenario]
    elif args.scenarios_dir:
        scenario_paths = discover_scenarios(args.scenarios_dir)
    else:
        default_dir = workspace_root / "scenarios"
        if default_dir.is_dir():
            scenario_paths = discover_scenarios(default_dir)
        else:
            print("No scenarios found. Use --scenarios-dir or --scenario.", file=sys.stderr)
            sys.exit(1)

    if not scenario_paths:
        print("No valid pibench_scenario_v1 files found.", file=sys.stderr)
        sys.exit(1)

    # Dry-run mode: just load and print scenario info
    if args.dry_run:
        results = []
        for i, path in enumerate(scenario_paths, 1):
            loaded = load(path, workspace_root=workspace_root)
            scenario_id = loaded["scenario_id"]
            print(f"\n[{i}/{len(scenario_paths)}] {scenario_id}", flush=True)
            print(f"  Domain: {loaded['env']['domain_name']}")
            print(f"  Label: {loaded['label']}")
            print(f"  Tools: {len(loaded['env']['tool_schemas'])}")
            print(f"  Outcomes: {len(loaded['outcomes'])}")
            results.append({
                "scenario_id": scenario_id,
                "label": loaded["label"],
                "status": "dry_run",
                "all_passed": None,
            })
        print_summary(results)
        return

    # Build agent
    if args.agent_class:
        agent = _load_agent(args.agent_class, args.agent_arg)
        agent_name = args.agent_class
    else:
        from pi_bench.agents.litellm_agent import LiteLLMAgent
        thinking_config = None
        if args.thinking > 0:
            thinking_config = {"type": "enabled", "budget_tokens": args.thinking}
        agent = LiteLLMAgent(model_name=args.model, thinking=thinking_config)
        agent_name = args.model

    print(f"Found {len(scenario_paths)} scenarios")
    print(f"Agent: {agent_name}")
    print(f"Workspace: {workspace_root}")

    if args.judge_model != "gpt-4o-mini":
        set_judge_model(args.judge_model)
        print(f"Judge model: {args.judge_model}")
    print(f"Concurrency: {args.concurrency}")
    if args.num_trials > 1:
        print(f"Trials per scenario: {args.num_trials}")

    # Validate scenarios and load them
    loaded_scenarios = []
    for path in scenario_paths:
        scenario_data = json.loads(Path(path).read_text())
        validation_errors = validate_scenario(scenario_data)
        if validation_errors:
            scenario_id = path.stem
            for err in validation_errors:
                logger.error("Validation error in %s: %s", scenario_id, err)
            continue
        loaded = load(path, workspace_root=workspace_root)
        # Attach capability_axes from raw JSON
        loaded["capability_axes"] = scenario_data.get("capability_axes", [])
        loaded_scenarios.append(loaded)

    if not loaded_scenarios:
        print("No valid scenarios after validation.", file=sys.stderr)
        sys.exit(1)

    # Build a dummy domain dict for backward compat with make_info()
    domain = {
        "name": loaded_scenarios[0]["env"]["domain_name"],
        "tasks": [s["task"] for s in loaded_scenarios],
        "get_environment": lambda: loaded_scenarios[0]["env"],
    }

    # Run via unified runner
    run_result = run_domain(
        domain=domain,
        agent=agent,
        user=None,
        num_trials=args.num_trials,
        seed=args.seed,
        max_concurrency=args.concurrency,
        max_steps=args.max_steps,
        solo=True,
        scenarios=loaded_scenarios,
    )

    # Extract per-scenario results from simulations
    results = []
    for sim in run_result["simulations"]:
        # Attach capability_axes from loaded scenario
        sid = sim.get("scenario_id", sim.get("task_id", ""))
        for s in loaded_scenarios:
            if s["scenario_id"] == sid:
                sim["capability_axes"] = s.get("capability_axes", [])
                break
        results.append(sim)

    # Output
    print_summary(results)

    output_path = args.output
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = workspace_root / "reports" / f"scenario_run_{agent_name}_{ts}.json"

    save_report(results, output_path)


if __name__ == "__main__":
    main()
