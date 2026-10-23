"""Coverage ledger for the GDPR dataset.

Joins four sources and says what the next wave should cover:
  - the ontology (domains/gdpr/ontology/gdpr_ontology.json): the universe of
    rules, their conditions by role, and rule-to-rule edges;
  - the scope file (coverage/scope.json): rules the environment can exercise;
  - the scenarios (scenarios/gdpr/*.json, their `coverage` blocks);
  - run results (coverage/results/*.json, pi-bench run-domain save files),
    one file per run condition, e.g. wave1_neutral.json, wave1_stress.json.

Writes coverage/ledger.json (machine-readable) and coverage/LEDGER.md.

Usage: python3 domains/gdpr/coverage/ledger.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COV = ROOT / "domains/gdpr/coverage"
ONT = json.loads((ROOT / "domains/gdpr/ontology/gdpr_ontology.json").read_text())
NODES = {n["id"]: n for n in ONT["nodes"]}
RULES = sorted(n["id"] for n in ONT["nodes"] if n["type"] == "rule")
ROLE_EDGES = {"triggered_by": "trigger", "has_exception": "exception", "blocked_by": "defeater", "weighs": "factor"}
RULE_EDGE_TYPES = {"refines", "depends_on", "overrides", "tension_with", "supports"}
LABELS = ("ALLOW", "DENY", "ESCALATE")
TARGET_SHARE = {"ALLOW": 0.4, "DENY": 0.4, "ESCALATE": 0.2}


def load_scenarios() -> list[dict]:
    out = []
    for p in sorted((ROOT / "scenarios/gdpr").glob("*.json")):
        sc = json.loads(p.read_text())
        sc["_file"] = p.name
        out.append(sc)
    return out


def load_results() -> dict[str, dict[str, dict]]:
    """{condition: {scenario_id: summary}} from coverage/results/<wave>_<condition>.json."""
    results: dict[str, dict[str, dict]] = {}
    from results_io import read_results, results_files
    for p in results_files(COV / "results"):
        try:
            data = read_results(p)
        except (json.JSONDecodeError, EOFError, OSError):  # a run still writing its save file
            continue
        cond = p.stem.split("_", 1)[1] if "_" in p.stem else p.stem
        rows = results.setdefault(cond, {})
        for sim in data.get("simulations", []):
            r = sim.get("reward_info") or {}
            failed = [o.get("outcome_id") for o in r.get("outcome_results", [])
                      if not o.get("passed") and o.get("type") not in ("NL_JUDGE", "NL_ASSERTION")]
            rows[sim.get("task_id")] = {
                "passed": bool(r.get("all_passed")),
                "decision": r.get("canonical_decision"),
                "unsafe_success": r.get("unsafe_success"),
                "failed_checks": failed,
                "termination": sim.get("termination_reason"),
            }
    return results


def rule_conditions() -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for e in ONT["edges"]:
        if e["type"] in ROLE_EDGES and e["source"] in NODES and NODES[e["source"]]["type"] == "rule":
            out[e["source"]][ROLE_EDGES[e["type"]]].add(e["target"])
    return out


def build() -> dict:
    scope = json.loads((COV / "scope.json").read_text())
    out_of_scope = scope["out_of_scope"]
    scenarios = load_scenarios()
    results = load_results()
    rconds = rule_conditions()
    rule_edges = {(e["source"], e["type"], e["target"]) for e in ONT["edges"] if e["type"] in RULE_EDGE_TYPES}

    per_rule: dict[str, dict] = {r: {"scenarios": [], "labels": Counter(), "conditions": set(),
                                     "failure_modes": set(), "results": defaultdict(list)} for r in RULES}
    edges_hit: set[tuple] = set()
    labels = Counter()
    fm = Counter()
    difficulty = Counter()
    stressors = Counter()
    twins = []
    for sc in scenarios:
        sid = sc["meta"]["scenario_id"]
        cov = sc.get("coverage", {})
        labels[sc["label"]] += 1
        for f in cov.get("failure_modes", []):
            fm[f] += 1
        for d in cov.get("difficulty", []):
            difficulty[d] += 1
        for s in sc.get("leaderboard", {}).get("stressors", []):
            stressors[s] += 1
        if cov.get("twin_of"):
            twins.append(tuple(sorted((sid, cov["twin_of"]))))
        for e in cov.get("rule_edges", []):
            edges_hit.add(tuple(e))
        conds = set(cov.get("conditions_true", [])) | set(cov.get("conditions_false", []))
        for r in cov.get("rules", []):
            if r not in per_rule:
                continue
            row = per_rule[r]
            row["scenarios"].append(sid)
            row["labels"][sc["label"]] += 1
            row["conditions"] |= conds
            row["failure_modes"] |= set(cov.get("failure_modes", []))
            for cond, rows in results.items():
                if sid in rows:
                    row["results"][cond].append(rows[sid]["passed"])

    rules_out = {}
    for r in RULES:
        row = per_rule[r]
        all_conds = set().union(*rconds[r].values()) if rconds.get(r) else set()
        by_role = {role: sorted(ids) for role, ids in rconds.get(r, {}).items()}
        hit = row["conditions"] & all_conds
        unexercised_exceptions = sorted((rconds[r].get("exception", set()) | rconds[r].get("defeater", set())) - hit)
        if r in out_of_scope:
            status = "out_of_scope"
        elif not row["scenarios"]:
            status = "uncovered"
        elif len(row["labels"]) == 1:
            status = "single_label"
        else:
            status = "covered"
        rules_out[r] = {
            "label": NODES[r]["label"], "group": NODES[r].get("group"), "status": status,
            "out_of_scope_reason": out_of_scope.get(r),
            "scenarios": row["scenarios"], "labels": dict(row["labels"]),
            "conditions_total": len(all_conds), "conditions_exercised": sorted(hit),
            "conditions_by_role": by_role, "unexercised_exceptions": unexercised_exceptions,
            "failure_modes": sorted(row["failure_modes"]),
            "pass_rate": {c: round(sum(v) / len(v), 3) for c, v in row["results"].items() if v},
        }

    in_scope = [r for r in RULES if r not in out_of_scope]
    total = sum(labels.values()) or 1
    summary = {
        "scenarios": len(scenarios),
        "labels": dict(labels),
        "label_share": {k: round(labels[k] / total, 3) for k in LABELS},
        "rules_total": len(RULES),
        "rules_in_scope": len(in_scope),
        "rules_covered": sum(1 for r in in_scope if rules_out[r]["scenarios"]),
        "rules_with_both_allow_and_deny": sum(1 for r in in_scope if {"ALLOW", "DENY"} <= set(rules_out[r]["labels"])),
        "rule_edges_total": len(rule_edges),
        "rule_edges_covered": len(edges_hit & rule_edges),
        "failure_modes": dict(fm.most_common()),
        "difficulty": dict(difficulty.most_common()),
        "stressors": dict(stressors.most_common()),
        "twin_pairs": len(set(twins)),
        "by_group": {},
    }
    for g in sorted({NODES[r].get("group") for r in in_scope}):
        rs = [r for r in in_scope if NODES[r].get("group") == g]
        summary["by_group"][g] = {"in_scope": len(rs), "covered": sum(1 for r in rs if rules_out[r]["scenarios"])}

    scenario_rows = []
    for sc in scenarios:
        sid = sc["meta"]["scenario_id"]
        scenario_rows.append({
            "id": sid, "file": sc["_file"], "label": sc["label"],
            "rules": sc.get("coverage", {}).get("rules", []),
            "construct": sc.get("coverage", {}).get("construct", ""),
            "twin_of": sc.get("coverage", {}).get("twin_of"),
            "results": {c: rows.get(sid) for c, rows in results.items() if sid in rows},
        })

    return {"summary": summary, "rules": rules_out, "scenarios": scenario_rows,
            "next_targets": next_targets(rules_out, scenario_rows, labels, results)}


def next_targets(rules_out: dict, scenario_rows: list[dict], labels: Counter, results: dict) -> list[dict]:
    """Ranked suggestions for the next wave (explore first, then exploit)."""
    todo: list[dict] = []
    for r, row in rules_out.items():
        if row["status"] == "uncovered":
            todo.append({"priority": 1, "kind": "explore_uncovered_rule", "rule": r, "why": row["label"]})
    for r, row in rules_out.items():
        if row["status"] == "single_label":
            have = next(iter(row["labels"]))
            want = "DENY" if have == "ALLOW" else "ALLOW"
            todo.append({"priority": 2, "kind": "add_opposite_label", "rule": r,
                         "why": f"only {have} so far; add a {want} twin that flips one deciding fact"})
    for r, row in rules_out.items():
        if row["status"] in ("covered", "single_label") and row["unexercised_exceptions"]:
            todo.append({"priority": 3, "kind": "exercise_exception", "rule": r,
                         "why": "exceptions/defeaters not yet tested: " + ", ".join(row["unexercised_exceptions"][:4])})
    total = sum(labels.values()) or 1
    for lab, share in TARGET_SHARE.items():
        if labels[lab] / total < share - 0.05:
            todo.append({"priority": 2, "kind": "label_balance", "label": lab,
                         "why": f"{lab} is {labels[lab]}/{total}; target about {int(share * 100)}%"})
    if results:
        for row in scenario_rows:
            res = row["results"]
            if not res:
                continue
            fails = [c for c, v in res.items() if v and not v["passed"]]
            if fails:
                checks = sorted({ck for c in fails for ck in res[c]["failed_checks"]})
                todo.append({"priority": 2, "kind": "exploit_failure", "scenario": row["id"], "rules": row["rules"],
                             "why": f"failed under {', '.join(fails)} ({', '.join(checks) or 'no Tier-1 detail'}); "
                                    "build a variant with a different surface and the same construct to confirm "
                                    "the weakness is systematic"})
            elif len(res) >= 2:
                todo.append({"priority": 4, "kind": "keep_as_control", "scenario": row["id"],
                             "why": "passed in every condition; keep as a control, deprioritise its construct"})
    return sorted(todo, key=lambda t: t["priority"])


def render_md(L: dict) -> str:
    s = L["summary"]
    lines = ["# GDPR coverage ledger", "",
             "Generated by `domains/gdpr/coverage/ledger.py`; do not edit by hand.", "",
             f"- Scenarios: **{s['scenarios']}**: " + ", ".join(f"{k} {s['labels'].get(k, 0)}" for k in LABELS),
             f"- Rules covered: **{s['rules_covered']} / {s['rules_in_scope']}** in scope ({s['rules_total']} in the ontology)",
             f"- Rules with both an ALLOW and a DENY scenario: {s['rules_with_both_allow_and_deny']}",
             f"- Rule-to-rule edges exercised: {s['rule_edges_covered']} / {s['rule_edges_total']}",
             f"- Twin pairs: {s['twin_pairs']}", "",
             "## By group", "", "| Group | Covered / in scope |", "|---|---|"]
    for g, v in s["by_group"].items():
        lines.append(f"| {g} | {v['covered']} / {v['in_scope']} |")
    lines += ["", "## Failure modes targeted", "", ", ".join(f"{k} ({v})" for k, v in s["failure_modes"].items()), ""]
    conds = sorted({c for row in L["scenarios"] for c in (row.get("results") or {})})
    lines += ["## Scenarios", "", "| Id | Label | Rules | " + " | ".join(conds) + (" |" if conds else "") + " Construct |",
              "|---|---|---|" + "---|" * len(conds) + "---|"]
    for row in L["scenarios"]:
        cells = []
        for c in conds:
            v = (row["results"] or {}).get(c)
            cells.append("—" if not v else ("pass" if v["passed"] else f"FAIL ({v['decision'] or 'no decision'})"))
        lines.append(f"| {row['id']} | {row['label']} | {', '.join(row['rules'])} | " + "".join(f"{x} | " for x in cells)
                     + row["construct"].replace("|", "/") + " |")
    lines += ["", "## Rules", "", "| Rule | Status | Labels | Conditions exercised | Pass rate |", "|---|---|---|---|---|"]
    for r, row in L["rules"].items():
        pr = ", ".join(f"{c} {v:.0%}" for c, v in row["pass_rate"].items()) or "—"
        labs = ", ".join(f"{k} {v}" for k, v in row["labels"].items()) or "—"
        lines.append(f"| {r} {row['label']} | {row['status']} | {labs} | "
                     f"{len(row['conditions_exercised'])}/{row['conditions_total']} | {pr} |")
    lines += ["", "## Archive (main rule x label)", "",
              "MAP-Elites view: each cell is a main rule and a label; it lists the scenarios whose main rule it is,",
              "with neutral/stress results (P pass, F fail, - not run). Empty cells are explore targets; cells with",
              "failures are exploit targets.", "",
              "| Rule | ALLOW | DENY | ESCALATE |", "|---|---|---|---|"]
    for r, row in L["rules"].items():
        if row["status"] == "out_of_scope":
            continue
        cells = []
        for lab in LABELS:
            items = [s for s in L["scenarios"] if s["rules"] and s["rules"][0] == r and s["label"] == lab]
            cells.append(" ".join(s["id"].replace("GDPR_", "") + "(" + "".join(
                "P" if (s["results"].get(c) or {}).get("passed") else ("F" if s["results"].get(c) else "-")
                for c in ("neutral", "stress")) + ")" for s in items) or "·")
        lines.append(f"| {r} | " + " | ".join(cells) + " |")
    lines += ["", "## Next targets (ranked)", ""]
    for t in L["next_targets"][:60]:
        subject = t.get("rule") or t.get("scenario") or t.get("label")
        lines.append(f"- P{t['priority']} `{t['kind']}` **{subject}**: {t['why']}")
    return "\n".join(lines) + "\n"


def viewer_coverage(L: dict) -> dict:
    """Compact coverage overlay for the ontology viewer (ontology/viewer/coverage.json)."""
    conditions: dict[str, list[str]] = defaultdict(list)
    rule_edges: set[tuple] = set()
    for p in sorted((ROOT / "scenarios/gdpr").glob("*.json")):
        sc = json.loads(p.read_text())
        cov = sc.get("coverage", {})
        for c in set(cov.get("conditions_true", [])) | set(cov.get("conditions_false", [])):
            conditions[c].append(sc["meta"]["scenario_id"])
        rule_edges |= {tuple(e) for e in cov.get("rule_edges", [])}
    return {
        "summary": L["summary"],
        "rules": {r: {k: v[k] for k in ("status", "scenarios", "labels", "pass_rate", "out_of_scope_reason")}
                  for r, v in L["rules"].items()},
        "conditions": dict(conditions),
        "rule_edges": sorted(list(e) for e in rule_edges),
        "scenarios": {s["id"]: {"label": s["label"], "construct": s["construct"],
                                "results": {c: (v or {}).get("passed") for c, v in (s["results"] or {}).items()}}
                      for s in L["scenarios"]},
    }


if __name__ == "__main__":
    L = build()
    (COV / "ledger.json").write_text(json.dumps(L, indent=1, default=sorted))
    (COV / "LEDGER.md").write_text(render_md(L))
    (ROOT / "domains/gdpr/ontology/viewer/coverage.json").write_text(json.dumps(viewer_coverage(L), indent=1))
    s = L["summary"]
    print(f"{s['scenarios']} scenarios {s['labels']}; rules {s['rules_covered']}/{s['rules_in_scope']} in scope; "
          f"edges {s['rule_edges_covered']}/{s['rule_edges_total']}; {len(L['next_targets'])} next targets")
