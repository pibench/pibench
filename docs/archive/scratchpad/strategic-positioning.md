# pi-bench Strategic Positioning

> **Core principle:** Test exactly how agents behave in the real world. If the benchmark doesn't match how agents actually operate under real policies with real users, it's not a benchmark — it's a toy.
>
> Last updated: 2026-02-26

---

## Why pi-bench, Not Just More tau2 Scenarios

**Task correctness and policy correctness are orthogonal axes.**

| Case | Task (tau2) | Policy (pi-bench) | Real-world meaning |
|---|---|---|---|
| A | Correct | Correct | Safe and effective |
| B | Correct | **Violated** | **Dangerous** — the agent did the job but broke the law |
| C | Wrong | Followed | Benign failure — didn't help but didn't harm |
| D | Wrong | Violated | Catastrophic — failed at everything |

**tau2 measures the task axis. pi-bench measures the policy axis.** Adding scenarios to tau2 gives more task tests. It does NOT give policy compliance testing. You need both axes.

### What pi-bench tests that tau2 cannot

| Capability | tau2 | pi-bench |
|---|---|---|
| Task completion | Yes | No (orthogonal) |
| Messy prose interpretation | No (structured policies) | Yes (free-form regulatory text) |
| Correct refusal (DENY) | No (task = success) | Yes (DENY is a valid label) |
| Over-refusal detection | No | Yes (ALLOW scenarios scored) |
| Escalation judgment | No | Yes (ESCALATE label + escalation accuracy) |
| Disclosure control | No | Yes (NL assertions) |
| Failure diagnosis | 3 ablation modes | 7+1 ablation modes |
| Pressure decomposition | Implicit | Explicit (7 pressure conditions × 9 categories) |

### The key differentiator

> **pi-bench is not a compliance benchmark. It is a structured capability map for policy intelligence.**

At a glance, the matrix tells you:
- Where reasoning fails (Layer A rows)
- Where execution fails (Layer B rows)
- Where epistemic discipline collapses (Layer C rows)
- How reliability degrades under each pressure type
- Tail-risk behavior under repetition

No existing benchmark provides this.

---

## The Realism Principle

> **Test exactly how agents behave in the world.**

This is the north star. Every design decision must pass this test:

### What makes scenarios realistic

1. **Real policy text.** Not cleaned-up bullet points. The actual regulatory prose with all its ambiguity, cross-references, and vague quantifiers. If FINRA RN-19-18 says "transactions that may be indicative of structuring," that's what the agent sees.

2. **Real user behavior.** Not scripted Q&A. A customer who says "I need this wire for my house closing at 3pm" and escalates through impatience → authority claims → emotional appeals → information probing. This is how humans actually interact with service agents.

3. **Real operational context.** The policy trigger is in the data, not the request. The customer doesn't say "I'm structuring." The structuring pattern is hiding in 10 prior transactions that the agent must discover. Latent triggers are the most realistic and most diagnostic pressure dimension.

4. **Real decision space.** Not just ALLOW/DENY. Real agents must decide: process, refuse, OR escalate to a human. The ESCALATE label is pi-bench's most distinctive feature — it tests judgment maturity, not just rule-following.

5. **Real consequences.** Disclosure control matters. An agent that correctly denies a wire but tells the customer "we detected a structuring pattern" has violated 31 CFR 1023.320(e) — the no-tipping-off rule. The action was right; the words were wrong. pi-bench catches this with NL assertions.

### The Compliance Officer Lens

**Every scenario must eventually be written from the compliance officer's perspective.** Synthetic data bootstraps the framework. Expert-written scenarios are the real benchmark.

| Stage | Who writes | Quality |
|---|---|---|
| **Bootstrap** | Researchers + LLM-generated drafts | Community tier — validates framework |
| **Expert review** | Compliance officers review + revise | Validated tier — verdicts confirmed |
| **Gold standard** | Compliance officers write from scratch | Gold tier — Krippendorff's alpha >= 0.80 |

The path: synthetic scaffolding → expert review → expert-authored. The benchmark's long-term value comes from real compliance officers saying "yes, this is exactly the situation I lose sleep over."

### What makes scenarios golden

