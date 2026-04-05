# Scenario Authoring Guide

This is the canonical starting point for creating or editing scenarios.
It replaces the older scratchpad authoring notes with a smaller set of
source-of-truth links and authoring rules.

## Canonical References

- [docs/specs/pi-bench-spec.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/specs/pi-bench-spec.md) — benchmark goals and philosophy
- [docs/specs/evaluation-rigor.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/specs/evaluation-rigor.md) — outcomes-over-trajectories evaluation design
- [docs/scenario-schema.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/scenario-schema.md) — required scenario fields
- [docs/evaluation-reference.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/evaluation-reference.md) — what the evaluator actually checks today
- [docs/specs/episode-isolation.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/specs/episode-isolation.md) — reproducibility requirements

## Authoring Rules

1. Write scenarios as realistic enterprise tasks, not direct policy quizzes.
2. Hide the decisive facts in environment state and tool outputs, not in the user’s first message.
3. Encode deterministic pass/fail checks for every hard requirement.
4. Use ordering checks only when the policy truly imposes a temporal dependency.
5. Prefer outcome and constraint checks over one fixed “gold” trajectory.
6. Make every scenario reproducible: deterministic environment state, explicit `now`, and isolated DB patches.
7. Keep semantic or language-quality checks separate from hard pass/fail checks.

## Required Check Coverage

Every strong scenario should make the expected behavior legible across these dimensions where applicable:

- decision correctness
- forbidden actions / permissibility
- required actions or outcomes
- temporal dependencies
- final state correctness

## When To Add More Checks

Add more checks when:

- the policy has multiple mandatory gates
- a forbidden shortcut could still reach the same final state
- the scenario is meant to test procedural depth, not just the final verdict
- ordering matters for safety, authorization, or auditability

Do not add checks that force a single route when multiple valid routes are acceptable.
