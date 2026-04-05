"""Assessment engine — runs pi-bench scenarios against a purple agent via A2A.

Unlike the Archive 9 version that only supported the finance domain, this
engine uses scenario_loader.load() to support all domains (finra, retail,
helpdesk) and delegates to runner/core.py for the evaluation pipeline,
ensuring identical evaluation logic across all paths.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pi_bench.a2a.purple_adapter import A2APurpleAgent
from pi_bench.evaluator.scenario_validator import validate_scenario
from pi_bench.runner.core import run_domain
from pi_bench.scenario_loader import discover_scenarios, load

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
    the unified runner with A2APurpleAgent in solo mode.

    Args:
        purple_url: HTTP endpoint of the purple agent.
        config: Optional configuration:
            - scenarios_dir: path to scenarios directory (default: ./scenarios)
            - workspace_root: root for resolving policy/tools (default: inferred)
            - max_steps: max orchestrator steps per scenario (default: 50)
            - seed: random seed (default: 42)

    Returns:
        List of per-scenario result dicts with scenario_id, label, reward,
        all_passed, outcome_results, canonical_decision, event_flags, etc.
    """
    config = config or {}
    scenarios_dir = Path(config.get("scenarios_dir", "scenarios"))
    workspace_root = config.get("workspace_root")
    max_steps = config.get("max_steps", 50)
    seed = config.get("seed", 42)

    # Discover all valid scenario files
    scenario_files = discover_scenarios(scenarios_dir)
    if not scenario_files:
        raise FileNotFoundError(f"No pibench_scenario_v1 files found in {scenarios_dir}")

    logger.info("Found %d scenarios in %s", len(scenario_files), scenarios_dir)

    # Load and validate all scenarios
    loaded_scenarios = []
    error_results = []
    for scenario_path in scenario_files:
        scenario_id = scenario_path.stem
        try:
            scenario_data = json.loads(Path(scenario_path).read_text())
            validation_errors = validate_scenario(scenario_data)
            if validation_errors:
                for err in validation_errors:
                    logger.error("Validation error in %s: %s", scenario_id, err)
                error_results.append(_error_result(
                    scenario_id, "",
                    f"Validation failed: {'; '.join(validation_errors)}",
                ))
                continue

            loaded = load(scenario_path, workspace_root=workspace_root)

            # Build enriched ticket for A2A (agent gets all context via ticket)
            user_sim = scenario_data.get("user_simulation", {})
            initial_message = user_sim.get("initial_user_message", "")
            env_setup = scenario_data.get("environment_setup", {})

            ticket_parts = [loaded["task"]["description"]]
            if initial_message:
                ticket_parts.append(f"\nCustomer request:\n{initial_message}")
            if env_setup.get("now"):
                ticket_parts.append(f"\nCurrent time: {env_setup['now']}")
            loaded["task"]["ticket"] = "\n".join(ticket_parts)

            loaded_scenarios.append(loaded)

        except Exception as exc:
            logger.exception("Scenario %s failed to load", scenario_id)
            error_results.append(_error_result(scenario_id, "", str(exc)))

    if not loaded_scenarios:
        return error_results

    # Create the purple agent adapter
    agent = A2APurpleAgent(purple_url)

    # Build a dummy domain dict for make_info() compatibility
    domain = {
        "name": "a2a",
        "tasks": [s["task"] for s in loaded_scenarios],
        "get_environment": lambda: loaded_scenarios[0]["env"],
    }

    # Run via unified runner — same path as run_scenarios.py
    run_result = run_domain(
        domain=domain,
        agent=agent,
        user=None,
        num_trials=1,
        seed=seed,
        max_concurrency=1,
        max_steps=max_steps,
        solo=True,
        scenarios=loaded_scenarios,
    )

    # Extract per-scenario results from simulations
    results = list(error_results)
    for sim in run_result["simulations"]:
        results.append(sim)

    return results
