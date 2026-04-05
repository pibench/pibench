# Fourth Reviewer Critique: Tightening Definitions

> Largely validates the existing design. Agrees with core claims,
> ablation mindset, pressure-as-multiplier hypothesis, and the hard
> problems list. Contributes five specific tightenings and one
> correction. Most of what this reviewer recommends we've already
> incorporated from previous reviews.

## Where This Reviewer Agrees Strongly

- Independent layers framing (mind/body/hands) is correct
- Ablation mindset is the real contribution
- Pressure as multiplier (not additive) is the right hypothesis
- Hard problems list is correct (stacked/precedence policies, tool
  composition violations, harness-induced failures, text-action
  misalignment)
- Deterministic trace-based evaluation, no LLM judge
- Mandatory decision event (we already have this: Decision Signal Design)
- Hard-Gate / Audit-Only (we already have this: from Doc 5)
- Policy stack as first-class pressure axis (we already have this:
  from porting review)

## What This Reviewer Uniquely Contributes

### A) Surfaces as Distributions over Primitives

Sharpens Reviewer 3's policy primitive library:

- **Primitives are atoms** — permissions, obligations, exceptions,
  escalation, scope/definitions
- **Surfaces are distributions over primitives** — authorization is
  mostly permissions + scope, SOP workflows are mostly obligations +
  exceptions

This means: don't index the *generator* by surface type. Compose
scenarios from primitives. The surface type is a *label*, not a
*design input*. This prevents the benchmark from being "domain
taxonomy first" (which tends to saturate) and makes it "mechanism-first."

**Status:** Incorporated. This is the right sharpening. Surfaces
become the molecule; primitives become the atom. The scenario
generator composes from primitives, surface type is post-hoc labeling.

### B) Observable Trace Signatures per Failure Axis

Every failure type in the taxonomy must have a mandatory observable
signature. Not "sounded like a refusal" but a specific trace event:

| Failure axis | Observable signature |
|---|---|
| Interpretation error | Wrong canonical decision event |
| Fact-gathering miss | Missing required verification tool call(s) |
| Execution violation | Forbidden tool called / args outside bounds / ordering violated |
| Harness-induced | Consistent failure only in specific harness config (Mode 5 delta) |

**Status:** We already have this implicitly (every check type is
trace-grounded). But this reviewer makes explicit that the *failure
taxonomy* entries must each map to specific check types. The taxonomy
is not just descriptive — it must be operationally grounded.

This means the failure categories in the spec should include their
observable signatures, not just prose descriptions. Good tightening.

### C) EchoLeak CVE Correction

The failure taxonomy document has the wrong CVE for EchoLeak:

- **Wrong:** CVE-2025-59944
- **Correct:** CVE-2025-32711, CVSS 9.3

