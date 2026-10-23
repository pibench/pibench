"""Assemble the GDPR ontology graph (v2) from three sources.

1. structure.json   — chapters, sections, articles, definitions and the
                      article-to-article references the text makes
                      (deterministic, from build_structure.py).
2. merged fragments — the 90 rule units with their trigger/exception facts,
                      actions, deadlines and rule-to-rule relations
                      (merge.py output, decision paths removed).
3. this file        — the legal concept layer: Article 5 principles, Article
                      6(1) lawful bases, data-subject rights, actors, and the
                      mapping of Article 4 defined terms onto concept nodes.

Writes gdpr_ontology.json (graph only). Decision paths from the earlier draft
are kept separately in drafts/decision_paths_draft.json.

Usage: python3 build_ontology.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = json.load(open(HERE / "structure.json"))
V1 = json.load(open(HERE / "drafts" / "ontology_v1_with_paths.json"))

nodes: dict[str, dict] = {}
edges: dict[tuple[str, str, str], dict] = {}


def add_node(node: dict) -> None:
    if node["id"] in nodes:
        nodes[node["id"]].update({k: v for k, v in node.items() if v not in (None, [], "")})
    else:
        nodes[node["id"]] = node


def add_edge(source: str, etype: str, target: str, **attrs) -> None:
    key = (source, etype, target)
    if key in edges:
        for k, v in attrs.items():
            if isinstance(v, list):
                edges[key][k] = list(dict.fromkeys(edges[key].get(k, []) + v))
        return
    edges[key] = {"source": source, "type": etype, "target": target, **attrs}


def article_of(ref: str) -> str | None:
    m = re.match(r"^(\d+)", ref.strip())
    return f"ART.{int(m.group(1))}" if m and 1 <= int(m.group(1)) <= 99 else None


# ── 1. document layer ────────────────────────────────────────────────────
for ch in S["chapters"]:
    add_node({"id": ch["id"], "type": "chapter", "label": f"Chapter {ch['id'].split('.')[1]}: {ch['title']}", "layer": "document"})
for sec in S["sections"]:
    add_node({"id": sec["id"], "type": "section", "label": f"Section {sec['num']}: {sec['title']}", "layer": "document"})
    add_edge(sec["chapter"], "contains", sec["id"])
for art in S["articles"]:
    add_node({"id": art["id"], "type": "article", "label": f"Art. {art['num']} {art['title']}", "layer": "document",
              "num": art["num"], "title": art["title"], "chapter": art["chapter"], "section": art["section"],
              "text": {"intro": art["intro"], "paragraphs": art["paragraphs"], "points": art.get("points", [])}})
    add_edge(art["section"] or art["chapter"], "contains", art["id"])
for ref in S["references"]:
    if not ref["internal"]:
        add_edge(ref["source"], "references", ref["target"],
                 at=[f"{o['from']} → {o['to']}" for o in ref["occurrences"]][:12])

# ── 2. legal concept layer ───────────────────────────────────────────────
ACTOR_IDS = {
    "C.data_subject", "C.controller", "C.joint_controller", "C.processor", "C.sub_processor", "C.recipient",
    "C.third_party", "C.representative", "C.dpo", "C.supervisory_authority", "C.child",
    "C.parental_responsibility_holder", "C.public_authority", "C.court", "C.health_professional",
    "C.not_for_profit_body", "C.representative_body", "C.group_of_undertakings", "C.international_organisation",
}
for n in V1["nodes"]:
    if n["type"] != "concept":
        continue
    nid = n["id"]
    ntype = "lawful_basis" if nid.startswith("C.basis.") else ("actor" if nid in ACTOR_IDS else "concept")
    add_node({**{k: v for k, v in n.items() if k not in ("shared", "fragment", "proposed")}, "type": ntype, "layer": "legal"})

NEW_ACTORS = {
    "C.board": ("European Data Protection Board", "68"),
    "C.commission": ("European Commission", "45"),
    "C.member_state": ("Member State", "6"),
    "C.lead_supervisory_authority": ("Lead supervisory authority", "56"),
}
for nid, (label, art) in NEW_ACTORS.items():
    add_node({"id": nid, "type": "actor", "label": label, "layer": "legal", "articles": [art]})

# Article 4 definitions -> concept/actor nodes (existing ID where the concept already exists)
DEFINED = {
    "personal data": "C.personal_data", "processing": "C.processing", "restriction of processing": "C.restriction_of_processing",
    "profiling": "C.profiling", "pseudonymisation": "C.pseudonymised_data", "filing system": "C.filing_system",
    "controller": "C.controller", "processor": "C.processor", "recipient": "C.recipient", "third party": "C.third_party",
    "consent": "C.consent", "personal data breach": "C.personal_data_breach", "genetic data": "C.genetic_data",
    "biometric data": "C.biometric_data", "data concerning health": "C.health_data", "main establishment": "C.main_establishment",
    "representative": "C.representative", "enterprise": "C.enterprise", "group of undertakings": "C.group_of_undertakings",
    "binding corporate rules": "C.binding_corporate_rules", "supervisory authority": "C.supervisory_authority",
    "supervisory authority concerned": "C.supervisory_authority_concerned", "cross-border processing": "C.cross_border_processing",
    "relevant and reasoned objection": "C.relevant_and_reasoned_objection", "information society service": "C.information_society_service",
    "international organisation": "C.international_organisation",
}
for d in S["definitions"]:
    nid = DEFINED[d["term"]]
    existing = nodes.get(nid, {})
    add_node({"id": nid, "type": existing.get("type", "actor" if nid in ACTOR_IDS else "concept"), "layer": "legal",
              "label": d["term"][:1].upper() + d["term"][1:], "definition": d["definition"],
              "defined_in": d["article"], "articles": list(dict.fromkeys((existing.get("articles") or []) + [d["article"]]))})
    add_edge(nid, "defined_in", "ART.4", at=[d["article"]])

PRINCIPLES = [
    ("P.lawfulness_fairness_transparency", "Lawfulness, fairness and transparency", "5(1)(a)", "PF-01"),
    ("P.purpose_limitation", "Purpose limitation", "5(1)(b)", "PF-02"),
    ("P.data_minimisation", "Data minimisation", "5(1)(c)", "PF-03"),
    ("P.accuracy", "Accuracy", "5(1)(d)", "PF-04"),
    ("P.storage_limitation", "Storage limitation", "5(1)(e)", "PF-05"),
    ("P.integrity_confidentiality", "Integrity and confidentiality", "5(1)(f)", "PF-06"),
    ("P.accountability", "Accountability", "5(2)", "PF-07"),
]
for pid, label, art, rule in PRINCIPLES:
    add_node({"id": pid, "type": "principle", "label": label, "layer": "legal", "articles": [art]})
    add_edge(pid, "grounded_in", "ART.5", at=[art])
    add_edge(rule, "implements", pid, articles=[art])

LAWFUL_BASES = {"C.basis.consent": "6(1)(a)", "C.basis.contract": "6(1)(b)", "C.basis.legal_obligation": "6(1)(c)",
                "C.basis.vital_interests": "6(1)(d)", "C.basis.public_task": "6(1)(e)", "C.basis.legitimate_interests": "6(1)(f)"}
for nid, art in LAWFUL_BASES.items():
    nodes[nid]["articles"] = [art]
    add_edge(nid, "grounded_in", "ART.6", at=[art])
for cid, lb in {"K.PF.basis_consent": "C.basis.consent", "K.PF.basis_contract": "C.basis.contract",
                "K.PF.basis_pre_contract": "C.basis.contract", "K.PF.basis_legal_obligation": "C.basis.legal_obligation",
                "K.PF.basis_vital_interests": "C.basis.vital_interests", "K.PF.basis_public_task": "C.basis.public_task",
                "K.PF.basis_legitimate_interests": "C.basis.legitimate_interests"}.items():
    add_edge(cid, "instance_of", lb)

RIGHTS = [
    ("RT.information", "Right to be informed", ["13", "14"]), ("RT.access", "Right of access", ["15"]),
    ("RT.rectification", "Right to rectification", ["16"]), ("RT.erasure", "Right to erasure", ["17"]),
    ("RT.restriction", "Right to restriction of processing", ["18"]),
    ("RT.recipient_notification", "Notification of rectification, erasure or restriction", ["19"]),
    ("RT.portability", "Right to data portability", ["20"]), ("RT.object", "Right to object", ["21"]),
    ("RT.automated_decisions", "Right not to be subject to solely automated decisions", ["22"]),
    ("RT.withdraw_consent", "Right to withdraw consent", ["7(3)"]),
    ("RT.complaint", "Right to lodge a complaint with a supervisory authority", ["77"]),
    ("RT.remedy_against_sa", "Right to an effective judicial remedy against a supervisory authority", ["78"]),
    ("RT.remedy_against_controller", "Right to an effective judicial remedy against a controller or processor", ["79"]),
    ("RT.representation", "Right to be represented by a body or organisation", ["80"]),
    ("RT.compensation", "Right to compensation", ["82"]),
]
right_by_article: dict[str, str] = {}
for rid, label, arts in RIGHTS:
    add_node({"id": rid, "type": "right", "label": label, "layer": "legal", "articles": arts})
    for a in arts:
        add_edge(rid, "grounded_in", article_of(a), at=[a])
        right_by_article.setdefault(article_of(a), rid)
    add_edge(rid, "held_by", "C.data_subject")
    if rid in ("RT.complaint", "RT.remedy_against_sa"):
        add_edge(rid, "exercised_against", "C.supervisory_authority")
    else:
        add_edge(rid, "exercised_against", "C.controller")


# Where the GDPR establishes each concept that Article 4 does not define.
CONCEPT_ANCHORS = {
    "C.adequacy_decision": "45(1)", "C.appropriate_safeguards": "46(1)", "C.automated_decision": "22(1)",
    "C.board": "68(1)", "C.certification_mechanism": "42(1)", "C.child": "8(1)", "C.code_of_conduct": "40(1)",
    "C.commission": "45(1)", "C.court": "79(1)", "C.criminal_offence_data": "10", "C.data_subject": "4(1)",
    "C.derogation": "49(1)", "C.direct_marketing": "21(2)", "C.dpia": "35(1)", "C.dpo": "37(1)",
    "C.explicit_consent": "9(2)(a)", "C.health_professional": "9(3)", "C.international_agreement": "48",
    "C.joint_controller": "26(1)", "C.lawful_basis": "6(1)", "C.lead_supervisory_authority": "56(1)",
    "C.legislative_measure": "23(1)", "C.member_state": "6(2)", "C.not_for_profit_body": "9(2)(d)",
    "C.parental_responsibility_holder": "8(1)", "C.processing_record": "30(1)", "C.public_authority": "37(1)(a)",
    "C.public_register": "49(1)(g)", "C.purpose": "5(1)(b)", "C.recipient_list": "15(1)(c)",
    "C.representative_body": "80(1)", "C.retention_period": "13(2)(a)", "C.special_category_data": "9(1)",
    "C.sub_processor": "28(2)", "C.third_country": "44",
}
for nid, ref in CONCEPT_ANCHORS.items():
    if nid in nodes:
        nodes[nid]["articles"] = list(dict.fromkeys((nodes[nid].get("articles") or []) + [ref]))
        add_edge(nid, "grounded_in", article_of(ref), at=[ref])

# ── 3. rule layer (90 rule units) and facts ──────────────────────────────
for r in V1["rules"]:
    add_node({**{k: v for k, v in r.items() if k not in ("fragment",)}, "type": "rule", "layer": "rule"})
    for a in r.get("articles", []):
        art = article_of(a)
        if art:
            add_edge(r["id"], "grounded_in", art, at=[a])
            if r["group"] in ("DR", "CM", "OL") and art in right_by_article:
                add_edge(r["id"], "gives_effect_to", right_by_article[art])
    if r.get("obligated_party"):
        add_edge(r["id"], "obligates", r["obligated_party"])

for n in V1["nodes"]:
    if n["type"] in ("condition", "action", "deadline", "role"):
        layer = "rule" if n["type"] in ("condition", "deadline") else "operational"
        add_node({**{k: v for k, v in n.items() if k not in ("shared", "fragment")}, "layer": layer})
        if n["type"] == "condition":
            for a in n.get("articles", []) or []:
                art = article_of(a)
                if art:
                    add_edge(n["id"], "grounded_in", art, at=[a])

for e in V1["edges"]:
    add_edge(e["source"], e["type"], e["target"], **({"articles": e["articles"]} if e.get("articles") else {}),
             **({"note": e["note"]} if e.get("note") else {}))


# Legal links the text states explicitly (cross-references) that the rule
# layer did not yet carry. Each cites the referencing provision.
RIGHTS_13_22 = ["RT.information", "RT.access", "RT.rectification", "RT.erasure", "RT.restriction",
                "RT.recipient_notification", "RT.portability", "RT.object", "RT.automated_decisions"]
LEGAL_LINKS = [
    *[(cm, "applies_to", rt, ["12(1)", "12(2)"], "Art 12 modalities govern every Art 13-22 communication")
      for cm in ("CM-01", "CM-02", "CM-03", "CM-04", "CM-05") for rt in RIGHTS_13_22],
    ("CM-06", "applies_to", "RT.access", ["12(6)"], "identity doubts for Art 15-21 requests"),
    ("DR-01", "depends_on", "DR-16", ["15(1)(h)"], "access must cover automated decision-making under 22(1)"),
    ("GP-04", "depends_on", "CM-07", ["26(1)"], "arrangement allocates the Art 13 information duties"),
    ("GP-04", "depends_on", "CM-09", ["26(1)"], "arrangement allocates the Art 14 information duties"),
    ("GP-05", "depends_on", "CS-07", ["27(2)(a)"], "representative exemption excludes large-scale special-category data"),
    ("GP-05", "depends_on", "CS-09", ["27(2)(a)"], "representative exemption excludes large-scale criminal data"),
    ("GP-09", "supports", "SB-03", ["28(3)(f)"], "processor assists with Art 33"),
    ("GP-09", "supports", "SB-07", ["28(3)(f)"], "processor assists with Art 34"),
    ("GP-09", "supports", "RA-01", ["28(3)(f)"], "processor assists with Art 35"),
    ("GP-09", "supports", "RA-05", ["28(3)(f)"], "processor assists with Art 36"),
    ("GP-09", "supports", "SB-01", ["28(3)(f)"], "processor assists with Art 32"),
    ("GP-11", "depends_on", "SB-01", ["30(1)(g)", "30(2)(d)"], "records describe the Art 32(1) security measures"),
    ("OL-02", "supports", "GP-02", ["25(3)"], "certification may demonstrate data protection by design"),
    ("OL-02", "supports", "SB-01", ["32(3)"], "codes/certification may demonstrate security compliance"),
    ("RA-06", "depends_on", "CS-07", ["37(1)(c)"], "DPO trigger: large-scale special-category data"),
    ("RA-06", "depends_on", "CS-09", ["37(1)(c)"], "DPO trigger: large-scale criminal data"),
    ("RA-06", "depends_on", "RA-08", ["37(5)"], "DPO designated on ability to fulfil the Art 39 tasks"),
    ("RA-08", "supports", "RA-03", ["39(1)(c)"], "DPO advises on the DPIA"),
    ("RA-08", "supports", "RA-05", ["39(1)(e)"], "DPO is contact point for prior consultation"),
    ("XT-04", "depends_on", "DR-16", ["47(2)(e)"], "BCRs must give the Art 22 right"),
    ("XT-04", "depends_on", "OL-03", ["47(2)(e)"], "BCRs must give complaint and judicial remedies"),
    ("XT-04", "depends_on", "CM-07", ["47(2)(g)"], "BCRs: information under Art 13"),
    ("XT-04", "depends_on", "CM-09", ["47(2)(g)"], "BCRs: information under Art 14"),
    ("XT-04", "depends_on", "RA-06", ["47(2)(h)"], "BCRs: tasks of the DPO"),
    ("PF-02", "depends_on", "OL-05", ["5(1)(b)"], "research/statistics compatibility relies on Art 89(1) safeguards"),
    ("PF-05", "depends_on", "OL-05", ["5(1)(e)"], "longer storage for research relies on Art 89(1) safeguards"),
    ("CS-07", "depends_on", "OL-05", ["9(2)(j)"], "research exception relies on Art 89(1)"),
    ("PF-09", "depends_on", "OL-01", ["6(4)"], "Union/MS law safeguarding Art 23(1) objectives can authorise further processing"),
    *[("OL-01", "overrides", r, ["23(1)"], "only to the extent a legislative measure restricts it")
      for r in ("CM-07", "CM-09", "DR-03", "DR-10", "PF-01", "PF-02", "PF-03", "PF-04", "PF-05", "PF-06")],
    *[("OL-05", "overrides", r, ["89(2)", "89(3)"], "only where Union/MS law provides derogations")
      for r in ("DR-03", "DR-07", "DR-10", "DR-11")],
    *[("OL-03", "gives_effect_to", rt, ["77", "78", "79", "80"], None)
      for rt in ("RT.complaint", "RT.remedy_against_sa", "RT.remedy_against_controller", "RT.representation")],
    ("OL-04", "gives_effect_to", "RT.compensation", ["82"], None),
]
for src, etype, dst, arts, note in LEGAL_LINKS:
    add_edge(src, etype, dst, articles=arts, **({"note": note} if note else {}), source_kind="text_cross_reference")

# ── validation ───────────────────────────────────────────────────────────
problems = []
for (s, t, d) in edges:
    for end in (s, d):
        if end not in nodes:
            problems.append(f"missing endpoint {end} in {s} -{t}-> {d}")
ungrounded = [n["id"] for n in nodes.values()
              if n.get("layer") in ("legal", "rule") and n["type"] not in ("deadline",)
              and not any(k[0] == n["id"] and k[1] in ("grounded_in", "defined_in") for k in edges)
              and n["type"] != "rule"]
rules_ungrounded = [r["id"] for r in V1["rules"] if not any(k[0] == r["id"] and k[1] == "grounded_in" for k in edges)]
degree = Counter()
for (s, _, d) in edges:
    degree[s] += 1
    degree[d] += 1
isolated = [n for n in nodes if degree[n] == 0]

out = {
    "meta": {
        "name": "GDPR ontology", "version": 2,
        "source": "Regulation (EU) 2016/679 — domains/gdpr/policy.md; rule units from rule_inventory.md",
        "groups": V1["meta"]["groups"],
        "layers": {
            "document": "chapters, sections and articles of the regulation, and the cross-references the text makes",
            "legal": "Article 4 defined terms, actors, Article 5 principles, Article 6(1) lawful bases, data-subject rights",
            "rule": "the 90 rule units, the facts (conditions) that trigger or exempt them, and their deadlines",
            "operational": "agent actions and operational roles (used to design the benchmark environment)",
        },
    },
    "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
    "edges": sorted(edges.values(), key=lambda e: (e["type"], e["source"], e["target"])),
    "open_questions": V1["open_questions"],
}
(HERE / "gdpr_ontology.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print("nodes by type:", dict(Counter(n["type"] for n in nodes.values())))
print("edges by type:", dict(Counter(k[1] for k in edges)))
print(f"total nodes {len(nodes)}, edges {len(edges)}")
print(f"problems: {len(problems)} {problems[:10]}")
print(f"legal/fact nodes without an article: {len(ungrounded)} {ungrounded[:20]}")
print(f"rules without an article edge: {rules_ungrounded}")
print(f"isolated nodes: {len(isolated)} {isolated[:20]}")
