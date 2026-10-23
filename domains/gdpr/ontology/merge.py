"""Merge GDPR ontology fragments, validate references, and report coverage targets.

Usage: python3 merge.py <fragments_dir> <out_dir> <rule_inventory.md>
Writes <out_dir>/gdpr_ontology.json and prints a validation report.
"""
import collections
import json
import re
import sys
from pathlib import Path

frag_dir, out_dir, inventory = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
schema = (frag_dir / "SCHEMA.md").read_text()

EDGE_TYPES = {"triggered_by", "has_exception", "requires_action", "forbids_action", "precedes",
              "due_within", "applies_to", "refines", "depends_on", "overrides", "tension_with",
              "performed_by"}
OUTCOMES = {"ALLOW", "DENY", "ESCALATE"}
GROUP_NAMES = {
    "PF": "Processing principles & lawful basis", "CS": "Consent & protected data",
    "CM": "Transparency & request handling", "DR": "Data-subject rights",
    "GP": "Controllers, processors & accountability", "SB": "Security & breaches",
    "RA": "DPIA & DPO", "XT": "International transfers", "OL": "Conditional mechanisms & overlays",
}

# Shared vocabulary from SCHEMA.md
vocab_block = schema.split("## Shared vocabulary", 1)[1]
vocab_ids = re.findall(r"\b([CATR]\.[a-z0-9_.]+)", vocab_block)
KIND = {"C": "concept", "A": "action", "T": "deadline", "R": "role"}


def humanize(node_id: str) -> str:
    tail = node_id.split(".", 1)[1].replace("basis.", "basis: ").replace("_", " ")
    return tail[:1].upper() + tail[1:]


# Same fact modelled by two fragments -> one canonical node (reviewed by hand).
# Look-alikes with different legal tests are deliberately NOT merged, e.g.
# legal claims for processing vs. for a transfer (49(1)(e)), processing risk vs.
# breach risk, large-scale special data vs. core-activity test (37(1)(c)).
ALIASES = {
    "K.PF.accuracy_unverified": "K.DR.accuracy_contested_unverified",
    "K.RA.large_scale_special_or_criminal_data": "K.CS.large_scale_special_or_criminal",
    "K.GP.large_scale_special_or_criminal_data": "K.CS.large_scale_special_or_criminal",
    "K.DR.processing_public_task_or_official_authority": "K.PF.basis_public_task",
    "K.DR.public_interest_task_or_official_authority": "K.PF.basis_public_task",
    "K.DR.request_received_by_processor": "K.GP.rights_request_reaches_processor",
    "K.CM.controller_demonstrably_cannot_identify": "K.PF.controller_cannot_identify",
    "K.CS.exc_legal_claims": "K.DR.legal_claims_establishment_exercise_defence",
    "K.DR.subject_opposes_erasure_requests_restriction": "K.DR.unlawful_processing_erasure_opposed",
    "K.PF.security_incident_detected": "K.SB.personal_data_breach_occurred",
    "K.DR.art9_2_g_substantial_public_interest_law": "K.CS.exc_substantial_public_interest_law",
    "K.DR.collected_for_iss_offer_to_child": "K.CS.iss_offered_directly_to_child",
    "K.DR.data_transferred_to_third_country": "K.XT.destination_third_country_or_io",
    "K.CM.third_country_transfer_intended": "K.XT.destination_third_country_or_io",
    "K.CM.subject_provides_identifying_information": "K.PF.subject_supplies_identifying_info",
    "K.GP.approved_code_or_certification_adhered": "K.OL.code_or_certification_adherence",
    "K.DR.direct_marketing_objection_received": "K.DR.objection_to_direct_marketing",
    "K.CM.purposes_do_not_require_identification": "K.PF.identification_not_required",
    "K.DR.art9_2_a_explicit_consent": "K.CS.exc_explicit_consent",
}


def canon(x):
    return ALIASES.get(x, x)


nodes: dict[str, dict] = {}
for vid in dict.fromkeys(vocab_ids):
    nodes[vid] = {"id": vid, "type": KIND[vid[0]], "label": humanize(vid), "shared": True}

