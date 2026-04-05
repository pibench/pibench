# Independent Taxonomy Review (2026-03-21)

This document is an independent re-synthesis of the local research taxonomy work. It reviews the prior synthesis documents, identifies where they agree and conflict, and recommends a taxonomy structure for pi-bench.

## 1. Sources Reviewed

Primary synthesis sources reviewed:

- `docs/workspace_analysis/policy-taxonomy-research-2026-03-14/taxonomy_assessment.md`
- `research/mar14-litrvw/papers/EMERGENT_TAXONOMY.md`
- `research/mar14-litrvw/papers/SYNTHESIS.md`
- `research/mar14-litrvw/papers/TAXONOMY_COMPARISON.md`
- `research/mar14-litrvw/papers/GROUNDED_TAXONOMY.md`
- `research/mar14-litrvw/papers/FINAL_TAXONOMY.md`
- `research/pi-bench/docs/SPEC.md`

Important count note:

- the local paper bundle inventory dated 2026-03-14 says 64 accessible PDFs were centralized in that bundle
- the March 2026 research synthesis documents repeatedly refer to an 87-paper review
- I did not verify a single source file in this repo that says the final synthesis covered exactly 90 papers

## 2. What The Prior Syntheses Agree On

Across the documents, the following points are stable:

1. `Policy Activation` is real and distinct.
   - It is not the same as interpretation.
   - Hidden-trigger and scope-recognition failures are repeatedly treated as a separate phenomenon.

2. `Procedural Compliance` is real and distinct.
   - Outcome success and policy-following are not the same.
   - Ordering and gating failures are a core benchmark target.

3. `Authorization / Access Control` is real and distinct.
   - Identity, permissions, and separation of duties form a separate capability surface.

4. `Epistemic Discipline` or `Escalation Judgment` is important and under-benchmarked.
   - Even the syntheses that compress the taxonomy keep escalation as a first-class differentiator.

5. `Operational Safety` matters, but it is partly a trust / deployment property rather than a pure reasoning faculty.

6. `Privacy / Information Flow` is underrepresented in the current scenario taxonomy.
   - Multiple research notes treat privacy as distinct from general safety.

7. The benchmark should not collapse to one overall score.
   - The documents consistently favor an MTEB-style decomposed view.

## 3. Where The Prior Syntheses Conflict

The documents diverge on three major questions.

### 3.1 Are the current nine categories final?

No consistent answer.

- `taxonomy_assessment.md` says the current nine are useful but not a final or fundamental master taxonomy.
- `SYNTHESIS.md` uses the nine as a practical mapping over the 87-paper review.
- `FINAL_TAXONOMY.md` proposes a different, compressed "validated" taxonomy for implementation.

### 3.2 Is `Norm Resolution` a standalone category?

No consistent answer.

- `taxonomy_assessment.md` says keep it.
- `TAXONOMY_COMPARISON.md` treats it as a genuine pi-bench contribution.
- `GROUNDED_TAXONOMY.md` and `FINAL_TAXONOMY.md` demote it into interpretation because the literature has not independently isolated it.

### 3.3 Is `Temporal Integrity` a standalone category?

No consistent answer.

- `taxonomy_assessment.md` says keep it.
- `TAXONOMY_COMPARISON.md` and `SYNTHESIS.md` treat it as one of pi-bench's genuine additions.
- `GROUNDED_TAXONOMY.md` keeps temporal reasoning.
- `FINAL_TAXONOMY.md` later demotes it to a scenario tag, not a leaderboard column.

### 3.4 Is `Justification Integrity` a category or a metric?

No consistent answer.

- `taxonomy_assessment.md` says keep it, but place it in a trust / audit layer.
- `TAXONOMY_COMPARISON.md` treats it as a distinctive pi-bench contribution.
- `GROUNDED_TAXONOMY.md` and `FINAL_TAXONOMY.md` argue it is better as a cross-cutting metric than a core capability.

### 3.5 Should scenario taxonomy and public leaderboard taxonomy be the same thing?

No consistent answer.

- the scenario authoring material assumes a scenario taxonomy
- `research/pi-bench/docs/SPEC.md` defines a different public 9-column task-type leaderboard:
  - `Compliance`
  - `Understanding`
  - `Robustness`
  - `Process`
  - `Restraint`
  - `Conflict Resolution`
  - `Detection`
  - `Explainability`
  - `Adaptation`

That means the project already contains two different answers to "what the leaderboard columns should be."

## 4. My Review Of The Prior Syntheses

My view is that the prior work is strongest when it separates evidence from design preference.

### 4.1 What I agree with

I agree with:

- the assessment that the current nine are a strong v1 benchmark taxonomy
- the claim that privacy deserves stronger treatment than the current scenario taxonomy gives it
- the claim that escalation / abstention is a core differentiator
- the push toward a layered taxonomy rather than a single flat list
- the idea that justification quality should be evaluated across the benchmark, not only in a few dedicated scenarios

### 4.2 What I think is too aggressive

I think the later compression in `FINAL_TAXONOMY.md` goes too far in two places:

