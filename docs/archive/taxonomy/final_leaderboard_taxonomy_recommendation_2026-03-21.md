# Final Leaderboard Taxonomy Recommendation

Date: 2026-03-21

This document gives the final recommended taxonomy for a greenfield pi-bench-style leaderboard after reviewing:

- the current scenario taxonomy
- the local taxonomy synthesis docs
- the 64-PDF source bundle

## 1. Design Goal

The leaderboard columns should work like MTEB task columns:

- each column should represent a distinct capability
- models should plausibly rank differently across columns
- each column should correspond to a different intervention / improvement path
- columns should answer different deployment questions

The columns should **not** mix together:

- core capabilities
- stress conditions
- trust / audit metrics
- evaluation metrics
- guardrail-only evaluator tasks

## 2. Final Recommendation

Use **9 primary leaderboard columns**.

### 2.1 Primary capability columns

1. `Policy Activation`
   - Can the agent catch the hidden, blocking, or scope-defining rule that actually controls the case, even when the user's framing points elsewhere?

2. `Policy Interpretation`
   - Can the agent correctly understand the meaning of the relevant rule text?

3. `Evidence Grounding`
   - Can the agent retrieve and anchor its behavior to the correct clause, obligation, or evidence?

4. `Procedural Compliance`
   - Can the agent follow required steps in the correct order, without skipping gates?

5. `Authorization & Access Control`
   - Can the agent verify identity, permission, and authority before acting?

6. `Temporal / State Reasoning`
   - Can the agent reason correctly over time, history, cumulative limits, deadlines, and evolving state?

7. `Safety Boundary Enforcement`
   - Can the agent avoid prohibited actions and unsafe instrumental behavior?

8. `Privacy & Information Flow`
   - Can the agent prevent inappropriate disclosure, recipient mismatch, and compositional leakage?

9. `Escalation / Abstention`
   - Can the agent recognize when it lacks sufficient evidence or authority and defer rather than guess?

## 3. Roll-Up Groups

Use three top-level roll-ups for reporting:

### 3.1 Policy Understanding

- `Policy Activation`
- `Policy Interpretation`
- `Evidence Grounding`

### 3.2 Policy Execution

- `Procedural Compliance`
- `Authorization & Access Control`
- `Temporal / State Reasoning`

### 3.3 Policy Boundaries

- `Safety Boundary Enforcement`
- `Privacy & Information Flow`
- `Escalation / Abstention`

These roll-ups are summaries only. The real leaderboard should still show the 9 columns.

## 4. What Should Not Be Primary Leaderboard Columns

### 4.1 Sub-dimensions, not primary columns

- `Norm Resolution`
  - Keep visible as a named subscore or scenario family under `Policy Interpretation`
- `Policy Drift`
- `Policy Stack / Layered Precedence`
- `Indirect Trigger Handling`

### 4.2 Cross-cutting trust / audit metrics

- `Justification Integrity`
- `Text-Action Consistency`
- `Overall Compliance Rate`
- `Completion-under-Policy`
- `pass^k` / repeatability
- risk / violation rates

These should be reported across the benchmark, not used as the main capability taxonomy.

### 4.3 Stress conditions / difficulty slices

- adversarial user pressure
- social engineering / sycophancy
- multi-turn wear-down
- policy ambiguity
- conflicting rules
- long context / information overload

These are difficulty modifiers, not capability columns.

### 4.4 Separate evaluator / guardrail track

- policy-violation detection
- trajectory monitoring
- guardrail judgment

These are real benchmark targets, but they belong on a separate guardrail leaderboard or as `n/a` columns for general-purpose acting agents.

## 5. Why This Is The Recommended Shape

This structure best fits the evidence:

- it preserves the strongest distinct capability surfaces supported by the source papers
- it keeps privacy as first-class instead of burying it in generic safety
- it keeps escalation / abstention explicit
- it treats evidence grounding as more than a side note
- it avoids over-promoting justification into a main capability column
- it avoids mixing stress conditions with base capabilities

## 6. Practical Benchmark Authoring Guidance

If this taxonomy is adopted:

- every scenario should have exactly one primary leaderboard column
- scenarios may also carry sub-tags like `conflict`, `policy_drift`, `indirect_attack`, `multi_turn`
- `Norm Resolution` scenarios should usually be primary `Policy Interpretation` plus sub-tag `conflict`
- `Justification Integrity` should be scored in evaluation across many scenarios, not isolated into its own benchmark bucket
- reports should show:
  - 9 primary column scores
  - 3 roll-up scores
  - cross-cutting trust metrics
  - stress slices

## 7. Final Answer

If the question is:

> “What should the final greenfield leaderboard taxonomy be?”

The answer is:

### Use these 9 columns

1. `Policy Activation`
2. `Policy Interpretation`
3. `Evidence Grounding`
4. `Procedural Compliance`
5. `Authorization & Access Control`
6. `Temporal / State Reasoning`
7. `Safety Boundary Enforcement`
8. `Privacy & Information Flow`
9. `Escalation / Abstention`

### Roll them up into these 3 broader groups

- `Policy Understanding`
- `Policy Execution`
- `Policy Boundaries`

This is the cleanest MTEB-like design I can defend from the research and source-paper review.