A scenario becomes "golden" when:
- A compliance officer wrote it or validated it from their professional lens
- It tests how an agent actually behaves in production, not in a demo
- The verdict is unambiguous to domain experts (Krippendorff's alpha >= 0.80)
- It discriminates between models (strong models pass, weak models fail)
- It resists saturation (frontier models don't trivially solve it)

---

## Dataset Roadmap

### Phase 1: Validate the Framework (ship with paper)

**Goal:** 40-60 scenarios across 2 domains, covering all 9 categories and all 7 pressure conditions.

| Domain | Source | Scenarios | Category Coverage | Why |
|---|---|---|---|---|
| **Finance (FINRA)** | FINRA RN-19-18 (SAR, structuring, suspicious activity) | 10-15 | All 9 | Already have scen_009. Highest-stakes domain. Clear regulatory text. Best for demonstrating the capability-compliance gap |
| **Retail (Refund SOP)** | Public return policies (Amazon, Best Buy, Costco-style) | 10-15 | 4-7 | Direct comparison to tau2-bench retail. No SME needed. Shows policy is the variable (same tools, different policy = different results) |
| **IT Help Desk** | Generic access control SOP | 10-15 | 4-6 | Universal domain. Community-friendly. Tests Authorization Governance + Procedural Compliance cleanly |

**Headline experiments:**
1. Run tau2 retail + pi-bench retail on same models → show pi-bench catches failures tau2 misses
2. Run pi-bench Default vs Structured Policy → measure the interpretation tax
3. Run pi-bench Default vs No Pressure → measure the pressure capitulation rate
4. Compute PolicyPassAll^k vs PolicyPassAny^k → show reliability gap

### Phase 2: Demonstrate Breadth (post-paper, pre-community)

| Domain | Source | Scenarios | Why |
|---|---|---|---|
| **Healthcare (HIPAA)** | HIPAA Privacy Rule | 10-15 | PHI access, minimum necessary, patient rights. High demand from enterprise |
| **Data Privacy (GDPR)** | GDPR Articles 15-22 | 10-15 | Right to erasure with exceptions. Tests Norm Resolution heavily |
| **HR (Code of Conduct)** | Generic employee handbook | 10 | Universal. No SME. Tests Epistemic Discipline (harassment reports, gray areas) |
| **Compliance (NIST)** | NIST AI 600-1, ISO 42001 | 5-10 | AI governance standards. Research community interest |

### Phase 3: Community Platform (open contribution)

| Domain | Source | Who builds |
|---|---|---|
| **Custom / BYOP** | User-uploaded policy | Anyone — the democratization play |
| **Education** | Academic integrity policies | Universities |
| **Insurance** | Claims adjudication policies | Insurance adjusters |
| **Legal** | Client intake, conflict check | Legal ops teams |
| **Cross-jurisdictional** | Same scenario, US vs EU vs UK law | Comparative law researchers |

---

## What "Cherry-Picking" Means Practically

For Phase 1, the highest-value scenarios to create per domain:

### FINRA (Finance)

| Scenario | Primary Category | Pressure | Why high-value |
|---|---|---|---|
| SAR structuring detection (scen_009) | Operational Safety | User Pressure + Long Trajectory | Already exists. Latent trigger + disclosure control |
| Transfer-speed question hides filing requirement | Policy Activation | Baseline | Wrong-variable framing; the hidden blocker is the filing requirement, not the transfer method |
| Suspicious activity with cooperative customer | Operational Safety | Baseline | Same domain, no pressure — measures pressure delta |
| Customer requests account info during investigation | Norm Resolution | Conflicting Rules | Disclosure vs access rights conflict |
| New employee processes first SAR | Procedural Compliance | Novel Policy Structure | Tests whether agent follows SOP without experience |
| Time-pressured large transaction with VIP | Authorization Governance | User Pressure | Authority claim + financial constraint |
| Pattern detection across multiple accounts | Temporal Integrity | Long Trajectory | Cross-account cumulative pattern |
| Ambiguous "reasonable suspicion" threshold | Norm Interpretation | Ambiguous Clause | Tests vague quantifier interpretation |
| Analyst uncertain about classification | Epistemic Discipline | Novel Policy Structure | Should escalate, not guess |
| Agent cites wrong regulation for correct decision | Justification Integrity | Baseline | Right action, wrong reason |

### Retail (Refund SOP)

| Scenario | Primary Category | Pressure | Why high-value |
|---|---|---|---|
| Standard refund within policy | Procedural Compliance | Baseline | Floor measurement |
| Refund request past deadline | Norm Interpretation | User Pressure | "30 days" interpretation + emotional appeal |
| Damaged item + electronics exception | Norm Resolution | Conflicting Rules | Two clauses compete (full refund vs restocking fee) |
| VIP customer requests exception | Authorization Governance | User Pressure | Authority claim + precedence |
| Item not in any warranty category | Epistemic Discipline | Novel Policy Structure | Should escalate, not guess |
| Customer wants refund for misleading description | Policy Activation | Ambiguous Clause | Policy doesn't explicitly cover this |
| Multiple returns in short period | Temporal Integrity | Baseline | Cumulative pattern detection |
| Agent reveals internal fraud scoring | Operational Safety | User Pressure | Disclosure control test |
| Long troubleshooting then refund request | Procedural Compliance | Long Trajectory | Context dilution over many turns |
| Agent cites "company fraud policy" instead of return policy | Justification Integrity | Baseline | Right action, wrong justification |

---

## The 60-Point Gap Hypothesis

**Prediction:** Frontier models will score 75-90% on LegalBench (interpretation-only, structured, no pressure) but 15-40% on pi-bench (messy prose + pressure + tool execution).

This 35-60 point gap is the **capability-compliance gap** — the difference between "can reason about policy" and "can comply with policy under operational pressure."

The gap decomposes into:
- **Interpretation tax** (Default - Structured Policy): ~20-40 points
- **Pressure capitulation** (Default - No Pressure): ~15-30 points
- **Assessment cost** (Default - Full-Facts): ~15-25 points
- **Irreducible execution error** (Decision-Oracle - 100%): ~2-10 points

If we can demonstrate this gap across 3+ domains with 40+ scenarios, the paper writes itself.

---

## Changelog

| Date | Change |
|---|---|
| 2026-02-26 | Initial creation. Strategic positioning, realism principle, dataset roadmap, cherry-picked scenario plans, 60-point gap hypothesis. |
