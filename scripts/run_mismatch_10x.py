"""Run mismatch scenarios x N trials, report pass rates.

Usage:
    python scripts/run_mismatch_10x.py [MODEL] [NUM_TRIALS] [CONCURRENCY]
    python scripts/run_mismatch_10x.py gpt-4o-mini 10 4
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from pi_bench.agents.litellm_agent import LiteLLMAgent
from pi_bench.runner import run_domain
from pi_bench.scenario_loader import load_domain
from pi_bench.metrics import compute_metrics

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o-mini"
NUM_TRIALS = int(sys.argv[2]) if len(sys.argv) > 2 else 10
CONCURRENCY = int(sys.argv[3]) if len(sys.argv) > 3 else 1
OUT_DIR = Path(f"reports/mismatch_{MODEL.replace('/', '_')}_{NUM_TRIALS}x")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Mismatch scenario IDs to select
MISMATCH_IDS = {
    "SCEN_019_WIRE_VS_ACH_SPEED",
    "SCEN_040_FINAL_SALE_RESTOCKING_TRADEOFF",
    "SCEN_041_ACTIVATED_TABLET_HOLIDAY_WINDOW",
    "SCEN_042_CRITICAL_LOCKOUT_TIMING",
    "SCEN_043_DATABASE_APPROVAL_FORMAT",
}


def agent_factory():
    return LiteLLMAgent(model_name=MODEL)


def main():
    print(f"Model: {MODEL}")
    print(f"Trials: {NUM_TRIALS}")
    print(f"Concurrency: {CONCURRENCY}")

    results_all = []

    for domain_name in ("finra", "retail", "helpdesk"):
        try:
            domain = load_domain(domain_name)
        except FileNotFoundError:
            continue

        # Filter to mismatch scenarios only
        task_ids = [t["id"] for t in domain["tasks"] if t["id"] in MISMATCH_IDS]
        if not task_ids:
            continue

        print(f"\n{domain_name}: running {len(task_ids)} mismatch scenarios x {NUM_TRIALS} trials")

        agent = LiteLLMAgent(model_name=MODEL)
        result = run_domain(
            domain=domain,
            agent=agent,
            user=None,
            num_trials=NUM_TRIALS,
            max_concurrency=CONCURRENCY,
            agent_factory=agent_factory if CONCURRENCY > 1 else None,
            solo=True,
            task_ids=task_ids,
            save_to=OUT_DIR / f"{domain_name}_results.json",
        )

        for sim in result["simulations"]:
            reward = sim.get("reward_info", {})
            results_all.append({
                "scenario_id": sim.get("task_id", "?"),
                "trial": sim.get("trial", 0),
                "passed": reward.get("all_passed", False),
                "label": sim.get("label", ""),
                "leaderboard_primary": sim.get("leaderboard_primary", ""),
            })

    # Aggregate
    stats = defaultdict(lambda: {"pass": 0, "fail": 0})
    for r in results_all:
        key = r["scenario_id"]
        if r["passed"]:
            stats[key]["pass"] += 1
        else:
            stats[key]["fail"] += 1

    print(f"\n{'='*80}")
    print(f"AGGREGATE RESULTS — {MODEL} x {NUM_TRIALS} trials")
    print(f"{'='*80}")
    print(f"{'Scenario':<55} {'Pass':>5} {'Fail':>5} {'Rate':>7}")
    print("-" * 80)

    for name in sorted(stats.keys()):
        s = stats[name]
        total = s["pass"] + s["fail"]
        rate = s["pass"] / total if total else 0
        flag = " <- DISCARD (too easy)" if rate >= 0.8 else ""
        print(f"  {name:<53} {s['pass']:>5} {s['fail']:>5} {rate:>6.0%}{flag}")


if __name__ == "__main__":
    main()