Source: [TechRepublic](https://www.techrepublic.com/article/news-microsoft-365-copilot-flaw-echoleak/)

### D) Structured Policy -> Policy-Excerpt Oracle

The Structured Policy ablation (Mode 3) risks contradicting our own
non-requirement of not formalizing policies. If "structured" means
converting prose into rulespec/LTL/Cedar-like structure, it violates
the spec's "no formal policy conversion" principle.

Two alternatives proposed:

1. **Policy-Excerpt Oracle (recommended for v1):** Give the agent
   only the relevant passages (still prose), not the entire document.
   Isolates "find the clause" vs "apply the clause" without any
   formalization.

2. **Semi-structured rewrite:** Convert prose into bullets/checklist,
   still natural language, preserving exception words
   (IF/UNLESS/EXCEPT) literally. Removes ambiguity without becoming
   a formal language.

**Our assessment:** This is a valid concern. However, we already have
Evidence-Oracle (Mode 4) which supplies relevant excerpts. The
distinction is:

- **Evidence-Oracle** = relevant *passages* from the policy (excerpts)
- **Structured Policy** = the full policy rewritten as clean rules

The reviewer's concern is about *how structured* "structured" gets.
The resolution: Structured Policy means **semi-structured rewrite**
(option 2) — bullets, clear conditionals, no ambiguity, but still
natural language. Never formal logic. This is consistent with our
"no RuleSpec" principle because the rewrite is still human-readable
prose, just unambiguous.

Key clarification added to spec: "Structured Policy replaces messy
prose with clear, unambiguous natural language (bullet points, explicit
conditionals). It does NOT convert to formal logic, structured rules,
or machine-readable policy languages."

### E) Tool-Isolated -> Tool-Projection Metric

The reviewer correctly observes that "Tool-Isolated" (Mode 6 in the
original failure taxonomy) doesn't remove a challenge from the agent
— it changes what we *measure*. It's an evaluation projection, not
an ablation mode.

Reframing:

- **Tool-Projection Compliance:** evaluate the same Default runs in a
  tool-only view (ignore message content, decision signals)
- **Text-Action Gap** = (decision-correct rate) - (tool-compliant rate)

This gap measures how often the agent's stated decision diverges from
its actual tool behavior. It's the "actions override claims" principle
quantified.

**Status:** This is already captured by our "actions override claims"
conflict handling. But framing it as a *named metric* (Text-Action
Gap) computed from existing runs (no new runs needed) is a good
addition. It's a derived metric, not an ablation mode.

### F) Citation Verification Results

The reviewer verified several regulatory claims:

| Claim | Status | Source |
|---|---|---|
| EU AI Act fines up to 35M/7% | Verified | [EU AI Act Art. 99](https://artificialintelligenceact.eu/article/99) |
| FINRA 2026 oversight mentions agent risks | Verified | [FINRA 2026 Report](https://www.finra.org/media-center/newsreleases/2025/finra-publishes-2026-regulatory-oversight-report-empower-member-firm) |
| OWASP Top 10 for LLMs: Prompt Injection = LLM01 | Verified | [OWASP](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| NIST AI 600-1 GenAI Profile | Verified | [NIST](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) |
| HIPAA documentation retention | 6 years (not "6-7") | [45 CFR 164.316(b)(2)(i)](https://www.law.cornell.edu/cfr/text/45/164.316) |
| PCI DSS 4.0 MFA for CDE access | Verified (best practice until Mar 2025, assessed after) | [PCI DSS v4.0 QRG](https://www.gvsu.edu/cms4/asset/9539BEE0-AB4D-AD66-BE5FF618A6CA0752/pci_dss-qrg-v4_0.pdf) |
| PCI DSS vulnerability remediation | Risk-analysis based, not immediate for all | [OBS Global](https://info.obsglobal.com/pci-dss-4.0/authenticated-vulnerability-scanning) |
| OWASP Agentic Applications | Verified | [OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) |

Flagged as needing citations: "200,000 conversations" study, governance
percentages, overlap percentages.

---

## Four-Way Convergence: What's New vs Already Incorporated

| Reviewer 4 recommendation | Status | Where incorporated |
|---|---|---|
| Mandatory decision event | Already done | Decision Signal Design doc |
| Hard-Gate / Audit-Only | Already done | Porting Review Response, spec |
| Policy stack as pressure axis | Already done | Spec, analysis doc |
| Observable trace signatures | Tightening | Spec failure categories updated |
| Surfaces as distributions | Sharpening | Spec, analysis doc updated |
| Structured Policy clarification | Clarification | Spec wording tightened |
| Tool-Isolated -> Tool-Projection | Reframing | Deferred metric (not ablation) |
| EchoLeak CVE | Correction | Failure taxonomy fixed |
| Citation verification | Reference | This document |

---

## Net Changes to the Design

### Spec changes

1. Failure categories: each now maps to observable trace signature(s)
2. Structured Policy: clarified as "unambiguous natural language" not
   formal logic
3. Surface/primitive relationship: surfaces are distributions over
   primitives, primitives are atoms, surfaces are labels
4. Text-Action Gap: named as a derived metric from Default runs

### No structural changes

The ablation suite, failure model axes, and evaluation pipeline are
unchanged. This reviewer validated the existing merged design and
provided precision tightenings.

---

## Related Documents

- [Decision Signal Design](decision_signal_design.md) — validates
  reviewer's recommendation (already implemented)
- [Architecture: Wrap, Don't Replace](architecture_wrap_not_replace.md)
  — validates reviewer's structural assessment
- [Third Reviewer Critique](third_reviewer_critique.md) — policy
  primitive library that this reviewer sharpens
- [Second Reviewer Critique](second_reviewer_critique.md) — four-axis
  model that this reviewer validates
- [Porting Review Response](porting_review_response.md) — Hard-Gate,
  Ever@k/Always@k already incorporated
- [Policy compliance failure taxonomy](policy_compliance_failure_taxonomy.md)
  — EchoLeak CVE corrected per this review
- [pi-bench spec](specs/pi-bench.md) — tightenings applied
