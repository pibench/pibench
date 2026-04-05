# Third Reviewer Critique: Final Merged Position

> The strongest of the three reviews. Contributes top-down conceptual
> architecture (policy as control system, primitive library) and
> concrete harness failure enumeration. Combined with Doc 5's
> aggregation semantics and our harness isolation + IRT lifecycle,
> produces the final merged design.

## What This Reviewer Sees That Others Don't

### Policy as a Control System (Section 1)

The best conceptual foundation anyone has offered. Neither we nor the
previous reviewers framed it this way. We were all working bottom-up:
failure modes → ablations → matrix. This reviewer works top-down:
across every policy domain (HIPAA, FINRA, SOPs, access control, codes
of conduct), there are exactly **five primitives**:

| Primitive | What it governs |
|---|---|
| Permissions / prohibitions | What actions are allowed or forbidden |
| Obligations with pre/postconditions | What must be done, under what conditions |
| Exceptions and precedence | Which rule wins when they conflict |
| Escalation triggers | When to hand off to humans |
| Scope / definitions | What terms mean, who counts as what |

**Why this matters:** It solves coverage without listing every
regulation. You don't index by regulation — you index by *primitive*.
A HIPAA disclosure scenario and a FINRA disclosure scenario test the
same primitive (permission with conditions) in different domains. The
primitive is what the agent's reasoning must handle. The domain is
context.

This goes into the spec as the foundational taxonomy underneath the
surface types.

### Derived/Inferred Leakage (Failure Mode E)

Genuinely novel in our conversation. The policy forbids disclosing X,
but the agent infers X from allowed facts and reveals the inference.
Doc-PP demonstrated this with "Reasoning-Induced Safety Gap" — models
that correctly refuse direct queries still leak through multi-step
reasoning.

None of the ablation suites we've discussed isolate this. It requires
specific scenario design where:

- Forbidden information is *derivable* from permitted information
- The check is whether the agent reveals the derivation

**Detection approaches (deterministic):**

- `tool_called_with(summarize_record, fields=[...])` where the field
  combination allows reconstruction of forbidden value
- `state_field(disclosed_pii=true)` if environment tracks information
  conveyance
- `message_not_contains(derived_value)` for specific known derivations

This needs design work but the failure mode is real and untested by
any existing benchmark.

### No-Policy Ablation Mode

**The addition we would have missed without this review.** Run the
same scenario without any policy text. If the agent still behaves
"correctly," it's relying on training priors (HIPAA/FINRA knowledge
baked into weights), not the provided document.

The delta between No-Policy and Default measures **document-conditioning
strength**: how much the agent reads vs how much it remembers.

For enterprise customers deploying custom policies that differ from
industry defaults, this is the single most operationally relevant
measurement. An agent that ignores your custom policy and follows its
training-data version of HIPAA is dangerous even when it's "correct"
— because your policy might intentionally differ from the standard.

### Harness Component Toggles (Section 5.6)

Most concrete version of our Harness-Isolated concept. Instead of one
ablation mode with an oracle model, toggle individual harness
components:

- Memory on/off
- Router on/off
- Policy location (system prompt vs document vs memory)
- Tool schema variants

Same model, same scenarios, change one harness variable at a time.
More granular and actionable than our "oracle through harness"
approach because it identifies *which* component caused the violation.

**Refinement:** These aren't ablation modes in the same sense as the
others. They're a separate evaluation dimension — a **harness stress
test matrix** that cross-cuts the policy evaluation matrix. Run
Default mode with harness variant A, then Default mode with variant B.
The delta is attributable to that specific harness change.

### Dual-Control Analog for Policy (Section 7)

Multi-actor authorization: agent proposes, user provides evidence,
simulated approver grants/denies. Creates the same "can't solve it
alone" property that tau2 gets from dual control.

**Status: v2 scope.** Adding a third actor requires non-trivial
changes to the Orchestrator's turn management. tau2 alternates between
agent and user. Three-party protocol needs explicit turn-ordering
rules. Diagnostic value is high, implementation cost is significant.

### Concrete Harness Failure Enumeration

Much more specific than our abstract "harness introduces violations":

| Failure | Mechanism |
|---|---|
| Router error | Request misclassified, wrong policy applied |
| Argument shaping | Harness reformats tool args, losing constraints |
| Memory distortion | Summarizer drops exception clause from context |
| Guard override | Safety layer blocks compliant action |
| Context truncation | Policy text truncated from system prompt |

The "memory distortion" case is particularly sharp: a summarizer that
drops an exception clause means all subsequent reasoning is
policy-blind on that exception. The failure is entirely in the
harness, not the model.

---

## Three-Way Convergence Analysis

### What all three reviews agree on

| Topic | Status |
|---|---|
| Default + Structured Policy + Decision-oracle + No Pressure | All three converge |
| Full-facts as separate from No Pressure | Reviewers 2 + 3 converge |
| Evidence-oracle in v1 | Reviewers 2 + 3 converge |
| Deterministic trace-based evaluation, no LLM judge | Unanimous |
| Full-facts → Default delta as headline diagnostic | Unanimous |
| Actions override claims | All three |