1. Demoting `Norm Resolution`
   - The literature may not isolate it cleanly yet, but the benchmark is allowed to define a novel category when the failure surface is important and operationally distinct.
   - If a system fails specifically on conflicting obligations, I would want to see that broken out.

2. Demoting `Temporal Integrity`
   - The argument that temporal failures decompose into interpretation plus procedure is too narrow.
   - In agent systems, memory, accumulation, deadlines, and cross-turn state tracking create a real and diagnosable failure surface.
   - The interventions are also different: memory/state tooling, accumulators, counters, state-query discipline.

### 4.3 What I think the current scenario taxonomy gets wrong

The current scenario taxonomy under-specifies privacy and over-promotes justification.

- `Privacy / Information Flow` should be explicit
- `Justification Integrity` should be scored everywhere, not only treated as one bucket

## 5. My Recommended Taxonomy

I would use a layered structure.

### 5.1 Core capability columns

These are the main leaderboard categories I would use for agent evaluation:

1. `Policy Activation`
   - Does the agent recognize that a rule or trigger applies?

2. `Policy Interpretation`
   - Does the agent correctly understand the meaning of the relevant rule text?

3. `Norm Resolution`
   - Can the agent handle conflicting clauses, exceptions, and precedence correctly?

4. `Temporal Integrity`
   - Can the agent reason correctly over time, history, cumulative limits, and cross-turn state?

5. `Procedural Compliance`
   - Does the agent follow required steps in the correct order?

6. `Authorization Governance`
   - Does the agent verify identity, permissions, and authority before acting?

7. `Operational Safety`
   - Does the agent avoid prohibited actions and unsafe instrumental behavior?

8. `Privacy & Information Flow`
   - Does the agent prevent inappropriate disclosure, compositional leakage, and recipient-inappropriate sharing?

9. `Epistemic Discipline`
   - Does the agent recognize when it lacks enough evidence or authority and escalate instead of guessing?

### 5.2 Cross-cutting scored metrics

These should be scored across all categories, not treated as scenario buckets:

- `Justification Integrity`
  - Does the stated reason match the action and the correct policy basis?

- `Evidence Grounding`
  - Is the explanation anchored to the right clause, source, or evidence?

- `Text-Action Consistency`
  - Did the agent say one thing and do another?

### 5.3 Metadata and slicing dimensions

These should be filters or tags, not primary leaderboard columns:

- policy regime or source
- domain
- pressure / difficulty tier
- multi-turn vs short-horizon
- policy drift
- policy stack / layered precedence
- language

## 6. Why I Recommend This Taxonomy

This recommendation is a compromise between the strongest parts of the earlier syntheses:

- it preserves the benchmark's diagnostic strengths
- it keeps novel but operationally important categories
- it fixes the clearest omission from the literature review: privacy
- it avoids treating justification as if it were only relevant in a few scenarios

In short:

- I reject the idea that the current scenario nine should remain unchanged forever
- I also reject the later move to compress too aggressively into a smaller set
- I recommend a revised 9-column capability taxonomy plus cross-cutting trust metrics

## 7. Should Scenario Taxonomy And Public Leaderboard Taxonomy Be The Same?

No.

They should be related, but not identical.

### 7.1 Scenario taxonomy

Scenario taxonomy should be diagnostic and author-facing.

It should answer:

- what exact failure surface is this scenario designed to isolate?

For that purpose, the 9 capability taxonomy above works well.

### 7.2 Public leaderboard taxonomy

The public leaderboard can be either:

1. the same 9 capability columns, if you want maximum diagnostic transparency
2. or a more user-facing rolled-up view, if you want easier market communication

If you want a rolled-up public view, I would group them as:

- `Policy Understanding`
  - `Policy Activation`
  - `Policy Interpretation`
  - `Norm Resolution`

- `Policy Execution`
  - `Temporal Integrity`
  - `Procedural Compliance`
  - `Authorization Governance`

- `Policy Boundaries`
  - `Operational Safety`
  - `Privacy & Information Flow`
  - `Epistemic Discipline`

And I would still show:

- `Justification Integrity`
- `Evidence Grounding`

as trust / audit metrics beside those groups.

## 8. Practical Implication For The Current Repo

For the current `workspace` codebase, my recommendation is:

1. Do not treat the current `metrics.py` taxonomy as the source of truth.
2. Do not blindly keep the current scenario taxonomy unchanged as the final public leaderboard.
3. In the short term:
   - align runtime reporting with the scenario taxonomy already in the data
4. In the medium term:
   - revise the scenario taxonomy from:
     - `Operational Safety`
     - `Justification Integrity`
   - toward:
     - `Operational Safety`
     - `Privacy & Information Flow`
     - cross-cutting `Justification Integrity`
5. Keep `Norm Resolution` and `Temporal Integrity` as explicit benchmark categories unless and until the empirical program shows they truly fail only as subcases of other columns.

## 9. Bottom Line

My independent recommendation is:

- use a revised 9-column capability taxonomy
- add `Privacy & Information Flow`
- move `Justification Integrity` to a cross-cutting metric
- keep `Norm Resolution` and `Temporal Integrity` as first-class benchmark categories
- separate diagnostic scenario taxonomy from public-facing leaderboard presentation
