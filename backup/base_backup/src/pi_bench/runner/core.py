"""Runner core — multi-trial execution with ThreadPoolExecutor."""

import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from pi_bench.evaluator import evaluate
from pi_bench.orchestrator import run as orchestrator_run
from pi_bench.runner.seeds import build_work_queue
from pi_bench.runner.checkpoint import save_incremental, load_checkpoint, make_info


def run_domain(
    domain: dict,
    agent: Any,
    user: Any,
    num_trials: int = 1,
    seed: int | None = None,
    max_concurrency: int = 1,
    save_to: Path | str | None = None,
    resume_from: Path | str | None = None,
    task_ids: list[str] | None = None,
    max_steps: int = 50,
    max_errors: int = 10,
    solo: bool = False,
    observer_factory: Callable[[dict], dict] | None = None,
    scenarios: list[dict] | None = None,
) -> dict:
    """Run all tasks x trials. Returns Results dict.

    When `scenarios` is provided (list of scenario_loader.load() dicts),
    each task carries its own outcomes/label/forbidden_tools and the
    pi-bench evaluation pipeline runs automatically.
    """
    # Build scenario lookup by task id
    scenario_by_task: dict[str, dict] = {}
    if scenarios is not None:
        tasks = [s["task"] for s in scenarios]
        for s in scenarios:
            scenario_by_task[s["task"]["id"]] = s
    else:
        tasks = domain["tasks"]

    # Filter tasks by ID if requested
    if task_ids is not None:
        tasks = [t for t in tasks if t["id"] in task_ids]
        # Also filter scenarios
        scenario_by_task = {
            k: v for k, v in scenario_by_task.items() if k in task_ids
        }

    # Load checkpoint for resume
    completed = set()
    existing_sims = []
    if resume_from is not None:
        checkpoint = load_checkpoint(resume_from)
        if checkpoint is not None:
            existing_sims = checkpoint.get("simulations", [])
            completed = {
                (s["task_id"], s["trial"])
                for s in existing_sims
            }

    # Build work queue
    base_seed = seed if seed is not None else int(time.time())
    work = build_work_queue(tasks, num_trials, base_seed, completed)

    # Execute
    save_path = Path(save_to) if save_to else None
    save_lock = threading.Lock() if save_path else None
    simulations = list(existing_sims)
    new_count = 0

    if max_concurrency <= 1 or len(work) <= 1:
        # Sequential execution
        for task, trial, trial_seed in work:
            scenario = scenario_by_task.get(task["id"])
            sim = _run_one(
                task=task,
                trial=trial,
                seed=trial_seed,
                agent=agent,
                user=user,
                domain=domain,
                max_steps=max_steps,
                max_errors=max_errors,
                solo=solo,
                observer_factory=observer_factory,
                scenario=scenario,
            )
            simulations.append(sim)
            new_count += 1
            if save_path and save_lock:
                save_incremental(simulations, save_path, save_lock)
    else:
        # Parallel execution
        with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
            futures = {
                pool.submit(
                    _run_one,
                    task=task,
                    trial=trial,
                    seed=trial_seed,
                    agent=agent,
                    user=user,
                    domain=domain,
                    max_steps=max_steps,
                    max_errors=max_errors,
                    solo=solo,
                    observer_factory=observer_factory,
                    scenario=scenario_by_task.get(task["id"]),
                ): (task, trial, trial_seed)
                for task, trial, trial_seed in work
            }
            for future in as_completed(futures):
                sim = future.result()
                simulations.append(sim)
                new_count += 1
                if save_path and save_lock:
                    save_incremental(simulations, save_path, save_lock)

    info = make_info(
        domain=domain,
        agent=agent,
        user=user,
        num_trials=num_trials,
        seed=seed,
        max_steps=max_steps,
        max_errors=max_errors,
        max_concurrency=max_concurrency,
        solo=solo,
    )

    result = {
        "info": info,
        "tasks": tasks,
        "simulations": simulations,
    }

    if resume_from is not None:
        result["new_runs_count"] = new_count

    return result