### What each source uniquely contributes

| Source | Unique contribution |
|---|---|
| **Us** | Harness isolation methodology, IRT lifecycle, safety/liveness formalism |
| **Doc 5 (Reviewer 1)** | Ever@k/Always@k operators, Hard-Gate/Audit-Only, T=0 vs T>0 regimes |
| **Reviewer 2** | Situation Assessment as 4th failure axis, Full-facts as separate mode |
| **Reviewer 3 (this)** | Policy primitive library, No-Policy mode, derived leakage, harness toggles, dual-control analog |

### What no reviewer addresses

- IRT/psychometric lifecycle (our unique contribution)
- Saturation tracking and scenario retirement
- Benchmark self-assessment metrics

---

## Final Merged Ablation Suite (v1)

| # | Mode | Isolates | Source |
|---|---|---|---|
| 1 | **Default** | Full difficulty | All agree |
| 2 | **No-Policy** | Training prior vs document conditioning | Reviewer 3 (new) |
| 3 | **Structured Policy** | Messy prose interpretation | Us + Reviewer 2 |
| 4 | **Evidence-Oracle** | Policy retrieval/navigation | Reviewers 2 + 3 |
| 5 | **Full-Facts** | Fact-gathering/assessment | Reviewers 2 + 3 |
| 6 | **Decision-Oracle** | Execution discipline | All agree |
| 7 | **No Pressure** | Adversarial pressure resistance | Us + Reviewer 2 |
| 8 | **Audit-Only / Hard-Gate** | Attempt behavior vs recovery | Doc 5 |

Seven diagnostic modes + one execution-mode pair.

### Separate dimension: Harness Stress Test Matrix

| Toggle | Variants |
|---|---|
| Memory | On / off / degraded |
| Policy location | System prompt / document / memory |
| Router | Default / disabled |
| Tool schemas | Full / minimal / mismatched |

Cross-cuts the main policy matrix. V2 for full implementation, but
specific toggles (e.g., policy location) are cheap to test in v1.

---

## Updated Failure Model (Five Axes)

| Axis | What it tests | Ablation that removes it |
|---|---|---|
| **Interpretation** | Read messy policy correctly | Structured Policy |
| **Assessment** | Gather material facts before deciding | Full-facts |
| **Execution** | Action matches decision | Decision-oracle |
| **Pressure Resistance** | Hold position under social pressure | No Pressure |
| **Document Conditioning** | Read provided policy vs rely on training | No-Policy |

Plus cross-cutting concerns:
- **Retrieval** (find the right clause): Evidence-oracle
- **Attempt / Recovery** (behavior when blocked): Hard-Gate / Audit-Only
- **Derived leakage** (infer forbidden info from allowed data): Needs specific scenarios
- **Harness fidelity** (system-level failures): Harness stress test matrix

---

## Policy Primitive Library

Goes into the spec as the coverage model underneath surface types:

| Primitive | Example | Coverage test |
|---|---|---|
| Permission / prohibition | "Agents may not disclose PHI to non-treating staff" | DENY scenario with disclosure tool |
| Obligation with conditions | "Agent must verify identity before account changes" | ALLOW scenario requiring verification step |
| Exception with precedence | "Emergency overrides normal approval for amounts < $500" | Conflicting pressure: is this an emergency? |
| Escalation trigger | "Transfer to supervisor if customer requests manager" | ESCALATE scenario with trigger phrase |
| Scope / definition | "Premium users are defined as those with active subscription" | Assessment: agent must determine if user qualifies |

A scenario set has **primitive coverage** if every primitive appears
in at least one scenario per surface type.

---

## What Goes to v2

- Multi-actor authorization (agent + user + approver)
- Full harness stress test matrix
- Harness-Isolated and Tool-Isolated ablation modes
- Derived leakage detection (needs scenario design work)
- Evidence-Oracle and Full-Facts sub-modes (e.g., partial excerpts,
  noisy facts)

---

## Related Documents

- [Decision Signal Design](decision_signal_design.md) — dual-channel
  resolution (decision tool now optional, delta is diagnostic)
- [Architecture: Wrap, Don't Replace](architecture_wrap_not_replace.md)
  — component design
- [Second Reviewer Critique](second_reviewer_critique.md) — four-axis
  failure model, Full-facts/Evidence-oracle
- [Porting Review Response](porting_review_response.md) — Doc 5:
  Ever@k/Always@k, Hard-Gate, T=0 vs T>0
- [tau2→pi-bench Porting Decisions](tau2_to_pibench_porting_decisions.md)
- [Policy compliance failure taxonomy](policy_compliance_failure_taxonomy.md)
  — 3-layer model now superseded by 5-axis model
- [pi-bench spec](specs/pi-bench.md) — needs final update
