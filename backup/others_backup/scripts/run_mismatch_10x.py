"""Run 12 mismatch scenarios x 10 trials on gpt-4o-mini, report pass rates."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

SCENARIOS = [
    "scenarios/finra/scen_019_wire_vs_ach_speed.json",
    "scenarios/finra/scen_020_lockup_withdrawal_timing.json",
    "scenarios/finra/scen_021_dual_auth_banker_on_leave.json",
    "scenarios/helpdesk/scen_042_critical_lockout_timing.json",
    "scenarios/helpdesk/scen_043_database_approval_format.json",
    "scenarios/retail/scen_040_final_sale_restocking_tradeoff.json",
    "scenarios/retail/scen_041_activated_tablet_holiday_window.json",
    "scenarios/retail/scen_042_fraud_hold_location_choice.json",
]

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o-mini"
NUM_TRIALS = int(sys.argv[2]) if len(sys.argv) > 2 else 10
CONCURRENCY = int(sys.argv[3]) if len(sys.argv) > 3 else 40
OUT_DIR = Path(f"reports/mismatch_{MODEL.replace('/', '_')}_{NUM_TRIALS}x")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_one(scenario_path: str, trial: int) -> dict:
    name = Path(scenario_path).stem
    out_file = OUT_DIR / f"{name}_t{trial:02d}.json"
    seed = trial * 7919 + hash(name) % 10000
    cmd = [
        sys.executable, "-m", "pi_bench.run_scenarios",
        "--model", MODEL,
        "--scenario", scenario_path,
        "--output", str(out_file),
        "--max-steps", "15",
        "--seed", str(seed),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    # Parse result
    try:
        report = json.loads(out_file.read_text())
        scenarios = report.get("scenarios", [])
        if scenarios:
            s = scenarios[0]
            passed = s.get("evaluation", {}).get("all_passed", False)
            return {"scenario": name, "trial": trial, "passed": passed}
    except Exception:
        pass
    return {"scenario": name, "trial": trial, "passed": False, "error": result.stderr[-200:] if result.stderr else "unknown"}


# Build work queue
work = [(s, t) for s in SCENARIOS for t in range(1, NUM_TRIALS + 1)]
print(f"Running {len(work)} evaluations ({len(SCENARIOS)} scenarios x {NUM_TRIALS} trials) on {MODEL}")
print(f"Concurrency: {CONCURRENCY}")
print()

results = []
done = 0
with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
    futures = {pool.submit(run_one, s, t): (s, t) for s, t in work}
    for future in as_completed(futures):
        r = future.result()
        results.append(r)
        done += 1
        status = "PASS" if r["passed"] else "FAIL"
        if done % 10 == 0 or done == len(work):
            print(f"  [{done}/{len(work)}] {r['scenario']} t{r['trial']:02d} → {status}")

# Aggregate
from collections import defaultdict
stats = defaultdict(lambda: {"pass": 0, "fail": 0})
for r in results:
    if r["passed"]:
        stats[r["scenario"]]["pass"] += 1
    else:
        stats[r["scenario"]]["fail"] += 1

print()
print("=" * 80)
print(f"AGGREGATE RESULTS — {MODEL} x {NUM_TRIALS} trials")
print("=" * 80)
print(f"{'Scenario':<55} {'Pass':>5} {'Fail':>5} {'Rate':>7}")
print("-" * 80)

to_discard = []
for name in sorted(stats.keys()):
    s = stats[name]
    total = s["pass"] + s["fail"]
    rate = s["pass"] / total if total else 0
    flag = " ← DISCARD (too easy)" if rate >= 0.8 else ""
    print(f"  {name:<53} {s['pass']:>5} {s['fail']:>5} {rate:>6.0%}{flag}")
    if rate >= 0.8:
        to_discard.append(name)

print()
if to_discard:
    print(f"Scenarios to discard (pass rate >= 80% on {MODEL}):")
    for name in to_discard:
        print(f"  - {name}")
else:
    print(f"All scenarios are hard enough (none pass >= 80% on {MODEL})")
