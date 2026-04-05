# Second Reviewer Critique: Merged Analysis

> Section-by-section comparison of second independent review against
> our existing analysis. Records where we agree, what's genuinely new,
> and the merged position.

## Section 1: tau2-bench Mindset Reconstruction

The reviewer's reconstruction of how the tau2 team arrived at each
decision is nearly identical to our first-principles analysis. Same
pattern: "observed a gap, asked what's the simplest structural change
that closes it." The reviewer phrases the design test as "what
confounders let a model score well without having the capability" —
arguably crisper than our "what's the gap with reality."

**Verdict:** Full agreement. No new substance. Reviewer's phrasing
is tighter.

---

## Section 2: Four Policy Failure Modes (A/B/C/D)

The reviewer identifies four failure categories:

| Category | Description |
|---|---|
| A. Interpretation | Wrong reading of policy clauses |
| B. Situation Assessment | Fails to gather material facts before deciding |
| C. Action Mapping | Correct decision but wrong execution (says DENY, calls forbidden tool) |
| D. Pressure Robustness | Caves under social engineering or authority claims |

### Comparison to our three-layer taxonomy

| Reviewer | Our Taxonomy | Same? |
|---|---|---|
| Interpretation (A) | Layer 1: Mind | Yes |
| Situation Assessment (B) | — | **NEW** |
| Action Mapping (C) | Layer 3: Hands (text-action misalignment) | Yes |
| Pressure Robustness (D) | Pressure conditions + Layer 1 | Yes |

### The genuine addition: Situation Assessment (B)

We had lumped "doesn't ask for missing facts" and "accepts claims
without verification" into interpretation or pressure. The reviewer
is right that this is a **distinct skill**: the agent must recognize
what facts are *material* under the policy, then actively gather them
before deciding.

**Concrete example:** HIPAA policy says PHI can be disclosed to a
treating physician. The agent needs to *verify* that the requester
actually is a treating physician — not just take their word for it.
An agent that interprets the policy perfectly but doesn't verify the
claim has failed at assessment, not interpretation.

**Why this matters for ablations:** Our Structured Policy ablation
removes interpretation difficulty but wouldn't reveal assessment
failures because the facts would still be incomplete. We need a
separate ablation that removes assessment difficulty (Full-facts)
to isolate interpretation from fact-gathering.

**Verdict:** Three of four map to existing analysis. Situation
Assessment as a first-class category is genuinely new and correct.
Adopted.

---

## Section 3: Ablation Suite Comparison

### Three-way alignment

| Reviewer 2 | Our Modes | Reviewer 1 (Doc 5) | Status |
|---|---|---|---|
| Default | Default | Default | Same across all three |
| Clean-policy | Structured Policy | Structured Policy | Same |
| Evidence-oracle | — | Evidence-oracle (proposed) | **Two reviewers converge; we deferred to v2** |
| Decision-oracle | Oracle Verdict | Oracle Verdict | Same (renamed) |
| Full-facts | — (collapsed into No Pressure) | Full-facts (proposed) | **Two reviewers converge; we missed** |
| No-pressure | No Pressure | No Pressure | Same |
| Short/Long trajectory | Mentioned informally | — | **New as formal mode** |
| — | Harness-Isolated | — | **Only us** |
| — | Tool-Isolated | — | **Only us** |
| — | — | Hard-Gate / Audit-Only | **Only Doc 5** |

### Key updates

**Evidence-oracle moves to v1.** Two independent reviewers both
proposed it. The idea: give the agent the 2-5 relevant policy
passages so it doesn't have to *find* them in a long document, only
*apply* them. Isolates retrieval/navigation from interpretation. When
two independent reviewers converge on the same ablation we didn't
think of, we should update.

**Full-facts is NOT the same as No Pressure.** This was our mistake.

- No Pressure removes adversarial user behavior but keeps facts
  hidden — agent still needs to ask for information
- Full-facts reveals all policy-relevant facts upfront but keeps messy
  policy and potentially keeps pressure

These are *orthogonal ablations isolating different things*:
- No Pressure isolates pressure resistance
- Full-facts isolates fact-gathering/assessment

Once you recognize Situation Assessment (B) as a separate failure
mode, you need an ablation that removes it independently. Full-facts
is that ablation.

**Short/Long trajectory** is formalized as a scenario property
(trajectory_length: short/medium/long) rather than a separate
ablation mode, since it's a parameter of the scenario, not a
modification to what the agent sees.

**Harness-Isolated and Tool-Isolated move to v2.** They test the
harness/system layer, not the model layer. They require different
infrastructure (oracle model stubs, multiple harness implementations).
Still critical for Vijil's use case but not v1.

**Hard-Gate / Audit-Only stays in v1** (from Doc 5). This reviewer
doesn't mention it, but it's the cleanest mechanism for making
"attempt" a precise trace event.

### Merged v1 ablation suite (final)

| # | Mode | What it isolates |
|---|---|---|
| 1 | **Default** | Full difficulty: messy policy, partial facts, adversarial pressure |
| 2 | **Structured Policy** | Interpretation: replace messy prose with clean rules |
| 3 | **Full-facts** | Assessment: reveal all material facts, keep messy policy |
| 4 | **Evidence-oracle** | Retrieval: supply relevant excerpts, keep messy policy |
| 5 | **Decision-oracle** | Execution: provide correct decision, must still execute |
| 6 | **No Pressure** | Pressure: replace adversarial user with cooperative |
| 7 | **Audit-Only / Hard-Gate** | Attempt observation vs enforcement (cross-cuts all modes) |

