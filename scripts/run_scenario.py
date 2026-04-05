#!/usr/bin/env python3
"""Run a single scenario against the LiteLLMAgent and print results.

Usage:
    python scripts/run_scenario.py scenarios/retail/scen_040_final_sale_restocking_tradeoff.json
    python scripts/run_scenario.py scenarios/retail/scen_040_final_sale_restocking_tradeoff.json --model gpt-4o
"""

from __future__ import annotations

import argparse
import json
import sys

from pi_bench.agents.litellm_agent import LiteLLMAgent
from pi_bench.decision import resolve, CanonicalDecision
from pi_bench.evaluator import evaluate
from pi_bench.event_flags import compute_flags
from pi_bench.observer import create_observer
from pi_bench.orchestrator import run as orchestrator_run
from pi_bench.scenario_loader import load
from pi_bench.trace import TraceRecorder
from pi_bench.users.scripted_user import ScriptedUser


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a pi-bench scenario")
    parser.add_argument("scenario_path", help="Path to scenario JSON file")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model name for the agent")
    parser.add_argument("--max-steps", type=int, default=40, help="Max simulation steps")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--observer-mode", default="audit_only", help="audit_only or hard_gate")
    args = parser.parse_args()

    # Load scenario
    loaded = load(args.scenario_path)
    task = loaded["task"]
    env = loaded["env"]
    label = loaded["label"]
    scenario_id = loaded["scenario_id"]
    forbidden_tools = loaded["forbidden_tools"]

    print(f"Scenario: {scenario_id}")
    print(f"Label: {label}")
    print(f"Agent model: {args.model}")
    print(f"Observer: {args.observer_mode}")

    # Set up agent
    agent = LiteLLMAgent(model_name=args.model)

    # Set up user simulator
    user = ScriptedUser()

    # Set up trace and observer
    trace = TraceRecorder()
    observer = create_observer(
        env, trace,
        forbidden_tools=set(forbidden_tools) if forbidden_tools else None,
        mode=args.observer_mode,
    )

    # Run simulation
    print(f"\nRunning simulation (max {args.max_steps} steps)...")
    sim = orchestrator_run(
        agent=agent,
        user=user,
        env=env,
        task=task,
        max_steps=args.max_steps,
        seed=args.seed,
        observer=observer,
    )

    sim["trace"] = trace
    sim["env"] = env

    # Print conversation
    messages = sim.get("messages", [])
    print(f"\nTermination: {sim.get('termination_reason', '?')}")
    print(f"Steps: {sim.get('step_count', 0)}")
    print(f"Duration: {sim.get('duration', 0):.2f}s")

    print(f"\n{'='*60}")
    print("CONVERSATION")
    print(f"{'='*60}")
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        if role == "system":
            print(f"\n[SYSTEM] {content[:120]}...")
        elif role == "assistant":
            if tool_calls:
                print(f"\n--- Step {i}: AGENT (tool calls) ---")
                for tc in tool_calls:
                    args_str = json.dumps(tc.get("arguments", {}), indent=2)
                    print(f"  -> {tc['name']}({args_str})")
            if content:
                print(f"\n--- Step {i}: AGENT ---")
                print(f"  {content}")
        elif role == "user":
            print(f"\n--- Step {i}: USER ---")
            print(f"  {content}")
        elif role == "tool":
            result = msg.get("content", "")
            name = msg.get("name", "?")
            error = msg.get("error", False)
            tag = "ERROR" if error else "OK"
            display = result[:300] + "..." if len(str(result)) > 300 else result
            print(f"  <- [{tag}] {name}: {display}")

    # Evaluate
    eval_result = evaluate(task, sim, domain={"get_environment": lambda: load(args.scenario_path)["env"]})

    # Resolve decision
    decision_result = resolve(trace)
    canonical_decision = (
        decision_result.decision
        if isinstance(decision_result, CanonicalDecision)
        else "NONE"
    )

    # Compute event flags
    policy_checks = task["evaluation_criteria"].get("policy_checks", [])
    flags = compute_flags(
        scenario_label=label,
        trace=trace,
        canonical_decision=canonical_decision,
        policy_checks=policy_checks,
        forbidden_tools=forbidden_tools,
        messages=messages,
    )

    # Print results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"  Canonical decision: {canonical_decision}")
    print(f"  All passed: {eval_result['all_passed']}")
    print(f"  Semantic score: {eval_result['semantic_score']:.2f}")
    print(f"  Event flags: V={flags.V_r} UR={flags.UR_r} OR={flags.OR_r} EA={flags.EA_r} AT={flags.AT_r}")

    print(f"\n  Outcome checks:")
    for r in eval_result["outcome_results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"    [{status}] {r.get('outcome_id', r.get('type', '?'))}: {r.get('detail', '')}")

    print(f"\n  Tools called: {trace.tool_names()}")

    sys.exit(0 if eval_result["all_passed"] else 1)


if __name__ == "__main__":
    main()