inventory_ids = re.findall(r"^\| ((?:PF|CS|CM|DR|GP|SB|RA|XT|OL)-\d\d) \| ([^|]+) \| ([^|]+) \|", inventory.read_text(), re.M)
inventory_map = {rid: (arts.strip(), text.strip()) for rid, arts, text in inventory_ids}

alias_nodes: dict[str, dict] = {}
rules: dict[str, dict] = {}
edges: dict[tuple, dict] = {}
paths: dict[str, dict] = {}
questions: list[dict] = []
problems: list[str] = []
fragments = sorted(frag_dir.glob("fragment_*.json"))

for frag_path in fragments:
    frag = json.loads(frag_path.read_text())
    name = frag.get("fragment", frag_path.stem)
    for r in frag.get("rules", []):
        if r["id"] in rules:
            problems.append(f"{name}: duplicate rule {r['id']}")
        r = {**r, "type": "rule", "fragment": name}
        r.setdefault("group", r["id"].split("-")[0])
        rules[r["id"]] = r
    for n in frag.get("nodes", []):
        nid = n["id"]
        if nid in ALIASES:
            alias_nodes[nid] = {**n, "fragment": name}
            continue
        if nid in nodes and not nodes[nid].get("shared"):
            nodes[nid].setdefault("also_from", []).append(name)
            continue
        if nid in nodes and nodes[nid].get("shared"):
            continue  # vocabulary wins
        nodes[nid] = {**n, "fragment": name}
    for e in frag.get("edges", []):
        e = {**e, "source": canon(e["source"]), "target": canon(e["target"])}
        key = (e["source"], e["type"], e["target"])
        if key in edges:
            continue
        edges[key] = {**e, "fragment": name}
    for p in frag.get("decision_paths", []):
        if p["id"] in paths:
            problems.append(f"{name}: duplicate path id {p['id']}")
        p = {**p, "fragment": name}
        for key in ("conditions_true", "conditions_false", "required_actions", "forbidden_actions"):
            p[key] = list(dict.fromkeys(canon(x) for x in (p.get(key) or [])))
        p["action_order"] = [[canon(a) for a in pair] for pair in (p.get("action_order") or [])]
        paths[p["id"]] = p
    for q in frag.get("open_questions", []):
        questions.append({"fragment": name, "question": q})

for alias, node in alias_nodes.items():
    target = ALIASES[alias]
    if target in nodes:
        nodes[target].setdefault("aliases", []).append({"id": alias, "label": node.get("label"), "articles": node.get("articles", [])})
        merged_articles = list(dict.fromkeys((nodes[target].get("articles") or []) + (node.get("articles") or [])))
        nodes[target]["articles"] = merged_articles
all_ids = set(nodes) | set(rules)
for pid, p in paths.items():
    both = set(p["conditions_true"]) & set(p["conditions_false"])
    if both:
        problems.append(f"path {pid}: condition both true and false after aliasing: {sorted(both)}")

# ── validation ──
for (s, t_, d), e in edges.items():
    if t_ not in EDGE_TYPES:
        problems.append(f"edge type '{t_}' not allowed: {s} -> {d}")
    for end in (s, d):
        if end not in all_ids:
            problems.append(f"edge endpoint missing: {end} ({s} -{t_}-> {d}, {e['fragment']})")
for pid, p in paths.items():
    if p.get("rule") not in rules:
        problems.append(f"path {pid}: unknown rule {p.get('rule')}")
    for ref in p.get("also_rules", []):
        if ref not in rules:
            problems.append(f"path {pid}: unknown also_rule {ref}")
    for key in ("conditions_true", "conditions_false", "required_actions", "forbidden_actions"):
        for ref in p.get(key, []) or []:
            if ref not in all_ids:
                problems.append(f"path {pid}: unknown {key} ref {ref}")
    for pair in p.get("action_order", []) or []:
        for ref in pair:
            if ref not in all_ids:
                problems.append(f"path {pid}: unknown action_order ref {ref}")
    if p.get("outcome") not in OUTCOMES:
        problems.append(f"path {pid}: bad outcome {p.get('outcome')}")
    if p.get("outcome") == "ESCALATE" and not p.get("escalate_to"):
        problems.append(f"path {pid}: ESCALATE without escalate_to")

