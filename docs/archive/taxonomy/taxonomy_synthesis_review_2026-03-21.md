# Taxonomy Synthesis Review (2026-03-21)

This note is an independent review of the local research synthesis chain. The goal is not to repeat the existing conclusion, but to check where the prior synthesis is solid, where it conflicts with itself, and what taxonomy should actually be used going forward.

## 1. What I Reviewed

Primary inputs:

- `docs/workspace_analysis/policy-taxonomy-research-2026-03-14/taxonomy_assessment.md`
- `research/mar14-litrvw/papers/EMERGENT_TAXONOMY.md`
- `research/mar14-litrvw/papers/TAXONOMY_COMPARISON.md`
- `research/mar14-litrvw/papers/GROUNDED_TAXONOMY.md`
- `research/mar14-litrvw/papers/FINAL_TAXONOMY.md`
- `research/mar14-litrvw/papers/SYNTHESIS.md`
- `research/pi-bench/docs/SPEC.md`

The literature synthesis consistently refers to an 87-paper review. A separate local inventory document tracks a 64-PDF bundle, but that is a local access bundle, not the full synthesized paper count.

## 2. What the Prior Synthesis Gets Right

Several conclusions are stable across the docs:

1. `Policy Activation` is distinct from interpretation.
   - This is one of the strongest repeated findings.
   - Retrieval / activation and interpretation are not the same failure surface.

2. `Procedural Compliance` is a real standalone capability.
   - The literature repeatedly distinguishes outcome success from procedural correctness.

3. `Authorization Governance` is real and important.
   - The main ambiguity is not whether it exists, but whether it is a capability, a policy regime, or both.

4. `Epistemic Discipline` is one of pi-bench's strongest contributions.
   - The literature does not benchmark escalation / abstention cleanly, but the need is repeatedly justified.

5. `Privacy / Information Flow` is under-modeled in the current scenario taxonomy.
   - This is the clearest gap relative to the literature.

6. `Justification Integrity` is important.
   - The open question is whether it should be a top-level capability or a cross-cutting metric.

## 3. Where the Prior Synthesis Conflicts With Itself

The local research notes are not actually converging on one single taxonomy. They contain at least three different abstractions:

### 3.1 Bottom-up literature clusters

`EMERGENT_TAXONOMY.md` derives 6 broad clusters from the 87 papers:

- rule comprehension & retrieval
- procedural execution & ordering
- authorization & access control
- safety boundary enforcement
- privacy & information flow control
- legal & regulatory reasoning

This is broad and literature-faithful, but too coarse to directly drive scenario design.

### 3.2 Benchmark scenario taxonomy

The older pi-bench scenario work uses the 9-category scenario taxonomy:

- Policy Activation
- Norm Interpretation
- Norm Resolution
- Authorization Governance
- Temporal Integrity
- Procedural Compliance
- Operational Safety
- Epistemic Discipline
- Justification Integrity

This is much more diagnostic for benchmark construction, but it mixes levels:

- some are reasoning operations
- some are control / trust properties
- some are partly domain-specific

### 3.3 Public leaderboard taxonomy

The research `SPEC.md` does not use either of the above directly. It defines 9 public leaderboard task types:

- Compliance
- Understanding
- Robustness
- Process
- Restraint
- Conflict Resolution
- Detection
- Explainability
- Adaptation

These are audience-facing evaluation dimensions, not scenario authoring labels.

## 4. The Core Problem

Most of the disagreement in the prior synthesis is caused by trying to force one flat list to do three jobs:

1. organize scenario authoring
2. represent cognitive capabilities
3. serve as public leaderboard columns

Those are not the same thing.

If one list is forced to serve all three roles, drift is almost guaranteed.

## 5. My Independent Synthesis

### 5.1 The current scenario 9 are good benchmark-construction categories

They are good because they are:

- concrete enough to design scenarios against
- diagnostic enough to explain failures
- already aligned with the scenario corpus

