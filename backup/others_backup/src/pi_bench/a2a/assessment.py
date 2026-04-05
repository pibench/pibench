"""Assessment engine — runs pi-bench scenarios against a purple agent via A2A.

Unlike the Archive 9 version that only supported the finance domain, this
engine uses scenario_loader.load() to support all domains (finra, retail,
helpdesk) and uses scenario_checker.check_outcomes() for the richer
11-outcome-type evaluation pipeline including LLM judge NL assertions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pi_bench.a2a.purple_adapter import A2APurpleAgent
from pi_bench.decision import CanonicalDecision, resolve
from pi_bench.evaluator.llm_judge import clear_judge_cache
from pi_bench.evaluator.scenario_checker import check_outcomes, outcomes_to_policy_checks
from pi_bench.evaluator.scenario_validator import validate_scenario
from pi_bench.event_flags import compute_flags
from pi_bench.observer import create_observer
from pi_bench.orchestrator.core import run as orchestrator_run
from pi_bench.scenario_loader import discover_scenarios, load
from pi_bench.trace import TraceRecorder

logger = logging.getLogger(__name__)

_EMPTY_FLAGS = {"V_r": False, "UR_r": False, "OR_r": False, "EA_r": False, "AT_r": False}


def _error_result(
    scenario_id: str, label: str, error: str, duration: float = 0,
) -> dict:
    """Build a standardized error result dict."""
    return {
        "scenario_id": scenario_id,
        "label": label,
        "status": "error",
        "error": error,
        "all_passed": False,
        "outcome_results": [],
        "canonical_decision": "",
        "event_flags": dict(_EMPTY_FLAGS),
        "duration": duration,
    }


def run_assessment(
    purple_url: str,
    config: dict[str, Any] | None = None,
) -> list[dict]:
    """Run all scenarios against a purple agent and return per-scenario results.

    This is the main entry point called by the executor. It discovers all
    pibench_scenario_v1 JSON files, loads each one via scenario_loader (which
    handles domain resolution for finra/retail/helpdesk), and runs them through
    the orchestrator with A2APurpleAgent in solo mode.

    Args:
        purple_url: HTTP endpoint of the purple agent.
        config: Optional configuration:
            - scenarios_dir: path to scenarios directory (default: ./scenarios)
            - workspace_root: root for resolving policy/tools (default: inferred)
            - max_steps: max orchestrator steps per scenario (default: 50)
            - seed: random seed (default: 42)
            - observer_mode: "audit_only" or "hard_gate" (default: "audit_only")

    Returns:
        List of per-scenario result dicts with scenario_id, label, reward,
        all_passed, outcome_results, canonical_decision, event_flags, etc.
    """
    config = config or {}
    scenarios_dir = Path(config.get("scenarios_dir", "scenarios"))
    workspace_root = config.get("workspace_root")
    max_steps = config.get("max_steps", 50)
    seed = config.get("seed", 42)
    observer_mode = config.get("observer_mode", "audit_only")

    # Discover all valid scenario files
    scenario_files = discover_scenarios(scenarios_dir)
    if not scenario_files:
        raise FileNotFoundError(f"No pibench_scenario_v1 files found in {scenarios_dir}")

    logger.info("Found %d scenarios in %s", len(scenario_files), scenarios_dir)

    results = []
    for scenario_path in scenario_files:
        scenario_id = scenario_path.stem
        try:
            result = _run_single_scenario(
                scenario_path=scenario_path,
                purple_url=purple_url,
                workspace_root=workspace_root,
                max_steps=max_steps,
                seed=seed,
                observer_mode=observer_mode,
            )
        except Exception as exc:
            logger.exception("Scenario %s failed", scenario_id)
            result = _error_result(scenario_id, "", str(exc))

        results.append(result)

    return results


def _run_single_scenario(
    scenario_path: Path,
    purple_url: str,
    workspace_root: str | Path | None = None,
    max_steps: int = 50,
    seed: int = 42,
    observer_mode: str = "audit_only",
) -> dict:
    """Run a single scenario against a purple agent via A2A.

    Uses scenario_loader.load() for multi-domain support, then runs the
    orchestrator in solo mode (no user simulator — the agent works from
    a ticket autonomously).
    """
    import time

    start = time.time()

    # Load scenario via the standard loader (handles finra/retail/helpdesk)
    loaded = load(scenario_path, workspace_root=workspace_root)
    task = loaded["task"]
    env = loaded["env"]
    outcomes = loaded["outcomes"]
    label = loaded["label"]
    scenario_id = loaded["scenario_id"]
    forbidden_tools = loaded["forbidden_tools"]

    # Validate scenario before running
    scenario_data = json.loads(Path(scenario_path).read_text())
    validation_errors = validate_scenario(scenario_data)
    if validation_errors:
        for err in validation_errors:
            logger.error("Validation error in %s: %s", scenario_id, err)
        return _error_result(
            scenario_id, label,
            f"Validation failed: {'; '.join(validation_errors)}",
            time.time() - start,
        )
    user_sim = scenario_data.get("user_simulation", {})
    initial_message = user_sim.get("initial_user_message", "")
    env_setup = scenario_data.get("environment_setup", {})

    # Construct a rich ticket that gives the agent all context
    ticket_parts = [task["description"]]
    if initial_message:
        ticket_parts.append(f"\nCustomer request:\n{initial_message}")
    if env_setup.get("now"):
        ticket_parts.append(f"\nCurrent time: {env_setup['now']}")

    task["ticket"] = "\n".join(ticket_parts)

    # Clear LLM judge cache for this scenario
    clear_judge_cache()

    # Create the purple agent adapter
    agent = A2APurpleAgent(purple_url)

    # Create trace and observer
    trace = TraceRecorder()
    observer = create_observer(
        env, trace,
        forbidden_tools=set(forbidden_tools) if forbidden_tools else None,
        mode=observer_mode,
    )

    # Run simulation in solo mode (no user simulator)
    try:
        sim = orchestrator_run(
            agent=agent,
            user=None,
            env=env,
            task=task,
            max_steps=max_steps,
            seed=seed,
            solo=True,
            observer=observer,
        )
    except Exception as exc:
        return _error_result(scenario_id, label, str(exc), time.time() - start)

    # Record messages to trace for NL assertions
    for msg in sim.get("messages", []):
        if msg.get("role") == "assistant" and msg.get("content"):
            trace.add_message("assistant", msg["content"])
        elif msg.get("role") == "user" and msg.get("content"):
            trace.add_message("user", msg["content"])

    # Evaluate outcomes using scenario_checker (supports all 11 outcome types)
    eval_result = check_outcomes(outcomes, trace, sim.get("messages", []), env)
    all_passed = eval_result["all_passed"]
    outcome_results = eval_result["outcome_results"]
    semantic_score = eval_result["semantic_score"]

    # Resolve canonical decision
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

    duration = time.time() - start

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
        "event_flags": {
            "V_r": flags.V_r,
            "UR_r": flags.UR_r,
            "OR_r": flags.OR_r,
            "EA_r": flags.EA_r,
            "AT_r": flags.AT_r,
        },
        "duration": duration,
        "tool_calls": trace.tool_names(),
    }