missing_rules = sorted(set(inventory_map) - set(rules))
extra_rules = sorted(set(rules) - set(inventory_map))
paths_by_rule = collections.defaultdict(list)
for p in paths.values():
    paths_by_rule[p["rule"]].append(p)
rules_without_paths = sorted(r for r in rules if not paths_by_rule.get(r))
one_sided = sorted(r for r, ps in paths_by_rule.items() if len({p["outcome"] for p in ps}) == 1)

# ── stats ──
outcomes = collections.Counter(p["outcome"] for p in paths.values())
esc_ground = collections.Counter(p.get("escalation_grounding") for p in paths.values() if p["outcome"] == "ESCALATE")
node_types = collections.Counter(n["type"] for n in nodes.values())
edge_types = collections.Counter(k[1] for k in edges)
rule_rule = [k for k in edges if k[0] in rules and k[2] in rules]
cross_group = [k for k in rule_rule if rules[k[0]]["group"] != rules[k[2]]["group"]]
used = {k[0] for k in edges} | {k[2] for k in edges}
for p in paths.values():
    used |= set(p.get("conditions_true", []) + p.get("conditions_false", []) + p.get("required_actions", []) + p.get("forbidden_actions", []))
orphans = sorted(n for n in nodes if n not in used and not nodes[n].get("shared"))
unused_vocab = sorted(n for n in nodes if n not in used and nodes[n].get("shared"))
fm = collections.Counter(f for p in paths.values() for f in p.get("failure_modes", []))
scope = collections.Counter(r.get("scope") for r in rules.values())

out = {
    "meta": {
        "name": "GDPR ontology", "source": "Regulation (EU) 2016/679 (domains/gdpr/policy.md) + rule_inventory.md",
        "groups": GROUP_NAMES, "edge_types": sorted(EDGE_TYPES), "outcomes": sorted(OUTCOMES),
        "fragments": [f.stem for f in fragments],
    },
    "rules": sorted(rules.values(), key=lambda r: r["id"]),
    "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
    "edges": [dict(source=k[0], type=k[1], target=k[2], **{x: v for x, v in e.items() if x not in ("source", "type", "target")}) for k, e in edges.items()],
    "decision_paths": sorted(paths.values(), key=lambda p: p["id"]),
    "open_questions": questions,
    "coverage": {"unit": "decision_path", "scenarios_per_path": {pid: 0 for pid in sorted(paths)},
                 "scenarios_per_rule_edge": {f"{k[0]}|{k[1]}|{k[2]}": 0 for k in rule_rule}},
}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "gdpr_ontology.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

print(f"fragments: {[f.name for f in fragments]}")
print(f"rules: {len(rules)}/{len(inventory_map)}  missing={missing_rules}  extra={extra_rules}")
print(f"rule scope: {dict(scope)}")
print(f"nodes by type: {dict(node_types)}")
print(f"edges: {len(edges)} by type {dict(edge_types)}")
print(f"rule-to-rule edges: {len(rule_rule)}  cross-group: {len(cross_group)}")
print(f"decision paths: {len(paths)}  outcomes: {dict(outcomes)}  escalation grounding: {dict(esc_ground)}")
print(f"overlay_required paths: {sum(1 for p in paths.values() if p.get('overlay_required'))}")
print(f"rules without paths: {rules_without_paths}")
print(f"rules whose paths all share one outcome: {one_sided}")
print(f"orphan non-vocab nodes: {len(orphans)} {orphans[:15]}")
print(f"unused shared vocab: {unused_vocab}")
print(f"failure modes: {fm.most_common()}")
print(f"aliases merged: {len(alias_nodes)} of {len(ALIASES)} listed")
print(f"open questions: {len(questions)}")
print(f"PROBLEMS: {len(problems)}")
for pr in problems[:80]:
    print("  -", pr)
