# How Scenario Evaluation Works Today

This document describes the **currently implemented** evaluator in the live
repo.

Use this file for current code behavior. Use
[docs/specs/pi-bench-spec.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/specs/pi-bench-spec.md)
for the target architecture and
[docs/specs/evaluation-rigor.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/specs/evaluation-rigor.md)
for planned rigor upgrades.

---

## Evaluator Entry Point

The live evaluator entry point is
[`src/pi_bench/evaluator/__init__.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/__init__.py).

Scenarios are evaluated from `task["evaluation_criteria"]`, not from the old
`expected_outcomes` / `scenario_checker.py` path.

At a high level:

1. The orchestrator produces a simulation with messages, trace, and env state.
2. `evaluate()` dispatches to the configured evaluator types in
   `evaluation_criteria.reward_basis`.
3. Deterministic checks contribute to `all_passed`.
4. LLM-judge checks contribute to `semantic_score` but do not block pass/fail.

---

## Current Result Shape

`evaluate()` currently returns:

```python
{
    "reward": 0.0 | 1.0,
    "reward_basis": [...],
    "reward_breakdown": {...},
    "all_passed": True | False,
    "semantic_score": 0.0-1.0,
    "outcome_results": [...],
    "dimensions": {
        "decision": {...},
        "permissibility": {...},
        "outcomes": {...},
        "ordering": {...},
        "state": {...},
        "semantic": {...},
    },
}
```

Important:

- `all_passed` is gated only by deterministic checks.
- `semantic_score` is separate because `NL_JUDGE` is non-deterministic.
- `dimensions` is a reporting breakdown over the same raw `outcome_results`.

---

## Where Checks Come From

### `POLICY`

`POLICY` uses `evaluation_criteria.policy_checks` and
[`src/pi_bench/evaluator/policy.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/policy.py).

Current check types include:

- `tool_called`
- `tool_not_called`
- `tool_called_with`
- `tool_called_any`
- `tool_called_min_times`
- `tool_before_tool`
- `tool_before_tool_any`
- `decision_equals`
- `message_not_contains`
- `escalation_attempted`

These checks run against the `TraceRecorder` plus assistant/user messages.

### `STATE_FIELD`

`STATE_FIELD` uses `evaluation_criteria.state_field_checks` and
[`src/pi_bench/evaluator/db.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/db.py).

These checks read `env["db"]` after the run and compare specific paths to
expected values.

### `NL_JUDGE`

`NL_JUDGE` uses `evaluation_criteria.nl_judge_checks` and
[`src/pi_bench/evaluator/llm_judge.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/llm_judge.py).

This is the current semantic layer. It asks a yes/no question about the
assistant messages and compares the judge answer to `expected_answer`.

The judge runs with:

- model: `gpt-4o-mini` by default
- temperature: `0.0`
- max tokens: `512`
- one retry on parse failure
- per-evaluation caching on `(text_hash, question)`

The cache is now local to a single evaluation run, so concurrent scenarios do
not share semantic results.

---

## Deterministic Vs Semantic Checks

The live evaluator has two tiers:

### Tier 1: deterministic

These checks gate `all_passed`:

- `POLICY` results except `NL_JUDGE`-style checks
- `STATE_FIELD`
- any other non-semantic evaluator configured in `reward_basis`

### Tier 2: semantic

These checks affect only `semantic_score`:

- `NL_JUDGE`
- `NL_ASSERTION` when present in older compatibility paths

So a scenario can:

- fail deterministically and still get `semantic_score = 1.0`, or
- pass deterministically and still get `semantic_score < 1.0`.

That separation is intentional.

---

## Dimension Breakdown

The current reporting split is:

| Dimension | Current source |
|---|---|
| `decision` | `decision_equals` |
| `permissibility` | `tool_not_called`, `message_not_contains` |
| `outcomes` | `tool_called`, `tool_called_with`, `tool_called_any`, `tool_called_min_times`, `escalation_attempted` |
| `ordering` | `tool_before_tool`, `tool_before_tool_any` |
| `state` | `state_field` |
| `semantic` | `NL_JUDGE`, `NL_ASSERTION`, `nl_assertion_llm_judge` |

This is a reporting classification over the current checks. It is not yet a
full executable procedural oracle.

---

## Decision Resolution

`decision_equals` is resolved deterministically via
[`src/pi_bench/decision/__init__.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/decision/__init__.py):

1. Prefer the last `record_decision` tool call.
2. If no decision tool call exists, fall back to a fenced JSON block in
   assistant messages.
3. If neither exists, the run is `INVALID:MISSING_DECISION`.

Runner-backed traces now populate `trace.messages`, so the JSON fallback works
in both runner and A2A paths.

---

## Event Flags

Event flags are computed separately from pass/fail using
[`src/pi_bench/event_flags/__init__.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/event_flags/__init__.py).

They summarize benchmark behavior such as:

- `V_r`
- `UR_r`
- `OR_r`
- `EA_r`
- `AT_r`

They are useful for leaderboard slicing, but they are not a substitute for the
full deterministic outcome checks.

---

## Scenario Validation Today

The live validator is
[`src/pi_bench/evaluator/scenario_validator.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/scenario_validator.py).

It currently checks:

- valid label
- non-empty `reward_basis`
- required check arrays for enabled evaluators
- exactly one `decision_equals`
- `decision_equals` matches the scenario label
- `tool_called_with` has non-empty arguments
- `tool_called_min_times` has `min_times >= 1`
- `state_field` checks have valid `field_path` / `equals`
- conflicting required-vs-forbidden tool checks
- orphaned ordering checks
- conflicting duplicate state-field assertions
- basic `reference_trajectory` structure when present

`reference_trajectory` is validation-only. It is not part of runtime scoring.

---

## What This Document Does Not Claim

This document does **not** claim that the current evaluator already has full
SOPBench-style procedural-oracle parity.

Current code has:

- deterministic tool and state checks
- semantic side-channel judging
- dimension reporting
- scenario validation

Planned upgrades such as richer procedural validation, deeper generated
coverage, and stricter parity claims live in the spec and roadmap docs linked
at the top.
