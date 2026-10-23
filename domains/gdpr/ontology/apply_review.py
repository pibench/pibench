"""Apply the expert review (review/fable_review.json) to the ontology graph.

One review pass, applied mechanically on top of build_ontology.py's output.
Run order: build_structure.py -> build_ontology.py -> apply_review.py.

Decisions that depart from a finding are listed in DEVIATIONS and written to
review/decisions.json together with what was applied for every finding.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
G = json.load(open(HERE / "gdpr_ontology.json"))
REVIEW = json.load(open(HERE / "review" / "fable_review.json"))

nodes = {n["id"]: n for n in G["nodes"]}
edges: dict[tuple[str, str, str], dict] = {(e["source"], e["type"], e["target"]): e for e in G["edges"]}
log: dict[str, list[str]] = defaultdict(list)
current = "setup"

# Findings applied differently from the reviewer's literal fix, and why.
DEVIATIONS = {
    "F001": "retyped to the new `blocked_by` edge (a defeater of the permission) instead of `triggered_by`",
    "F008": "retyped to the new `blocked_by` edge instead of `triggered_by`",
    "F005": "removed the 22(2)(b) trigger from DR-17 instead of splitting DR-17 into two rules",
    "F011": "added SC-01 and its conditions; kept K.GP.not_established_in_union_art3_2 on GP-05 "
            "(it is the exact combined Art 27 test) and linked GP-05 depends_on SC-01",
    "F056": "merged the processing-side legal-claims nodes; kept K.XT.necessary_for_legal_claims separate "
            "because Art 49(1)(e) tests the transfer, not the processing",
    "F057": "deadlines get articles and quotes; actions are grounded through the rules that require or "
            "forbid them (derived), roles stay design-layer nodes from rule_inventory.md",
    "F059": "normalised subparagraph ids and moved recitals to a `recitals` field; recital text is not parsed",
    "F064": "added the implements edges; rule_inventory.md is left unchanged (documented in ONTOLOGY.md)",
}
BLOCKED_BY_FINDINGS = {"F001", "F008"}
SKIP_KEYS = {"note", "alternative", "keep", "replace_with", "policy", "recommended", "coverage_rule",
             "schema", "docs", "audit_list", "also", "rule", "summary_patch"}


def say(msg: str) -> None:
    log[current].append(msg)


def layer_for(ntype: str) -> str:
    return {"condition": "rule", "deadline": "rule", "rule": "rule", "action": "operational",
            "role": "operational"}.get(ntype, "legal")


def add_node(spec: dict) -> None:
    spec = dict(spec)
    nid = spec["id"]
    if nid in nodes:
        nodes[nid].update({k: v for k, v in spec.items() if v is not None})
        say(f"updated node {nid}")
        return
    spec.setdefault("layer", layer_for(spec.get("type", "concept")))
    spec.setdefault("label", spec.get("quote", nid)[:120] if spec.get("type") == "condition" else nid)
    spec["added_by_review"] = current
    nodes[nid] = spec
    say(f"added node {nid}")


def add_edge(spec: dict) -> None:
    s, t, d = spec["source"], spec["type"], spec["target"]
    for end in (s, d):
        if end not in nodes:
            say(f"SKIPPED edge {s} -{t}-> {d}: unknown node {end}")
            return
    key = (s, t, d)
    attrs = {k: v for k, v in spec.items() if k not in ("source", "type", "target")}
    if key in edges:
        edges[key].update(attrs)
        say(f"updated edge {s} -{t}-> {d}")
    else:
        edges[key] = {"source": s, "type": t, "target": d, **attrs, "added_by_review": current}
        say(f"added edge {s} -{t}-> {d}")


def remove_edge(spec: dict) -> None:
    key = (spec["source"], spec["type"], spec["target"])
    if edges.pop(key, None) is not None:
        say(f"removed edge {key[0]} -{key[1]}-> {key[2]}")
    else:
        say(f"edge not present (nothing to remove) {key[0]} -{key[1]}-> {key[2]}")


def retype_edge(spec: dict) -> None:
    old = (spec["source"], spec["from"], spec["target"])
    new_type = "blocked_by" if current in BLOCKED_BY_FINDINGS else spec["to"]
    e = edges.pop(old, None)
    if e is None:
        say(f"edge to retype not found {old}")
        return
    e = {**e, "type": new_type, **{k: v for k, v in spec.items() if k in ("note", "articles")}}
    edges[(spec["source"], new_type, spec["target"])] = e
    say(f"retyped {old[0]} -{old[1]}-> {old[2]} to {new_type}")


def update_edge(spec: dict) -> None:
    key = (spec["source"], spec["type"], spec["target"])
    if key not in edges:
        say(f"edge to update not found {key}")
        return
    edges[key].update({k: v for k, v in spec.items() if k not in ("source", "type", "target")})
    say(f"updated edge {key[0]} -{key[1]}-> {key[2]}")


def apply_attrs(spec: dict) -> None:
    """Set qualifies / conjunct_with / when / note on an existing edge (or add it)."""
    etype = spec.get("type")
    candidates = [k for k in edges if k[0] == spec["source"] and k[2] == spec["target"] and (etype is None or k[1] == etype)]
    if not candidates:
        if etype:
            add_edge(spec)
        else:
            say(f"edge for attributes not found {spec['source']} -> {spec['target']}")
        return
    for key in candidates:
        edges[key].update({k: v for k, v in spec.items() if k not in ("source", "type", "target")})
        say(f"set {', '.join(k for k in spec if k not in ('source', 'type', 'target'))} on {key[0]} -{key[1]}-> {key[2]}")


def rename_node(old: str, new: str, fields: dict) -> None:
    node = nodes.pop(old)
    node.update(fields)
    node["id"] = new
    node.setdefault("aliases", []).append({"id": old})
    nodes[new] = node
    for key in list(edges):
        if old in (key[0], key[2]):
            e = edges.pop(key)
            nk = (new if key[0] == old else key[0], key[1], new if key[2] == old else key[2])
            edges[nk] = {**e, "source": nk[0], "target": nk[2]}
    say(f"renamed {old} -> {new}")


def merge(keep, drop, articles_union=None, note=None) -> None:
    keeps = keep if isinstance(keep, list) else [keep]
    drops = drop if isinstance(drop, list) else [drop]
    for d in drops:
        if d not in nodes:
            say(f"merge: {d} not present")
            continue
        dropped = nodes.pop(d)
        for k in keeps:
            kn = nodes[k]
            kn["articles"] = list(dict.fromkeys((kn.get("articles") or []) + (dropped.get("articles") or []) + (articles_union or [])))
            kn.setdefault("aliases", []).append({"id": d, "label": dropped.get("label"), "articles": dropped.get("articles", [])})
        for key in list(edges):
            if d in (key[0], key[2]):
                e = edges.pop(key)
                for k in keeps:
                    nk = (k if key[0] == d else key[0], key[1], k if key[2] == d else key[2])
                    if nk[0] != nk[2]:
                        edges.setdefault(nk, {**e, "source": nk[0], "target": nk[2]})
        say(f"merged {d} into {', '.join(keeps)}")


def apply_finding(f: dict) -> None:
    global current
    current = f["id"]
    fix, details = f["fix"], f["fix"].get("details", {})
    op = fix.get("op")
    # retype before remove: a finding may retype an edge and remove its duplicate elsewhere
    for key, val in sorted(details.items(), key=lambda kv: 0 if kv[0] == "retype_edge" else 1):
        if key in SKIP_KEYS:
            continue
        if key == "edges":
            for e in val:
                if op == "remove_edge":
                    remove_edge(e)
                elif op == "retype_edge":
                    retype_edge(e)
                elif op in ("add_edge", "add_node", "other"):
                    add_edge(e)
                else:
                    say(f"unhandled edges under op {op}")
        elif key in ("add_edge",):
            for e in (val if isinstance(val, list) else [val]):
                add_edge(e)
        elif key == "optionally_add":
            add_edge(val)
        elif key in ("remove_edge", "review"):
            for e in val:
                remove_edge(e)
        elif key == "retype_edge":
            for e in val:
                retype_edge(e)
        elif key == "update_edge":
            for e in (val if isinstance(val, list) else [val]):
                update_edge(e)
        elif key == "apply":
            for e in val:
                apply_attrs(e)
        elif key in ("nodes", "add_node", "node") and op in ("add_node", "add_edge", "other"):
            items = val if isinstance(val, list) else [val]
            for n in items:
                add_node(n)
        elif key == "nodes" and op == "update_node":
            for nid, fields in val.items():
                if nid in nodes:
                    nodes[nid].update(fields)
                    say(f"updated node {nid} ({', '.join(fields)})")
        elif key == "node" and op == "update_node":
            nid = val if isinstance(val, str) else val.get("id")
            fields = {k: v for k, v in details.items() if k not in ("node", "add_edge", "also") and k not in SKIP_KEYS}
            if nid in nodes:
                nodes[nid].update(fields)
                say(f"updated node {nid} ({', '.join(fields)})")
        elif key in ("articles", "summary", "definition", "defined_in") and op == "update_node":
            continue  # handled with "node"
        elif key in ("update_node", "node_updates"):
            for nid, fields in val.items():
                if "id" in fields and fields["id"] != nid:
                    rename_node(nid, fields["id"], {k: v for k, v in fields.items() if k != "id"})
                elif nid in nodes:
                    nodes[nid].update(fields)
                    say(f"updated node {nid} ({', '.join(fields)})")
        elif key == "conditions_set_overlay_true":
            for nid in val:
                if nid in nodes:
                    nodes[nid]["overlay"] = True
                    say(f"set overlay on {nid}")
        elif key in ("set_polarity", "also_set_polarity"):
            for nid, pol in val.items():
                if nid in nodes:
                    nodes[nid]["polarity_override"] = pol
                    say(f"polarity of {nid} fixed to {pol}")
        elif key == "merges":
            for m in val:
                if current == "F056" and m["keep"] == "K.DR.legal_claims_establishment_exercise_defence":
                    m = {**m, "drop": [d for d in m["drop"] if d != "K.XT.necessary_for_legal_claims"],
                         "articles_union": [a for a in m["articles_union"] if a != "49(1)(e)"]}
                if "drop_edge_only" in m:
                    s, t, d = m["drop_edge_only"].split()
                    remove_edge({"source": s, "type": t, "target": d})
                else:
                    merge(m["keep"], m["drop"], m.get("articles_union"))
        elif key == "retarget":
            for r in val:
                if "source" in r:
                    e = edges.pop((r["source"], r["type"], r["from"]), None)
                    if e:
                        add_edge({**e, "target": r["to"]})
                else:
                    a, b = [x.strip() for x in r["from"].split("->")]
                    c, d = [x.strip() for x in r["to"].split("->")]
                    remove_edge({"source": a, "type": "precedes", "target": b})
                    add_edge({"source": c, "type": "precedes", "target": d})
        elif key == "remove_open_question":
            before = len(G["open_questions"])
            G["open_questions"] = [q for q in G["open_questions"]
                                   if not (q["fragment"] == "A1" and "Article 9" in q["question"] and "6(1)" in q["question"])][:]
            say(f"removed {before - len(G['open_questions'])} open question(s)")
        elif key == "note_for_kept_edges":
            for t in ("PF-01", "PF-04", "PF-05"):
                update_edge({"source": "OL-01", "type": "overrides", "target": t,
                             "note": "only insofar as Art 5 corresponds to the rights and obligations in Arts 12-22"})
        elif key == "normalise":
            normalise(val)
        elif key == "recitals":
            move_recitals()
        else:
            say(f"UNHANDLED key {key} (op {op})")


def normalise(mapping: dict) -> None:
    def fix(ref: str) -> list[str]:
        if ref in mapping:
            m = mapping[ref]
            return m if isinstance(m, list) else [m["articles"]]
        return [ref]
    count = 0
    for obj in list(nodes.values()) + list(edges.values()):
        for field in ("articles",):
            if obj.get(field):
                new = [x for r in obj[field] for x in fix(r)]
                if new != obj[field]:
                    obj[field] = list(dict.fromkeys(new))
                    count += 1
    say(f"normalised article ids on {count} items")


def move_recitals() -> None:
    count = 0
    for obj in list(nodes.values()) + list(edges.values()):
        arts = obj.get("articles") or []
        rec = [int(m.group(1)) for a in arts for m in [re.match(r"Recital (\d+)", a)] if m]
        if rec:
            obj["articles"] = [a for a in arts if not a.startswith("Recital")]
            obj["recitals"] = sorted(set((obj.get("recitals") or []) + rec))
            count += 1
    say(f"moved recital references to `recitals` on {count} items")


for finding in REVIEW["findings"]:
    apply_finding(finding)

# ── one-off fixes whose instructions are prose ───────────────────────────
current = "F028"
nodes["DR-05"]["summary"] = re.sub(r"Grounds \(a\), \(b\) and \(c\)[^.]*\.", "", nodes["DR-05"].get("summary", "")).strip() + \
    " Ground (b) depends on Union/Member State law and needs an overlay; grounds (a) and (c) may need one depending on the Art 85 / Art 9(2)(h)-(i) basis relied on."
say("rewrote DR-05 summary overlay sentence")
current = "F011"
nodes["SC-01"].update({"scope": "core", "summary": "The GDPR applies to wholly or partly automated processing, or manual processing in a filing system, by an EU-established controller or processor, or by a non-EU one offering goods or services to, or monitoring, people in the Union; purely personal or household activity is excluded."})
G["meta"]["groups"]["SC"] = "Material & territorial scope"
current = "F053"
nodes["C.data_subject"].update({"definition": "an identified or identifiable natural person ('data subject'); an identifiable natural person is one who can be identified, directly or indirectly", "defined_in": "4(1)"})
add_edge({"source": "C.data_subject", "type": "defined_in", "target": "ART.4", "at": ["4(1)"]})

# ── hygiene after the review (own check, not a finding) ──────────────────
current = "post-review hygiene"
add_edge({"source": "GP-11", "type": "triggered_by", "target": "K.GP.organisation_acts_as_processor", "articles": ["30(2)"],
          "note": "the processor's own record of processing activities"})
merge("K.CS.child_below_applicable_age", "K.CS.child_at_or_above_threshold")

update_edge({"source": "XT-01", "type": "requires_action", "target": "A.block_transfer",
             "when": "K.XT.no_adequacy_no_safeguards", "note": "and no Art 49 derogation applies (no Chapter V route)"})

# Art 46(3): authorisation goes with EITHER ad hoc clauses OR an administrative arrangement.
key = ("XT-03", "triggered_by", "K.XT.sa_transfer_authorisation_obtained")
if key in edges and "conjunct_with" in edges[key]:
    edges[key]["conjunct_with_any"] = edges[key].pop("conjunct_with")
    say("XT-03 authorisation: conjunct_with -> conjunct_with_any (46(3)(a) or (b))")

# Re-point condition ids inside edge fields after merges and renames.
alias_of = {a["id"]: n["id"] for n in nodes.values() for a in (n.get("aliases") or []) if isinstance(a, dict) and a.get("id")}
unresolved = []
for e in edges.values():
    for field in ("qualifies", "conjunct_with", "conjunct_with_any", "when"):
        if field not in e:
            continue
        vals = e[field] if isinstance(e[field], list) else [e[field]]
        fixed = []
        for v in vals:
            neg = v.startswith("NOT ")
            cid = v[4:] if neg else v
            cid = alias_of.get(cid, cid)
            if cid not in nodes:
                unresolved.append(f"{e['source']} -{e['type']}-> {e['target']} {field}: {cid}")
            fixed.append(("NOT " if neg else "") + cid)
        e[field] = fixed if isinstance(e[field], list) else fixed[0]
say(f"re-pointed edge-field references; unresolved: {unresolved}")

# ── derived fields ───────────────────────────────────────────────────────
current = "derived"
ART_IDS = {f"ART.{n}" for n in range(1, 100)}


def article_of(ref: str) -> str | None:
    m = re.match(r"^(\d+)", ref.strip())
    return f"ART.{int(m.group(1))}" if m and f"ART.{int(m.group(1))}" in ART_IDS else None


for n in nodes.values():  # grounding for nodes added by the review and for deadlines
    if n["type"] in ("condition", "rule", "deadline", "concept", "actor") and n.get("added_by_review") or n["type"] == "deadline":
        for a in n.get("articles", []) or []:
            art = article_of(a)
            if art:
                edges.setdefault((n["id"], "grounded_in", art), {"source": n["id"], "type": "grounded_in", "target": art, "at": [a]})
for (s, t, d), e in list(edges.items()):  # actions inherit articles from the rules that require/forbid them
    if t in ("requires_action", "forbids_action") and nodes.get(d, {}).get("type") == "action":
        refs = e.get("articles") or nodes[s].get("articles") or []
        nodes[d]["articles"] = list(dict.fromkeys((nodes[d].get("articles") or []) + refs))
        nodes[d]["grounding"] = "derived from the rules that require or forbid it"

ROLE = {"triggered_by": "trigger", "has_exception": "exception", "blocked_by": "defeater", "weighs": "factor"}
for n in nodes.values():
    if n["type"] != "condition":
        continue
    roles = sorted({ROLE[t] for (s, t, d) in edges if d == n["id"] and t in ROLE})
    n["roles"] = roles
    n["polarity"] = n.pop("polarity_override", None) or (roles[0] if len(roles) == 1 else ("mixed" if roles else "state"))

# ── validation ───────────────────────────────────────────────────────────
problems = [f"missing endpoint in {k}" for k in edges if k[0] not in nodes or k[2] not in nodes]
cycles = []
dep = defaultdict(set)
for (s, t, d) in edges:
    if t == "depends_on":
        dep[s].add(d)


def find_cycle(start, node, seen):
    for nxt in dep.get(node, ()):
        if nxt == start:
            return True
        if nxt not in seen:
            seen.add(nxt)
            if find_cycle(start, nxt, seen):
                return True
    return False


cycles = sorted(r for r in dep if find_cycle(r, r, set()))
degree = Counter()
for (s, _, d) in edges:
    degree[s] += 1
    degree[d] += 1
isolated_conditions = sorted(n for n in nodes if nodes[n]["type"] == "condition" and not any(
    d == n and t in ("triggered_by", "has_exception", "blocked_by", "weighs") for (s, t, d) in edges))
bad_articles = sorted({a for obj in list(nodes.values()) + list(edges.values()) for a in (obj.get("articles") or [])
                       if not re.match(r"^\d+(\(\w+\))*$", a) and not re.match(r"^\d+-\d+$", a)})

G["nodes"] = sorted(nodes.values(), key=lambda n: n["id"])
G["edges"] = sorted(edges.values(), key=lambda e: (e["type"], e["source"], e["target"]))
G["meta"]["version"] = 3
G["meta"]["review"] = {"by": "Fable (single expert pass)", "findings": len(REVIEW["findings"]),
                       "applied": "review/decisions.json"}
(HERE / "gdpr_ontology.json").write_text(json.dumps(G, indent=1, ensure_ascii=False))

decisions = []
for f in REVIEW["findings"]:
    decisions.append({"id": f["id"], "severity": f["severity"], "problem": f["problem"][:240],
                      "decision": "applied with change" if f["id"] in DEVIATIONS else "applied",
                      "why_changed": DEVIATIONS.get(f["id"]), "actions": log.get(f["id"], [])})
(HERE / "review" / "decisions.json").write_text(json.dumps({"derived": log.get("derived", []), "findings": decisions}, indent=1, ensure_ascii=False))

unhandled = [(fid, m) for fid, msgs in log.items() for m in msgs if "UNHANDLED" in m or "SKIPPED" in m or "not found" in m]
print("nodes by type:", dict(Counter(n["type"] for n in nodes.values())))
print("edges by type:", dict(Counter(k[1] for k in edges)))
print(f"total nodes {len(nodes)}, edges {len(edges)}")
print(f"problems: {len(problems)}  depends_on cycles: {cycles}")
print(f"conditions attached to no rule: {len(isolated_conditions)} {isolated_conditions[:12]}")
print(f"non-standard article ids left: {bad_articles[:15]}")
print(f"edge-field references unresolved: {unresolved}")
print(f"findings with notes to check: {len(unhandled)}")
for fid, m in unhandled:
    print(f"  {fid}: {m}")