But they are not level-consistent enough to serve as the final universal taxonomy for "all policy agents."

### 5.2 The public leaderboard should not use the raw scenario 9 unchanged

The strongest reasons:

- `Operational Safety` is too broad and should be split from privacy / information flow
- `Justification Integrity` behaves more like an auditability metric than a core action capability
- `Authorization Governance` mixes a reasoning capability with a policy regime
- `Norm Resolution` is important, but the literature evidence for its independent status is weaker than for activation, interpretation, procedure, authorization, privacy, or safety

### 5.3 The right answer is a layered taxonomy

There should be:

1. a scenario-design taxonomy
2. a public capability leaderboard taxonomy
3. cross-cutting trust / audit metrics

## 6. Recommended Taxonomy

### 6.1 Scenario-design taxonomy

Use this for authoring scenarios and assigning `taxonomy.primary`:

1. `Policy Activation`
2. `Norm Interpretation`
3. `Norm Resolution`
4. `Authorization Governance`
5. `Temporal Integrity`
6. `Procedural Compliance`
7. `Operational Safety`
8. `Epistemic Discipline`
9. `Justification Integrity`

Reason:

- this matches the current scenario corpus
- it preserves the benchmark's existing diagnostic resolution
- it is already the language the scenarios were written against

### 6.2 Public capability leaderboard taxonomy

Use this for public model comparison:

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Temporal / State Reasoning`
6. `Harm / Safety Boundaries`
7. `Privacy & Information Flow`
8. `Escalation Judgment`

This is my recommended top-level capability taxonomy.

Why this structure:

- `Policy Activation` stays separate from `Policy Interpretation`
- `Norm Resolution` becomes a named sub-family under `Policy Interpretation`, not a lost concept
- `Temporal Integrity` stays, because the literature and benchmark scenarios both support it as practically useful
- privacy is promoted to a first-class capability rather than being buried inside safety
- `Epistemic Discipline` is renamed more explicitly for public consumption as `Escalation Judgment`
- the labels are closer to deployment questions a user would actually care about

### 6.3 Cross-cutting trust and audit metrics

These should not be mixed into the same flat capability list:

1. `Justification Integrity`
2. `Evidence Grounding`
3. `Text-Action Consistency`
4. `Robustness Under Pressure`

Reason:

- these measure whether behavior is explainable, auditable, and stable
- they cut across multiple underlying capabilities
- they are important enough to report, but they should not distort the capability taxonomy

## 7. What This Means for the Current Repo

### 7.1 Near-term

For the current `workspace` benchmark:

- keep the existing 9-category scenario taxonomy as the canonical scenario taxonomy
- do not rename the scenario files right now
- wire reporting to that 9-category taxonomy first

This fixes the live codebase with minimal conceptual churn.

### 7.2 Medium-term

If the project wants a cleaner external leaderboard:

- add a derived roll-up layer from scenario taxonomy to public capability taxonomy
- add separate trust / audit metrics rather than folding them into the main capability list

That avoids losing information while still producing a cleaner leaderboard.

## 8. Final Recommendation

If the question is:

> "What taxonomy should we use tomorrow in the current benchmark code?"

Answer:

- use the current 9 scenario categories

If the question is:

> "What should the long-term public leaderboard taxonomy be for judging agents on policy understanding, interpretation, following, and compliance?"

Answer:

- do not use the raw current 9 as the final public taxonomy
- use a layered design
- recommend 8 public capability columns plus separate cross-cutting trust metrics

### Final proposed public capability taxonomy

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Temporal / State Reasoning`
6. `Harm / Safety Boundaries`
7. `Privacy & Information Flow`
8. `Escalation Judgment`

### Final proposed cross-cutting trust metrics

1. `Justification Integrity`
2. `Evidence Grounding`
3. `Text-Action Consistency`
4. `Robustness Under Pressure`

This is the most coherent synthesis I can defend from the current local research record.
