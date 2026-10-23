# GDPR ontology

A graph of Regulation (EU) 2016/679 built as the coverage map for
benchmark scenario generation. Source text: `domains/gdpr/policy.md`.
Version 3: built from the text, checked, reviewed once by Fable, fixes applied.

Browse it: `python3 -m http.server 8642 --directory domains/gdpr/ontology`,
then open http://localhost:8642/viewer/ (or start `gdpr-ontology` from
`.claude/launch.json`).

## Files

| File | What it is |
|---|---|
| `gdpr_ontology.json` | the graph: `nodes`, `edges`, `open_questions`, `meta` |
| `structure.json` | the regulation parsed from the text: chapters, sections, articles, paragraphs, points, Article 4 definitions, cross-references |
| `viewer/index.html` | interactive explorer (served locally) |
| `build_structure.py` | deterministic parser → `structure.json` |
| `build_ontology.py` | assembles the graph from `structure.json`, the merged rule fragments and the legal layer |
| `apply_review.py` | applies the review findings on top of `build_ontology.py`'s output |
| `check_coverage.py` | checks every "shall" paragraph of Arts 5-49 is covered |
| `review/fable_review.json` | the review: 64 findings with evidence and fixes |
| `review/decisions.json` | what was applied for each finding, and where the fix was changed and why |
| `merge.py`, `fragments/`, `SCHEMA.md` | the rule-layer fragments (one per article range) and how they were merged |
| `drafts/` | parked material: decision paths (ALLOW/DENY/ESCALATE) and the v1 graph |

Rebuild: `python3 build_structure.py && python3 build_ontology.py && python3 apply_review.py && python3 check_coverage.py`

## Node types (804 nodes)

| Layer | Node type | ID pattern | Count | What it is |
|---|---|---|---|---|
| document | `chapter` | `CH.III` | 11 | a chapter of the regulation |
| document | `section` | `CH.III.S3` | 15 | a section inside a chapter |
| document | `article` | `ART.17` | 99 | an article, with its paragraphs and points as text |
| legal | `concept` | `C.personal_data` | 41 | a legal concept; Article 4 terms carry their verbatim definition |
| legal | `actor` | `C.controller` | 25 | a party the GDPR assigns rights or duties to |
| legal | `principle` | `P.data_minimisation` | 7 | an Article 5 principle |
| legal | `lawful_basis` | `C.basis.contract` | 6 | an Article 6(1) ground |
| legal | `right` | `RT.erasure` | 15 | a data-subject right (Arts 7(3), 13-22, 77-80, 82) |
| rule | `rule` | `DR-04` | 91 | a rule unit: the 90 from `rule_inventory.md` plus `SC-01` (material and territorial scope, Arts 2-3) |
| rule | `condition` | `K.DR.legal_obligation_to_retain` | 377 | a fact about a situation, quoted from the text |
| rule | `deadline` | `T.72_hours` | 11 | a time limit, with its article and quote |
| operational | `action` | `A.erase` | 99 | something an agent does to comply; its articles are derived from the rules that require or forbid it |
| operational | `role` | `R.privacy_rights_operator` | 7 | an operational job (from `rule_inventory.md`) |

Rule groups: PF principles & lawful basis, CS consent & protected data, CM
transparency & requests, DR data-subject rights, GP controllers/processors &
accountability, SB security & breaches, RA DPIA & DPO, XT international
transfers, OL conditional mechanisms & overlays, SC material & territorial scope.

A condition's role is not stored on the fact itself: the same fact can trigger
one rule and be an exception to another. Each condition carries `roles`, derived
from its edges (`trigger`, `exception`, `defeater`, `factor`).

## Relationship types (2,638 edges)

