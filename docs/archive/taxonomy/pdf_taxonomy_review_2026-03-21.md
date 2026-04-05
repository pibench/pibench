# PDF Taxonomy Review (64-Paper Bundle)

Date: 2026-03-21

This note summarizes an independent review of the 64-PDF local bundle referenced by:

- `docs/workspace_analysis/policy-taxonomy-research-2026-03-14/paper_inventory.md`

Bundle composition:

- 40 PDFs from `research/policy-intelligence`
- 15 PDFs from `research/policy-benchmark-review/papers`
- 9 gap PDFs from `docs/workspace_analysis/policy-taxonomy-research-2026-03-14/papers/downloaded`

For this pass, readable text was extracted from the first four pages of each PDF into `/tmp/pibench_pdf_review`, then reviewed in four non-overlapping chunks plus spot-checks of anchor papers.

## 1. Strongest Findings From The Source PDFs

Across the 64-PDF bundle, the most consistently supported standalone capability categories are:

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Temporal / State Reasoning`
6. `Safety Boundary Enforcement`
7. `Privacy & Information Flow`
8. `Escalation / Abstention`

The strongest repeated pattern is that the papers do **not** support a single flat notion of "policy compliance." They consistently separate:

- finding the right rule
- understanding the rule
- following procedures correctly
- avoiding forbidden actions
- preserving sensitive information
- knowing when not to act

## 2. What The PDFs Support Strongly

### 2.1 Policy Activation

This is strongly supported as separate from interpretation.

Representative papers:

- `RuleArena`
- `POLIS-Bench`
- `IFEval`
- `tau-bench`

Repeated finding:

- models often fail before reasoning even starts because they do not identify which clause, trigger, or instruction actually applies

### 2.2 Policy Interpretation

This is one of the best-supported categories in the corpus.

Representative papers:

- `LegalBench`
- `LexGLUE`
- `MAUD`
- `ContractNLI`
- `GuideBench`
- `POLIS-Bench`
- `RegNLP / RIRAG`

Repeated finding:

- understanding domain policy language is separate from retrieving it
- interpretation degrades under ambiguity, domain updates, and complex paragraph context

### 2.3 Procedural Compliance

This is also strongly supported as its own capability.

Representative papers:

- `SOPBench`
- `JourneyBench`
- `tau-bench`
- `tau2-bench`
- `LogiSafetyBench`

Repeated finding:

- task success and policy-following are not the same
- agents often complete the goal while skipping required steps, validations, or order constraints

### 2.4 Authorization & Access Control

This is strongly supported by the policy-agent and formal-policy papers, though not by every part of the corpus equally.

Representative papers:

- `tau2-bench`
- `Cedar`
- `GuardAgent`

Repeated finding:

- identity, permissions, and separation of duties form a separate failure surface
- authorization is not reducible to generic interpretation or generic procedure

### 2.5 Temporal / State Reasoning

This is directly supported by the temporal reasoning papers and reinforced by agent settings with cross-turn state.

Representative papers:

- `TimeBench`
- `DateLogicQA`
- `ActionReasoningBench`
- `CNFinBench` (via the research synthesis chain)

Repeated finding:

- models struggle with deadlines, date windows, cumulative state, history-dependent rules, and action-state evolution

### 2.6 Safety Boundary Enforcement

This is one of the strongest categories in the corpus.

Representative papers:

- `AgentHarm`
- `Agent-SafetyBench`
- `ToolEmu`
- `HarmBench`
- `ODCV-Bench`
- `LogiSafetyBench`
- `ST-WebAgentBench`

Repeated finding:

- agents can understand the task and still violate policy or safety boundaries
- harmful or prohibited behavior is not reducible to misunderstanding policy text

### 2.7 Privacy & Information Flow

This is the clearest gap in the current pi-bench scenario taxonomy.

Representative papers:

- `CoPriva`
- `Doc-PP`
- `PrivacyLens`
- `PrivaCI-Bench`
- `TOP-Bench`
- `AgentLeak`

Repeated finding:

- privacy leakage is not just "general safety"
- indirect attacks, recipient mismatch, compositional leakage, and contextual non-disclosure are distinct and important

### 2.8 Escalation / Abstention

This is strongly supported by the newer uncertainty-handling papers.

Representative papers:

- `AbstentionBench`
- `OpenExempt` (diagnostic skill isolation)
- `Policy Compliance User Requests`
- `R-Judge` (indirectly)

Repeated finding:

- knowing when not to answer is an unsolved problem
- uncertainty handling is not fixed by general reasoning scale alone

## 3. What The PDFs Support Only Weakly Or Indirectly

### 3.1 Norm Resolution

The PDF review supports keeping conflict handling visible, but the evidence for it as a universal top-level category is weaker than for the eight categories above.

What the papers support:

- conflicting directives and priority failures are real
- instruction hierarchy and control-priority failures are measurable
- legal and policy conflicts matter in practice

What is weaker:

- a broad, stable literature consensus that conflict resolution must be its own public leaderboard column

Best interpretation:

- keep `Norm Resolution` visible
- but treat it as either:
  - a named sub-dimension under `Policy Interpretation`, or
  - a flagship benchmark-specific category if pi-bench wants to emphasize it as a differentiator

### 3.2 Justification Integrity

The corpus supports justification and explanation quality as important, but not cleanly as a standalone capability bucket on the same level as activation, procedure, privacy, or abstention.

What the papers support:

- legal answers should cite evidence
- compliance systems should justify decisions
- explanation quality matters for audit and trust

Best interpretation:

- split this into:
  - `Evidence Grounding`
  - `Justification Integrity`
- do not treat raw justification quality alone as the main taxonomy bucket

## 4. Capability Categories vs Other Things

One of the clearest lessons from the PDF review is that prior syntheses were mixing different kinds of dimensions.

These should be separated:

### 4.1 Core capabilities

- `Policy Activation`
- `Policy Interpretation`
- `Procedural Compliance`
- `Authorization & Access Control`
- `Temporal / State Reasoning`
- `Safety Boundary Enforcement`
- `Privacy & Information Flow`
- `Escalation / Abstention`

### 4.2 Cross-cutting trust / audit metrics

- `Evidence Grounding`
- `Justification Integrity`
- `Text-Action Consistency`

### 4.3 Pressure or robustness slices

- adversarial prompting / jailbreak pressure
- sycophancy / social engineering pressure
- multi-turn / long-horizon degradation
- policy drift / rule updates
- indirect attacks

### 4.4 Separate evaluator / guardrail track

- policy-violation detection
- trajectory monitoring
- guardrail judgment

These are real tasks, but they are not the same as the capabilities required of an acting agent.

## 5. Recommended Taxonomy After Reviewing The PDFs

### 5.1 Public capability taxonomy

This is the taxonomy I would recommend after reviewing the 64-PDF bundle:

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Temporal / State Reasoning`
6. `Safety Boundary Enforcement`
7. `Privacy & Information Flow`
8. `Escalation / Abstention`

