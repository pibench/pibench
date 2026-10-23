"""Registry of every GDPR benchmark run: which models, which settings, which scores.

Each entry is one run of one wave in one condition. Scores are computed from
the run's save file (pi-bench run-domain output) with the benchmark's own
metrics, plus label, layer and (for structured pressure) per-technique
breakdowns.

  python3 domains/gdpr/coverage/registry.py add --wave 2 --condition stress \
      --results domains/gdpr/coverage/results/wave2_stress.json \
      --agent-model claude-sonnet-4-5 --user-model claude-sonnet-5-5 \
      --judge-model claude-haiku-5-5 --pressure-version 2 --pushbacks 3 \
      --concurrency 2 --started 2026-10-22T10:00 --finished 2026-10-22T12:30
  python3 domains/gdpr/coverage/registry.py render   # rewrite RUNS.md

Writes coverage/results/runs.json and coverage/results/RUNS.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src")]
RESULTS = ROOT / "domains/gdpr/coverage/results"
RUNS_JSON = RESULTS / "runs.json"
RUNS_MD = RESULTS / "RUNS.md"
LABELS = ("ALLOW", "DENY", "ESCALATE")
COMPLETED = ("agent_stop", "user_stop", "max_steps")


def _scenario_pressure() -> dict[str, list[str]]:
    """Current technique ids per scenario (structured pressure only)."""
    out = {}
    for p in (ROOT / "scenarios/gdpr").glob("*.json"):
        sc = json.loads(p.read_text())
        pr = sc.get("user_simulation", {}).get("pressure")
        if isinstance(pr, dict) and pr.get("technique"):
            out[sc["meta"]["scenario_id"]] = list(pr["technique"])
    return out


def summarise(results_path: Path, pressure_version: int) -> dict:
    from pi_bench.metrics import compute_metrics

    from results_io import read_results
    sims = read_results(results_path).get("simulations", [])
    rows = []
    for s in sims:
        r = s.get("reward_info") or {}
        rows.append({
            "scenario_id": s.get("task_id"), "label": s.get("label", ""),
            "leaderboard_primary": s.get("leaderboard_primary", ""),
            "status": "completed" if s.get("termination_reason") in COMPLETED else "error",
            "termination": s.get("termination_reason"),
            "all_passed": bool(r.get("all_passed")), "reward": r.get("reward"),
            "deterministic_score": r.get("deterministic_score", 0.0),
            "semantic_score": r.get("semantic_score", 0.0),
            "canonical_decision": r.get("canonical_decision"),
            "decision_valid": r.get("decision_valid", False),
            "event_flags": s.get("event_flags", {}), "dimensions": r.get("dimensions", {}),
            "layers": r.get("layers"), "unsafe_success": r.get("unsafe_success"),
        })
    m = compute_metrics(rows)
    n = len(rows)
    passed = sum(r["all_passed"] for r in rows)
    by_label = {}
    for lab in LABELS:
        sub = [r for r in rows if r["label"] == lab]
        by_label[lab] = {"n": len(sub), "passed": sum(r["all_passed"] for r in sub),
                         "decision_correct": sum(r["canonical_decision"] == lab for r in sub)}
    layer = lambda r, k: ((r.get("layers") or {}).get(k) or {}).get("passed")
    summary = {
        "episodes": n,
        "completed": sum(r["status"] == "completed" for r in rows),
        "full_compliance": round(passed / n, 4) if n else None,
        "passed": passed,
        "deterministic_score": round(m.mean_deterministic_score, 4),
        "semantic_score": round(m.mean_semantic_score, 4),
        "event_rates": {k: round(v, 4) for k, v in (getattr(m, "event_metrics", None) or {}).items() if isinstance(v, (int, float))},
        "by_label": by_label,
        "decision_confusion": {f"{a}->{b}": c for (a, b), c in sorted(Counter(
            (r["label"], r["canonical_decision"] or "none") for r in rows).items())},
        "outcome_layer_passed": sum(1 for r in rows if layer(r, "outcome")),
        "procedure_layer_passed": sum(1 for r in rows if layer(r, "procedure") in (True, None)),
        "unsafe_success": sum(1 for r in rows if r["unsafe_success"]),
        "per_scenario": {r["scenario_id"]: {"passed": r["all_passed"], "decision": r["canonical_decision"],
                                            "termination": r["termination"]} for r in rows},
    }
    if pressure_version >= 2:
        tech = _scenario_pressure()
        per = defaultdict(lambda: {"n": 0, "passed": 0})
        for r in rows:
            for t in tech.get(r["scenario_id"], ["(no pressure)"]):
                per[t]["n"] += 1
                per[t]["passed"] += int(r["all_passed"])
        summary["by_technique"] = dict(sorted(per.items()))
    return summary


def load() -> list[dict]:
    return json.loads(RUNS_JSON.read_text()) if RUNS_JSON.exists() else []


def add(entry: dict) -> None:
    runs = [r for r in load() if not (r["wave"] == entry["wave"] and r["condition"] == entry["condition"]
                                      and r.get("results") == entry.get("results"))]
    runs.append(entry)
    runs.sort(key=lambda r: (r["wave"], r["condition"], r.get("started", "")))
    RUNS_JSON.write_text(json.dumps(runs, indent=1))
    render()


def render() -> None:
    runs = load()
    lines = ["# GDPR benchmark runs", "",
             "Generated by `domains/gdpr/coverage/registry.py`; one row per wave x condition run.", "",
             "| Wave | Condition | Agent | User | Judge | Pressure | N | Conc. | Started | Episodes | Full compliance | ALLOW | DENY | ESCALATE | Unsafe |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        s = r["summary"]
        lab = lambda k: f"{s['by_label'][k]['passed']}/{s['by_label'][k]['n']}"
        lines.append(f"| {r['wave']} | {r['condition']} | {r['agent_model']} | {r['user_model']} | {r['judge_model']} | "
                     f"v{r['pressure_version']} | {r['pushbacks']} | {r['concurrency']} | {r.get('started', '')} | "
                     f"{s['completed']}/{s['episodes']} | **{s['full_compliance']:.0%}** ({s['passed']}) | "
                     f"{lab('ALLOW')} | {lab('DENY')} | {lab('ESCALATE')} | {s['unsafe_success']} |")
    for r in runs:
        s = r["summary"]
        lines += ["", f"## Wave {r['wave']} · {r['condition']}", "",
                  f"- Results file: `{r['results']}`; harness: {r['harness']}; notes: {r.get('notes', '')}",
                  f"- Deterministic score {s['deterministic_score']:.1%}; semantic score {s['semantic_score']:.1%}; "
                  f"outcome layer passed {s['outcome_layer_passed']}/{s['episodes']}; procedure layer passed "
                  f"{s['procedure_layer_passed']}/{s['episodes']}",
                  f"- Event rates: " + ", ".join(f"{k} {v:.1%}" for k, v in s.get("event_rates", {}).items()),
                  f"- Decision confusion: " + ", ".join(f"{k}: {v}" for k, v in s["decision_confusion"].items())]
        if s.get("by_technique"):
            lines.append("- By technique (passed/n): " + ", ".join(
                f"{k} {v['passed']}/{v['n']}" for k, v in s["by_technique"].items()))
    RUNS_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    for k in ("wave", "pushbacks", "concurrency", "pressure-version"):
        a.add_argument(f"--{k}", type=int, required=True)
    for k in ("condition", "results", "agent-model", "user-model", "judge-model", "started", "finished"):
        a.add_argument(f"--{k}", required=True)
    a.add_argument("--harness", default="OmniGent local server, claude-sdk harness (Claude subscription)")
    a.add_argument("--notes", default="")
    sub.add_parser("render")
    args = ap.parse_args(argv)
    if args.cmd == "render":
        render()
        return
    path = (ROOT / args.results) if not Path(args.results).is_absolute() else Path(args.results)
    entry = {"wave": args.wave, "condition": args.condition, "results": str(path.relative_to(ROOT)),
             "agent_model": args.agent_model, "user_model": args.user_model, "judge_model": args.judge_model,
             "harness": args.harness, "pressure_version": args.pressure_version, "pushbacks": args.pushbacks,
             "concurrency": args.concurrency, "started": args.started, "finished": args.finished,
             "notes": args.notes, "summary": summarise(path, args.pressure_version)}
    add(entry)
    s = entry["summary"]
    print(f"recorded wave {args.wave} {args.condition}: {s['passed']}/{s['episodes']} = {s['full_compliance']:.0%}")


if __name__ == "__main__":
    main(sys.argv[1:])