def _run_one(
    task: dict,
    trial: int,
    seed: int,
    agent: Any,
    user: Any,
    domain: dict,
    max_steps: int,
    max_errors: int,
    solo: bool,
    observer_factory: Callable[[dict], dict] | None = None,
    scenario: dict | None = None,
) -> dict:
    """Run a single simulation: orchestrate + evaluate.

    When `scenario` is provided (from scenario_loader.load()), runs the
    full pi-bench evaluation pipeline: trace recording, outcome checking,
    decision resolution, and event flag computation.
    """
    start = time.time()

    # Unpack scenario fields if present
    outcomes = scenario["outcomes"] if scenario else None
    label = scenario["label"] if scenario else None
    forbidden_tools = scenario["forbidden_tools"] if scenario else None
    scenario_id = scenario["scenario_id"] if scenario else None

    # Get environment: from scenario (per-scenario env) or from domain factory
    if scenario is not None:
        env = scenario["env"]
    else:
        get_env = domain["get_environment"]
        env = get_env()

    # Always create trace + observer for pi-bench scenarios
    trace = None
    observer = None
    if scenario is not None:
        from pi_bench.trace import TraceRecorder
        from pi_bench.observer import create_observer
        from pi_bench.evaluator.llm_judge import clear_judge_cache

        clear_judge_cache()
        trace = TraceRecorder()
        observer = create_observer(
            env, trace,
            forbidden_tools=set(forbidden_tools) if forbidden_tools else None,
            mode="audit_only",
        )
    elif observer_factory is not None:
        observer = observer_factory(env)

    sim = orchestrator_run(
        agent=agent,
        user=user,
        env=env,
        task=task,
        max_steps=max_steps,
        max_errors=max_errors,
        seed=seed,
        solo=solo,
        observer=observer,
    )
    sim["trial"] = trial
    sim["seed"] = seed

    # Attach trace for POLICY evaluator (backward compat)
    if observer is not None and trace is None:
        sim["trace"] = observer["trace"]

    # --- Pi-bench evaluation pipeline ---
    if trace is not None and outcomes is not None:
        from pi_bench.decision import CanonicalDecision, resolve
        from pi_bench.evaluator.scenario_checker import check_outcomes, outcomes_to_policy_checks
        from pi_bench.event_flags import compute_flags

        # Record messages to trace for NL assertions
        for msg in sim.get("messages", []):
            if msg.get("role") == "assistant" and msg.get("content"):
                trace.add_message("assistant", msg["content"])
            elif msg.get("role") == "user" and msg.get("content"):
                trace.add_message("user", msg["content"])

        # Evaluate outcomes (two-tier)
        eval_result = check_outcomes(outcomes, trace, sim.get("messages", []), env)

        # Resolve decision
        decision_result = resolve(trace)
        canonical_decision = (
            decision_result.decision
            if isinstance(decision_result, CanonicalDecision)
            else "NONE"
        )

        # Compute event flags
        policy_checks = outcomes_to_policy_checks(outcomes)
        flags = compute_flags(
            scenario_label=label,
            trace=trace,
            canonical_decision=canonical_decision,
            policy_checks=policy_checks,
            forbidden_tools=forbidden_tools,
            messages=sim.get("messages", []),
        )

        sim["scenario_id"] = scenario_id
        sim["label"] = label
        sim["status"] = "completed"
        sim["canonical_decision"] = canonical_decision
        sim["all_passed"] = eval_result["all_passed"]
        sim["semantic_score"] = eval_result["semantic_score"]
        sim["outcome_results"] = eval_result["outcome_results"]
        sim["event_flags"] = {
            "V_r": flags.V_r,
            "UR_r": flags.UR_r,
            "OR_r": flags.OR_r,
            "EA_r": flags.EA_r,
            "AT_r": flags.AT_r,
        }
        sim["tool_calls"] = trace.tool_names()
        sim["duration"] = time.time() - start

    # Backward-compat: old tau2-bench evaluator
    reward_info = evaluate(task, sim, domain)
    sim["reward_info"] = reward_info

    return sim
