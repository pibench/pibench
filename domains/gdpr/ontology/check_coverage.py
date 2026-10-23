"""Check that every obligation paragraph of the GDPR is covered by the ontology.

Coverage = the paragraph is cited by a rule unit or by any node (condition,
action, ...) in gdpr_ontology.json. Paragraphs whose duty falls on the
Commission, Member States, supervisory authorities or the Board are reported
separately: they are institutional, not agent obligations.

Usage: python3 check_coverage.py [structure.json] [gdpr_ontology.json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = json.load(open(sys.argv[1] if len(sys.argv) > 1 else HERE / "structure.json"))
O = json.load(open(sys.argv[2] if len(sys.argv) > 2 else HERE / "gdpr_ontology.json"))

arts = {a["num"]: a for a in S["articles"]}
paras_of = {n: [p["num"] for p in a["paragraphs"]] or [0] for n, a in arts.items()}
INSTITUTIONAL = re.compile(r"^(The Commission|Member States|Each Member State|The Board|The supervisory authority|Supervisory authorities|The competent supervisory authority|The lead supervisory authority|Each supervisory authority|The Commission may)\b")


def expand(ref: str) -> set[tuple[int, int]]:
    """'17(1)' -> {(17,1)}; '33(3)-(4)' -> {(33,3),(33,4)}; '77-80' -> all paras; '28(3)(a)-(d)' -> {(28,3)}."""
    ref = ref.split(",")[0].strip()
    m = re.fullmatch(r"(\d+)-(\d+)", ref)
    if m:
        return {(n, p) for n in range(int(m.group(1)), int(m.group(2)) + 1) for p in paras_of.get(n, [0])}
    m = re.fullmatch(r"(\d+)\((\d+)\)(?:\([a-z]+\))?(?:-\((\d+)\))?.*", ref)
    if m:
        n, a = int(m.group(1)), int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a
        return {(n, p) for p in range(a, b + 1)}
    m = re.fullmatch(r"(\d+)(?:\s.*)?", ref)
    if m:
        n = int(m.group(1))
        return {(n, p) for p in paras_of.get(n, [0])}
    return set()


covered_by: dict[tuple[int, int], set[str]] = {}
for r in [n for n in O["nodes"] if n["type"] == "rule"]:
    for ref in r.get("articles", []):
        for key in expand(ref):
            covered_by.setdefault(key, set()).add(r["id"])
for n in O["nodes"]:
    for ref in n.get("articles", []) or []:
        for key in expand(ref):
            covered_by.setdefault(key, set()).add(n["id"])

rows = []
for num in range(5, 50):
    a = arts[num]
    for p in a["paragraphs"] or [{"num": 0, "text": " ".join(a["intro"]), "points": [], "more": []}]:
        text = " ".join([p["text"], *p.get("more", []), *(pt["text"] for pt in p.get("points", []))])
        if not re.search(r"\bshall\b", text):
            continue
        institutional = bool(INSTITUTIONAL.match(p["text"]))
        key = (num, p["num"])
        rows.append({"para": f"{num}({p['num']})" if p["num"] else str(num), "title": a["title"],
                     "institutional": institutional, "covered_by": sorted(covered_by.get(key, set())),
                     "text": p["text"][:160]})

agent_rows = [r for r in rows if not r["institutional"]]
gaps = [r for r in agent_rows if not r["covered_by"]]
weak = [r for r in agent_rows if r["covered_by"] and not any(c[:2] in {"PF", "CS", "CM", "DR", "GP", "SB", "RA", "XT", "OL"} and "-" in c for c in r["covered_by"])]
print(f"obligation paragraphs in Arts 5-49: {len(rows)} (agent-relevant {len(agent_rows)}, institutional {len(rows) - len(agent_rows)})")
print(f"covered by a rule unit: {len(agent_rows) - len(gaps) - len(weak)} | covered only by facts/actions: {len(weak)} | NOT covered: {len(gaps)}")
for r in gaps:
    print(f"  GAP  {r['para']:8s} {r['title'][:40]:40s} {r['text'][:110]}")
for r in weak:
    print(f"  WEAK {r['para']:8s} {r['title'][:40]:40s} -> {', '.join(r['covered_by'][:4])}")
json.dump({"rows": rows}, open(HERE / "coverage_check.json", "w"), indent=1, ensure_ascii=False)