| Edge | From → To | Meaning |
|---|---|---|
| `contains` | chapter/section → section/article | document structure |
| `references` | article → article | the text of one article cites another (`at` lists each citation) |
| `defined_in` | concept/actor → ART.4 | the term is defined in Article 4 |
| `grounded_in` | any non-document node → article | the node comes from this article (`at` gives paragraph/point) |
| `implements` | rule → principle | the rule operationalises the principle |
| `instance_of` | condition → lawful_basis | the fact is that lawful basis applying |
| `held_by` / `exercised_against` | right → actor | who holds the right / against whom |
| `gives_effect_to` | rule → right | the rule is how the right is honoured |
| `obligates` | rule → actor | who carries the duty (controller and/or processor) |
| `applies_to` | rule → concept/actor/right | the rule governs that concept, party or right |
| `triggered_by` | rule → condition | the rule applies when the fact holds |
| `has_exception` | rule → condition | the rule is displaced when the fact holds |
| `blocked_by` | rule → condition | the permission or route the rule offers fails when the fact holds (e.g. no enforceable rights for an Art 46 transfer) |
| `weighs` | rule → condition | a factor weighed in a balancing test (`sign`: for / against), e.g. Art 6(4) compatibility |
| `requires_action` / `forbids_action` | rule → action | complying requires / forbids this action |
| `precedes` | action → action | required order (e.g. verify identity before disclosing) |
| `due_within` | rule → deadline | time limit |
| `refines` | rule → rule | the source is a more specific part or exception of the target |
| `depends_on` | rule → rule | the source can only be applied after the target is checked (no cycles) |
| `overrides` | rule → rule | the source takes precedence when both apply |
| `tension_with` | rule ↔ rule | the two pull in opposite directions (stored once per pair) |
| `supports` | rule → rule | the source duty exists to help satisfy the target (processor assistance, DPO tasks, certification as evidence) |
| `performed_by` | action → role | which operational role normally performs the action |

Optional fields on edges:

| Field | On | Meaning |
|---|---|---|
| `qualifies` | `has_exception` | the trigger(s) this exception defeats (e.g. "subject opposes erasure" only defeats the unlawful-processing ground) |
| `conjunct_with` | trigger / exception edges | facts that must also hold; `NOT <id>` means that fact must be false |
| `conjunct_with_any` | trigger edges | at least one of these must also hold |
| `when` | `requires_action` / `forbids_action` | the action is required only in this situation |
| `articles`, `at`, `note` | any | provenance and explanation |

Nodes may carry `recitals` (recital numbers relied on), `overlay: true` (depends
on Union or Member State law the scenario must supply) and `aliases` (ids merged
into this node).

## How it was built and checked

1. `build_structure.py` parses the regulation: 11 chapters, 15 sections, 99
   articles, 372 paragraphs, 378 points, 26 definitions, 309 article-to-article
   references.
2. Five agents modelled one article range each against `SCHEMA.md`; `merge.py`
   joined them, merged duplicate facts and validated every reference. All
   quotes are verbatim.
3. `build_ontology.py` adds the legal layer and the rule-layer links that the
   text's own cross-references require.
4. Own checks: every legal and rule node anchored to an article; no isolated
   nodes; `check_coverage.py` finds 145 of 149 agent-relevant "shall"
   paragraphs in Arts 5-49 covered (the other 4 are a savings clause, optional
   icons, and two institutional duties).
5. One review pass by Fable (64 findings: 2 critical, 18 major, 44 minor), all
   applied by `apply_review.py`; 8 with a changed fix, each explained in
   `review/decisions.json`. Main corrections: permission-defeating facts moved
   to `blocked_by`; processor duties added to 18 rules; Art 23 and Art 89
   override maps corrected; scope rule SC-01 added; duplicate exceptions and 14
   duplicate facts consolidated; joint and alternative conditions made explicit;
   no `depends_on` cycles; every condition attached to a rule.

`rule_inventory.md` lists Arts 8-10 among external-law overlays; in the graph
these rules are core defaults and only their law-dependent exceptions carry
`overlay: true`.
