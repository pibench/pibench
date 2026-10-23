"""Summarise one GDPR wave run with the benchmark's own metrics.

Reads coverage/results/<wave>_<condition>.json (pi-bench run-domain save
files), rebuilds the per-scenario rows the CLI builds, prints the standard
PI-BENCH metrics block for each condition, then a side-by-side table across
conditions.

Usage: python3 domains/gdpr/coverage/report_run.py wave1
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src")]

from pi_bench.metrics import compute_metrics, format_metrics_summary  # noqa: E402

RESULTS = ROOT / "domains/gdpr/coverage/results"
COMPLETED = ("agent_stop", "user_stop", "max_steps", "agent_error")


def rows_for(path: Path) -> list[dict]:
    from results_io import read_results
    sims = read_results(path).get("simulations", [])
    rows = []
    for sim in sims:
        reward = sim.get("reward_info") or {}
        tier1_failed = [o.get("outcome_id") for o in reward.get("outcome_results", [])
                        if not o.get("passed") and o.get("type") not in ("NL_JUDGE", "NL_ASSERTION")]
        judge_failed = [o.get("outcome_id") for o in reward.get("outcome_results", [])
                        if not o.get("passed") and o.get("type") in ("NL_JUDGE", "NL_ASSERTION")]
        rows.append({
            "scenario_id": sim.get("task_id", "?"),
            "domain": sim.get("domain", ""),
            "label": sim.get("label", ""),
            "leaderboard_primary": sim.get("leaderboard_primary", ""),
            "status": "completed" if sim.get("termination_reason") in COMPLETED else "error",
            "termination": sim.get("termination_reason"),
            "reward": reward.get("reward"),
            "all_passed": reward.get("all_passed", False),
            "deterministic_score": reward.get("deterministic_score", 0.0),
            "layers": reward.get("layers"),
            "unsafe_success": reward.get("unsafe_success"),
            "semantic_score": reward.get("semantic_score", 0.0),
            "canonical_decision": reward.get("canonical_decision"),
            "decision_channel": reward.get("decision_channel"),
            "decision_valid": reward.get("decision_valid", False),
            "decision_error": reward.get("decision_error"),
            "event_flags": sim.get("event_flags", {}),
            "dimensions": reward.get("dimensions", {}),
            "tier1_failed": tier1_failed,
            "judge_failed": judge_failed,
        })
    return sorted(rows, key=lambda r: r["scenario_id"])


def layer_pass(row: dict, layer: str) -> bool | None:
    info = (row.get("layers") or {}).get(layer)
    if isinstance(info, dict):
        return info.get("passed")
    return None


def main(wave: str) -> None:
    from results_io import results_files
    files = results_files(RESULTS, f"{wave}_*.json")
    by_cond = {p.stem.split("_", 1)[1]: rows_for(p) for p in files}
    for cond, rows in by_cond.items():
        print(f"\n######## condition: {cond} ({len(rows)} scenarios) ########")
        print(format_metrics_summary(compute_metrics(rows), None))
        labels = Counter(r["label"] for r in rows)
        print("  By label (all checks passed):")
        for lab in ("ALLOW", "DENY", "ESCALATE"):
            n = labels.get(lab, 0)
            p = sum(1 for r in rows if r["label"] == lab and r["all_passed"])
            d = sum(1 for r in rows if r["label"] == lab and r["canonical_decision"] == lab)
            print(f"    {lab:9} {p:2}/{n:<2} passed   decision correct {d:2}/{n}")
        conf = Counter((r["label"], r["canonical_decision"] or "none") for r in rows)
        print("  Decision confusion (label -> recorded): " + ", ".join(f"{a}->{b}: {c}" for (a, b), c in sorted(conf.items())))
        out_ok = sum(1 for r in rows if layer_pass(r, "outcome"))
        proc_ok = sum(1 for r in rows if layer_pass(r, "procedure") in (True, None))
        print(f"  Outcome layer passed {out_ok}/{len(rows)}; procedure layer passed {proc_ok}/{len(rows)}; "
              f"unsafe success {sum(1 for r in rows if r['unsafe_success'])}")
        errs = [r for r in rows if r["status"] != "completed"]
        if errs:
            print(f"  Episodes not completed: {', '.join(r['scenario_id'] + ' (' + str(r['termination']) + ')' for r in errs)}")

    if len(by_cond) > 1:
        conds = list(by_cond)
        idx = {c: {r["scenario_id"]: r for r in rows} for c, rows in by_cond.items()}
        ids = sorted(set().union(*[set(v) for v in idx.values()]))
        print("\n######## side by side ########")
        print(f"{'scenario':12} {'label':9} " + " ".join(f"{c:28}" for c in conds))
        for sid in ids:
            cells = []
            for c in conds:
                r = idx[c].get(sid)
                if not r:
                    cells.append(f"{'—':28}")
                    continue
                mark = "pass" if r["all_passed"] else "FAIL " + ",".join(x.split("_")[0] for x in r["tier1_failed"])
                cells.append(f"{(mark + ' [' + str(r['canonical_decision']) + ']')[:28]:28}")
            lab = next(idx[c][sid]["label"] for c in conds if sid in idx[c])
            print(f"{sid:12} {lab:9} " + " ".join(cells))
        if {"neutral", "stress"} <= set(conds):
            n, s = idx["neutral"], idx["stress"]
            both = [i for i in ids if i in n and i in s]
            cap = [i for i in both if n[i]["all_passed"] and not s[i]["all_passed"]]
            rec = [i for i in both if not n[i]["all_passed"] and s[i]["all_passed"]]
            print(f"\nPassed neutral but failed under stress (capitulation): {len(cap)} {cap}")
            print(f"Failed neutral but passed under stress: {len(rec)} {rec}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "wave1")
