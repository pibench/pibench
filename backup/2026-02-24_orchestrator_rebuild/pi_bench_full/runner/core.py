"""Runner core — multi-trial execution with ThreadPoolExecutor."""

import threading
import time
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
) -> dict:
    """Run all tasks x trials. Returns Results dict."""
    tasks = domain["tasks"]

    # Filter tasks by ID if requested
    if task_ids is not None:
        tasks = [t for t in tasks if t["id"] in task_ids]

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
) -> dict:
    """Run a single simulation: orchestrate + evaluate."""
    get_env = domain["get_environment"]
    env = get_env()

    sim = orchestrator_run(
        agent=agent,
        user=user,
        env=env,
        task=task,
        max_steps=max_steps,
        max_errors=max_errors,
        seed=seed,
        solo=solo,
    )
    sim["trial"] = trial
    sim["seed"] = seed

    # Evaluate
    reward_info = evaluate(task, sim, domain)
    sim["reward_info"] = reward_info

    return sim
