"""Print everything a scenario author needs about one or more ontology rules.

Usage: python3 domains/gdpr/coverage/rule_card.py DR-05 [CM-04 ...]

Shows the rule, its conditions by role (trigger / exception / blocked_by /
weighs) with the quoted text, required and forbidden actions, links to other
rules, and the parked seed paths for the rule. Use the ids printed here in a
scenario's `coverage` block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ONT = ROOT / "domains/gdpr/ontology"
O = json.loads((ONT / "gdpr_ontology.json").read_text())
NODES = {n["id"]: n for n in O["nodes"]}
SEEDS = json.loads((ONT / "drafts/decision_paths_draft.json").read_text())["decision_paths"]

ROLE_EDGES = ("triggered_by", "has_exception", "blocked_by", "weighs")
ACTION_EDGES = ("requires_action", "forbids_action")
RULE_EDGES = ("refines", "depends_on", "overrides", "tension_with", "supports")


def _extras(e: dict) -> str:
    parts = []
    for key in ("qualifies", "conjunct_with", "conjunct_with_any", "when", "sign"):
        if e.get(key):
            parts.append(f"{key}={e[key]}")
    if e.get("articles"):
        parts.append("art " + ",".join(e["articles"]))
    return f"  [{'; '.join(parts)}]" if parts else ""


def card(rule_id: str) -> str:
    r = NODES.get(rule_id)
    if not r or r["type"] != "rule":
        return f"{rule_id}: not a rule id\n"
    out = [f"== {r['id']}  {r['label']}  (arts {', '.join(r.get('articles', []))}; scope {r.get('scope')})",
           f"   {r.get('summary', '')}", f"   quote: {r.get('quote', '')}"]
    edges = [e for e in O["edges"] if e["source"] == rule_id]
    for etype in ROLE_EDGES:
        rows = [e for e in edges if e["type"] == etype]
        if rows:
            out.append(f"-- {etype}")
            for e in rows:
                c = NODES.get(e["target"], {})
                out.append(f"   {e['target']}: {c.get('label', '')}{_extras(e)}")
                if c.get("quote"):
                    out.append(f"      \"{c['quote']}\"")
    for etype in ACTION_EDGES:
        rows = [e for e in edges if e["type"] == etype]
        if rows:
            out.append(f"-- {etype}: " + "; ".join(e["target"] + _extras(e) for e in rows))
    links = [e for e in O["edges"] if e["type"] in RULE_EDGES and rule_id in (e["source"], e["target"])]
    if links:
        out.append("-- rule links (use these exact triples in coverage.rule_edges)")
        for e in links:
            out.append(f"   [\"{e['source']}\", \"{e['type']}\", \"{e['target']}\"]  {e.get('note', '')}")
    seeds = [s for s in SEEDS if s["rule"] == rule_id]
    if seeds:
        out.append("-- seed paths (drafts; condition ids may predate v3 merges, re-check them above)")
        for s in seeds:
            out.append(f"   {s['id']} [{s['outcome']}] {s['situation']}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for rid in sys.argv[1:]:
        print(card(rid))
