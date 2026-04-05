# Research Gap Analysis: What Existing Work Covers vs. What pi-bench Fixes

> **Purpose:** This document maps the 44 research papers to pi-bench's design, identifies what they do well, what they miss, and how pi-bench fills the gaps. This feeds directly into the "Related Work" and "Motivation" sections of the pi-bench research paper.
>
> Last updated: 2026-02-25

---

## The Core Claim

**No existing benchmark tests all three layers together:**

1. **Interpretation** — parsing messy, ambiguous policy prose
2. **Decision** — applying rules to novel situations (ALLOW / DENY / ESCALATE)
3. **Execution under pressure** — maintaining compliance when users push back, deadlines loom, or KPIs conflict

Existing work tests these in isolation. pi-bench tests them as a single integrated pipeline — because that's how real-world policy compliance works.

---

## What Existing Papers Cover (and Where They Stop)

### Layer 1: Interpretation — Covered, but in isolation

| What they do well | What they miss | pi-bench fills the gap |
|---|---|---|
| LegalBench (#1): 162 tasks across 6 reasoning types | Tasks are standalone Q&A — no tool-use, no execution, no user pressure | pi-bench embeds interpretation inside a live agent interaction |
| CUAD (#3), MAUD (#4), ContractNLI (#5): Contract clause extraction/NLI | Focus on extractive QA over clean documents, not messy prose | pi-bench uses deliberately ambiguous, cross-referencing policy text |
| LexGLUE (#2): Legal NLU benchmark | Classification tasks only — no reasoning chains, no actions | pi-bench requires interpretation → decision → action chain |
| BLT (#8): Basic legal text lookup fails | Identified the problem but no operational benchmark | pi-bench's deterministic checks catch these failures in context |
| RegNLP (#14): Regulatory QA pipeline | Retrieval-focused — doesn't test what the agent *does* with the answer | pi-bench requires the agent to act on its interpretation |
| Not Ready for the Bench (#7): Interpretation instability | Proves models give different answers to same question in different phrasings | pi-bench's multi-trial pass^k metric directly captures instability |

**Key gap:** All interpretation benchmarks test comprehension. None test whether the agent's interpretation leads to the correct *action*.

### Layer 2: Decision — Partially covered, missing real policies

| What they do well | What they miss | pi-bench fills the gap |
|---|---|---|
| tau-bench (#23): Policy compliance in retail/airline domains | Only 2 domains with fixed policies; no ALLOW/DENY/ESCALATE labels; no over-refusal metric | pi-bench: policy is the variable (swappable), 3-label verdict, over-refusal is a first-class metric |
| RuleArena (#24): Rule-guided reasoning over real regulations | Rules are provided in structured form; no agent execution | pi-bench gives messy prose, not structured rules — interpretation is part of the test |
| IFEval (#18): Verifiable instruction-following | Tests format constraints (word count, keywords), not substantive policy reasoning | pi-bench tests substantive regulatory decisions with real-world consequences |
| Constitutional AI (#17): Training with explicit principles | Training method, not evaluation benchmark | pi-bench evaluates whether any model (regardless of training) complies |
| SORRY-Bench (#25): Safety refusal across categories | Binary safe/unsafe; no concept of "correctly allowing" or escalation | pi-bench's 3-label system (ALLOW/DENY/ESCALATE) captures the full decision space |
| LogiSafetyBench (#30): Formal logic for compliance | Converts regulations to LTL — but regulations arrive as prose, not logic | pi-bench starts from prose — the conversion is the agent's job |

**Key gap:** Existing decision benchmarks either (a) provide structured rules (not messy policy), or (b) test binary safe/unsafe (not the full ALLOW/DENY/ESCALATE space), or (c) use fixed policies (not swappable as the experimental variable).

### Layer 3: Execution Under Pressure — Covered in adversarial settings, not in operational ones

| What they do well | What they miss | pi-bench fills the gap |
|---|---|---|
| ODCV-Bench (#43): Agents cheat under KPI pressure | Tests outcome-driven violations but in scripted scenarios, not interactive conversations | pi-bench uses live user simulators who apply realistic social pressure |
| Sleeper Agents (#21): Deceptive behavior persists | Training/safety concern, not a benchmark for policy compliance | pi-bench's multi-trial pass^k catches inconsistent compliance across runs |
| Instruction Hierarchy (#34) + Control Illusion (#35): System prompt adherence | Tests prompt-level hierarchy, not domain-specific policy adherence | pi-bench tests whether policy documents (not just system prompts) govern behavior |
| AgentHarm (#26): Agents execute harmful tool sequences | Adversarial/malicious tasks, not legitimate operational pressure | pi-bench tests legitimate scenarios where pressure comes from time, social dynamics, conflicting priorities |
| Sycophancy (#42): Models capitulate to confident users | Documented as a phenomenon, no benchmark tests it against specific policies | pi-bench's pressure scripts directly test sycophancy-induced policy violations |
| WebArena (#39), SWE-bench (#40): Real-world task failure | Test task completion, not policy compliance during tasks | pi-bench tests whether the agent respects rules *while* trying to complete the task |

**Key gap:** Existing execution benchmarks test adversarial attacks (jailbreaks) or task completion. None test whether agents maintain policy compliance under *operational* pressure — the kind that comes from time-constrained customers, conflicting business objectives, and ambiguous real-world situations.

---

## The 8 Critical Gaps pi-bench Fills

| Gap | Existing state | What pi-bench does |
|---|---|---|
| **1. Policy as the variable** | All benchmarks fix the policy per domain | pi-bench swaps policies on the same domain — GDPR vs HIPAA vs custom SOP on the same toolset |
| **2. DENY as success** | No benchmark scores "correctly refusing" as success | pi-bench's DENY label means the correct answer is to block the request |
| **3. Over-refusal measurement** | No benchmark penalizes excessive caution | pi-bench's over-refusal metric catches agents that block legitimate requests |
| **4. Messy policy text** | Structured rules, bullet points, or no policy at all | pi-bench uses real-world regulatory prose with ambiguity, cross-references, vague quantifiers |
| **5. Interpretation → Action chain** | Interpretation benchmarks stop at comprehension; action benchmarks assume understanding | pi-bench tests the full chain: read policy → decide → execute correctly |
| **6. Operational (not adversarial) pressure** | Jailbreaks, prompt injection, malicious prompts | pi-bench applies realistic pressure: deadlines, confident users, conflicting priorities |
| **7. Deterministic evaluation** | Many benchmarks use LLM-as-judge for compliance | pi-bench uses tool_called, state_field, message_not_contains — zero LLM judgment |
| **8. Ablation-based failure diagnosis** | Single score per model | pi-bench's 7 ablation modes pinpoint *where* the failure happens (interpretation? decision? execution?) |

---

## How pi-bench's Taxonomy Maps to the Research Landscape

### Policy Source Types (Level 1 taxonomy)

| Policy Source | Research paper coverage | pi-bench domains needed |
|---|---|---|
| **Regulatory (GDPR, HIPAA, FINRA, NIST)** | LegalBench, RegNLP, Legal Compliance papers — mostly interpretation-only | Finance domain (FINRA, SAR, structuring); Health domain (HIPAA, PHI); Data domain (GDPR, deletion, access rights) |
| **Standards (PCI-DSS, ISO 42001, SOX)** | Survey papers mention but no benchmarks test | Compliance domain with standards-derived policies |
| **Organizational SOPs** | tau-bench (retail/airline policies) — closest match | Retail, telecom, airline domains with swappable SOP policies |
| **Codes of Conduct** | ODCV-Bench touches this; no dedicated benchmark | HR/employee domain with code of conduct policies |
| **Enterprise User-Defined Policies** | No coverage at all | Custom policy domain — user uploads their own policy doc |
| **Contractual (Terms of Service, NDAs)** | CUAD, ContractNLI, MAUD — interpretation only | Contract review domain with tool-based actions |

### Policy Intelligence Categories (9 categories in 3 layers)

| Category | Which papers test it | How pi-bench tests it |
|---|---|---|
| **1. Policy Activation** | Sleeper Agents (latent triggers), AgentHarm (context-dependent harm) | Latent trigger scenarios; scope detection; `tool_called` for relevant lookups |
| **2. Norm Interpretation** | LegalBench (text reasoning), BLT (legal text), RuleArena (structured rules) | Messy prose policy text with ambiguity; `decision_equals` checks |
| **3. Norm Resolution** | Control Illusion (instruction hierarchy) — no policy-level conflict testing | Conflicting clauses; multi-policy stacks; ESCALATE when ambiguous |
| **4. Authorization Governance** | IFEval (weak), SORRY-Bench (refusal) | Identity verification; `tool_before_tool(verify → action)` |
| **5. Temporal Integrity** | No benchmark tests this systematically | Cumulative patterns; deadlines; `state_field` + `tool_called(query_activity)` |
| **6. Procedural Compliance** | SOPBench (SOP following), tau-bench (implicit) | `tool_before_tool` ordering; step omission detection |
| **7. Operational Safety** | AgentHarm (adversarial), Agent-SafetyBench | `tool_not_called`; `nl_assertion_forbidden_disclosure`; `message_not_contains` |
| **8. Epistemic Discipline** | Sycophancy Survey (capitulation phenomenon) — no policy-specific benchmark | ESCALATE label; `decision_equals(ESCALATE)`; over-refusal rate |
| **9. Justification Integrity** | No benchmark tests this | Clause citation accuracy; reason-action alignment; trace consistency |

### Pressure Conditions (7 matrix columns)

| Pressure Condition | Which papers demonstrate it | How pi-bench applies it |
|---|---|---|
| **Baseline** | tau-bench (cooperative users) | Straightforward policy application, no complication |
| **Ambiguous Clause** | Not Ready for the Bench (interpretation instability) | Policy text with deliberately ambiguous language |
| **Conflicting Rules** | Control Illusion (instruction hierarchy) | Two clauses produce competing obligations |
| **User Pressure / Coercion** | ODCV-Bench (KPI), Sycophancy Survey, Crescendo | User simulator with authority claims, emotional appeals, deadline pressure |
| **Novel Policy Structure** | SORRY-Bench (over/under-refusal boundary) | Situation not covered by any clause |
| **Long Trajectory / Multi-Turn** | Multi-turn degradation study (200K+ conversations) | 5+ tool steps before decision; context dilution |
| **Policy Update / Drift** | Sleeper Agents (temporal triggers) | Policy changed between training and evaluation |

---

## Positioning for the Research Paper

### What we say in Related Work

> "Existing benchmarks measure legal reasoning (LegalBench), agent safety (AgentHarm, Agent-SafetyBench), instruction following (IFEval), or task completion (tau-bench, WebArena). However, no benchmark tests the integrated pipeline: interpreting messy policy text → making the correct compliance decision → executing that decision correctly under realistic operational pressure. pi-bench addresses this gap with a three-layer evaluation framework — Normative Reasoning, Governance Execution, and Epistemic & Integrity Control — comprising 9 policy intelligence categories, a deterministic evaluation methodology, and 7 pressure conditions drawn from real-world regulatory and enterprise contexts."

### What we validate empirically

We should run:

1. **LegalBench interpretation tasks** on frontier models → show high scores (75%+)
2. **pi-bench scenarios** on the same models → show the gap (expecting 15-40%)
3. **Ablation modes** → show *where* the performance drops (interpretation vs decision vs execution)
4. **tau-bench comparison** → show pi-bench captures failures tau-bench misses (policy violations that tau-bench scores as task success)

This validates the "60-point capability-compliance gap" hypothesis.

### What we contribute beyond existing work

1. **Benchmark:** 162+ scenarios across GDPR, FINRA, HIPAA, codes of conduct, custom SOPs
2. **Taxonomy:** 9 policy intelligence categories in 3 layers (Normative Reasoning, Governance Execution, Epistemic & Integrity Control) × 7 pressure conditions — mechanism-first, not domain-first
3. **Evaluation methodology:** Deterministic, no LLM-as-judge, with 7 ablation modes for failure diagnosis
4. **Open platform:** Community-contributable scenarios — anyone can add their domain (IT help desk, HR, legal intake, insurance claims, etc.)
5. **Metrics:** Over-refusal, under-refusal, escalation accuracy — the vocabulary enterprises need

---

## Scenario Design Priorities (What to Build Next)

Based on the gap analysis, the highest-value scenarios to build are:

### Tier 1: Validate the core claim (run these first)

| Domain | Policy Source | Mechanism Tested | Pressure Type | Why |
|---|---|---|---|---|
| Finance | FINRA RN-19-18 | Prohibition + Escalation | Time + Social | Already have scen_009; validates full pipeline |
| Healthcare | HIPAA Privacy Rule | Data protection + Scope | Authority | PHI access scenarios — high stakes, clear rules, real-world demand |
| Data/Privacy | GDPR Art. 17 | Obligation + Exception | Conflicting objectives | Right to erasure with exceptions — tests exception handling |
| Enterprise | Refund SOP | Permission + Threshold | Social pressure | Simple enough to build without SME; maps to tau-bench retail for comparison |

### Tier 2: Demonstrate breadth (build for taxonomy coverage)

| Domain | Policy Source | Mechanism Tested | Pressure Type | Why |
|---|---|---|---|---|
| HR | Code of Conduct | Prohibition + Escalation | Latent trigger | Employee misconduct reporting — codes of conduct are universal |
| IT Help Desk | Access Control SOP | Permission + Scope | Authority | Universal domain; easy for community to contribute |
| Insurance | Claims Policy | Obligation + Precedence | Ambiguity | Complex multi-clause policies with exceptions |
| Compliance | PCI-DSS 4.0 | Permission + Obligation | Information overload | Technical compliance with verbose standards |

### Tier 3: Community-friendly (designed for contributions)

| Domain | Policy Source | Mechanism Tested | Why community can build |
|---|---|---|---|
| Custom | User-uploaded policy | Any | Template scenario format; bring-your-own-policy |
| Education | Academic integrity policy | Prohibition + Escalation | Every university has one; no SME needed |
| Retail (extended) | Returns + warranty SOP | Permission + Temporal | Extends tau-bench comparison |

---

## Changelog

| Date | Change |
|---|---|
| 2026-02-25 | Initial creation. Maps 44 papers to pi-bench gaps. Scenario priorities identified. |