Six diagnostic modes + one execution-mode pair. Each isolates a
different axis. The deltas between them produce the full failure
decomposition.

### The headline experiment

**Full-facts → Default delta is the core diagnostic experiment
pi-bench should be built around.**

Prediction: like tau2 found 18-25% drop from No-User to Default
(coordination cost bigger than expected), pi-bench will find a
significant drop from Full-facts to Default. Agents that apply policy
correctly when given all facts will fail substantially when they need
to *figure out what to ask*. Assessment is probably the most
underestimated skill in policy compliance, just as coordination was
in task completion.

---

## Section 4: policy_decision Tool

The reviewer suggests a required `policy_decision(decision=...,
rationale_id=..., cited_sections=[...])` tool.

### Our position evolution

1. **Original (Doc 5):** Required `record_decision()` tool + JSON
   fallback with strict precedence
2. **Our pushback:** Real agents don't call `declare_verdict()`. Prefer
   inferring from existing tool patterns.
3. **Updated position:** Offer as **optional tool**. Score scenarios
   both with and without. When present, use as ground truth. When
   absent, infer from tool patterns.

The *delta* between "with explicit decision tool" and "without" is
itself an interesting measurement — tells you how much ambiguity
exists in the agent's natural behavior.

This subsumes the Decision Signal Design's dual-channel approach: the
decision tool is Channel A, inference from tool patterns is the
natural-behavior fallback, and measuring the delta between them is a
diagnostic feature.

---

## Section 5: What This Reviewer Doesn't Address

Three gaps compared to our full analysis:

### 1. The Harness Layer

Everything here is model-focused. Nothing about harness-level
failures: LangChain truncating policy from context, retry logic
re-executing blocked tools, multi-agent handoffs losing policy state.
Our failure taxonomy identified this as a critical untested gap
(Layer 2: Body). For evaluating real deployed agent systems,
harness-level testing is non-negotiable. Deferred to v2 but not
forgotten.

### 2. IRT / Psychometric Lifecycle

Neither this reviewer nor Doc 5 engages with pi-bench's item quality
tracking (difficulty beta, discrimination alpha, saturation index).
This is a major differentiator from every existing benchmark. Scenarios
that lose discriminative power get retired. The benchmark tracks its
own shelf life. The February 2026 research shows 48% of benchmarks
are already saturated. Both reviewers implicitly assume a static
scenario set.

### 3. Policy Stack Formalization

Doc 5 explicitly called out policy stack depth and precedence
complexity as a modeled dimension. This reviewer mentions "conflicting
clauses + precedence rules" but doesn't formalize it. Doc 5's version
is stronger and already in our spec.

---

## Net Update Table

| Category | Previous Position | Update | Source |
|---|---|---|---|
| Four policy failure modes | 3 layers (mind/body/hands) | Add Situation Assessment as 4th axis | Reviewer 2 |
| Evidence-oracle ablation | Deferred to v2 | Move to v1 | Both reviewers converge |
| Full-facts ablation | Collapsed into No Pressure | Separate mode | Reviewer 2 |
| Short/Long trajectory | Informal mention | Formalize as scenario property | Reviewer 2 |
| Harness-Isolated mode | In v1 | Move to v2 | Our decision, reviewer gap |
| Tool-Isolated mode | In v1 | Move to v2 | Our decision, reviewer gap |
| Hard-Gate / Audit-Only | In v1 (from Doc 5) | Keep | Not addressed by Reviewer 2 |
| policy_decision tool | Required (Doc 5) | Optional, measure delta | Our synthesis |
| IRT lifecycle | In spec | Keep | Not addressed by either reviewer |
| Policy stack | Modeled dimension (Doc 5) | Keep | Not formalized by Reviewer 2 |
| Headline experiment | Implicit | Full-facts → Default delta | Reviewer 2 |

---

## Updated Four-Axis Failure Model

| Axis | What it tests | Ablation that removes it |
|---|---|---|
| **Interpretation** | Can the agent read messy policy correctly? | Structured Policy |
| **Assessment** | Does the agent gather material facts before deciding? | Full-facts |
| **Execution** | Does the agent's action match its decision? | Decision-oracle |
| **Pressure Resistance** | Does the agent hold its position under social pressure? | No Pressure |

Plus two cross-cutting concerns:
- **Retrieval** (can the agent find the right clause?): Evidence-oracle
- **Attempt / Recovery** (what happens when blocked?): Hard-Gate / Audit-Only

---

## Related Documents

- [Decision Signal Design](decision_signal_design.md) — dual-channel
  resolution (updated: decision tool now optional, delta is diagnostic)
- [Architecture: Wrap, Don't Replace](architecture_wrap_not_replace.md)
  — component design (update needed for Full-facts mode)
- [Porting Review Response](porting_review_response.md) — Doc 5
  analysis
- [tau2→pi-bench Porting Decisions](tau2_to_pibench_porting_decisions.md)
- [Policy compliance failure taxonomy](policy_compliance_failure_taxonomy.md)
  — 3-layer model now superseded by 4-axis model
- [pi-bench spec](specs/pi-bench.md) — needs ablation suite update