### 5.2 Visible sub-dimensions

These should be reported visibly, but not necessarily elevated to top-level columns:

- `Norm Resolution`
- `Evidence Grounding`

### 5.3 Cross-cutting metrics

- `Justification Integrity`
- `Text-Action Consistency`
- `Completion-under-Policy`
- `pass^k` / reliability
- `Risk Ratio` or equivalent safety/compliance failure rate

## 6. Implication For The Current pi-bench Taxonomy

Relative to the current scenario taxonomy:

Keep:

- `Policy Activation`
- `Norm Interpretation` or renamed `Policy Interpretation`
- `Procedural Compliance`
- `Authorization Governance`
- `Temporal Integrity`
- `Operational Safety` or renamed `Safety Boundary Enforcement`
- `Epistemic Discipline` or renamed `Escalation / Abstention`

Change:

- add `Privacy & Information Flow` as a first-class category
- move `Justification Integrity` out of the main capability taxonomy and treat it as a cross-cutting metric

Borderline:

- keep `Norm Resolution` visible, but consider whether it is:
  - a top-level benchmark-specific category
  - or a named subscore under interpretation/conflict handling

## 7. Bottom Line

After reviewing the 64 local source PDFs, I would not keep the raw current 9-category scenario taxonomy as the final public leaderboard taxonomy.

I would also not compress everything down so far that privacy, temporal reasoning, or abstention disappear.

The best-supported public capability taxonomy from the PDF evidence is:

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Temporal / State Reasoning`
6. `Safety Boundary Enforcement`
7. `Privacy & Information Flow`
8. `Escalation / Abstention`

With:

- `Norm Resolution` as a visible sub-dimension
- `Evidence Grounding` as a visible audit/evidence dimension
- `Justification Integrity` as a cross-cutting metric
