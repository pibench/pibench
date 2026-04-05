# Evaluation Rigor Spec

Date: 2026-03-21

Goal: Match or exceed SOPBench's evaluation rigor on every dimension
that applies to pi-bench scenarios, while keeping the broader policy
interpretation and pressure-resistance capabilities that SOPBench
doesn't have.

---

## Status

This document is a **roadmap and design target**, not a statement that every
item here is already implemented in code.

Current implemented behavior lives in
[docs/evaluation-reference.md](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/evaluation-reference.md).

| Area | Status |
|---|---|
| Deterministic tool/state evaluation | Current |
| Per-dimension reporting | Current, with limited current check vocabulary |
| Scenario consistency validation | Current, partial |
| Reference trajectory validation | Current, structural only |
| Systematic scenario generation as active benchmark input | Planned |
| Full SOPBench-style procedural-oracle parity | Planned |

## 1. What we already have (and SOPBench also has)

- Agent calls OUR tools in OUR environment — full trajectory control
- Deterministic tool execution — same inputs → same outputs (after the
  uuid/datetime fix)
- Trace recording of every tool call, argument, and result
- DB state verification via state_field_checks
- Tool call verification via policy_checks
- Ordering verification via tool_before_tool checks

The execution-control surface is equivalent: the agent has no tools we do not
control, and we can inspect the full trace. The remaining gap is in oracle
expressiveness and validation rigor, not basic runtime visibility.

## 2. What SOPBench has that we need to add

### 2.1 Scenario self-validation (pre-run oracle check)

**The problem:** If a scenario author writes a bad check (e.g., expects
DENY but the setup actually requires ALLOW), nothing catches it. The
scenario ships broken and produces wrong benchmark results.

**SOPBench's solution:** Every SOP exists in three synchronized forms
(natural language, action graph, executable oracle). Inconsistency
between any two is caught before testing.

**Our solution:**

Add a `scenario_validator` that, for each scenario:

1. Parses the evaluation_criteria checks
2. Verifies internal consistency:
   - If label is DENY and there's a `decision_equals: ALLOW`, that's a conflict
   - If there's a `tool_not_called: X` AND a `tool_called: X`, that's a conflict
   - If there's a `tool_before_tool: A, B` but no `tool_called: A` or `tool_called: B`, the ordering check is orphaned
   - If there's a `state_field` check but no tool that could produce that state change, the check may be unreachable
3. Optionally runs a **reference trajectory** (if provided in the scenario)
   through the environment and verifies that the checks pass against it

This catches scenario authoring errors before they reach the benchmark.

**Important: the reference trajectory is for scenario validation only —
it is NOT used to score the agent.** A smart agent that takes a completely
different path and achieves the same outcomes gets full credit. We verify
outcomes and constraints, not the specific route.

**Schema addition:** Optional `reference_trajectory` field in scenarios:
```json
"reference_trajectory": {
  "tool_sequence": ["read_policy", "lookup_order", "check_return_eligibility", "record_decision"],
  "expected_decision": "DENY",
  "expected_state_changes": {
    "activity.pending_requests[request_id=REQ_1].status": "denied"
  }
}
```

If present, the validator uses this ONLY to verify that:
- The scenario's evaluation_criteria checks are internally consistent
  (the happy path would actually pass all checks)
- The expected state changes are reachable from the initial state
- No checks contradict each other

This catches bad scenario authoring. It does NOT constrain how the agent
solves the scenario.

### 2.2 Multi-dimensional per-trajectory scoring

**The problem:** We collapse everything into one `all_passed` boolean.
A scenario that fails on action permissibility and one that fails on
DB outcome look the same in the report.

**SOPBench's solution:** Three independent scores per trajectory.

**Our solution:**

Break evaluation results into 4 dimensions (we have more than SOPBench):

| Dimension | What it checks | Source | Principle |
|---|---|---|---|
| **Decision correctness** | Did the agent make the right call? | `decision_equals` | Outcome — what verdict did it reach? |
| **Action permissibility** | Did it avoid forbidden actions? | `tool_not_called` + AT_r | Constraint — what must NOT happen? |
| **Required outcomes achieved** | Did the necessary things happen? | `tool_called`, `tool_called_with`, `tool_called_any`, `tool_called_min_times` | Outcome — what must happen, in any order? |
| **Temporal constraints honored** | Where order matters, was it respected? | `tool_before_tool` | Constraint — ONLY checked when the policy explicitly requires ordering |
| **State correctness** | Is the DB in the right state? | `state_field_checks` | Outcome — did the world end up right? |

Plus the existing tier-2:
| **Semantic quality** | Right reasoning/language? | `nl_judge_checks` (does not gate pass/fail) |

**Core principle: verify outcomes and constraints, not the specific route.**
A smart agent that takes a completely different path — skips unnecessary
lookups, reorders independent actions, finds a creative solution — gets
full credit as long as:
- The decision is correct
- Forbidden actions were avoided
- Required outcomes were achieved
- Temporal dependencies (where they exist) were honored
- The DB ended up in the right state

We do NOT force a fixed trajectory. `tool_before_tool` checks are used
sparingly and only when the policy explicitly requires ordering (e.g.,
"must verify identity before resetting password").

**Reporting change:**

Instead of just `all_passed: true/false`, the detailed report shows:

```
[FAIL] SCEN_010_CTR_THRESHOLD_WIRE
  Decision:      FAIL  (expected DENY, got ALLOW)
  Permissible:   PASS  (no forbidden tools called)
  Outcomes:      PASS  (queried activity, filed CTR)
  Ordering:      PASS  (no temporal constraints violated)
  State:         FAIL  (wire not held)
  Semantic:      PASS  (1/1 NL checks)
```

This tells you exactly WHERE the failure happened — the agent knew the
right procedure but made the wrong decision and didn't hold the wire.

**Implementation:**

In `evaluator/__init__.py`, split `outcome_results` into dimensions:
```python
{
    "all_passed": False,
    "dimensions": {
        "decision": {"passed": False, "checks": [...]},
        "permissibility": {"passed": True, "checks": [...]},
        "procedure": {"passed": True, "checks": [...]},
        "state": {"passed": False, "checks": [...]},
        "semantic": {"passed": True, "checks": [...]},
    },
    "reward": 0.0,
    "semantic_score": 1.0,
}
```

### 2.3 Systematic case generation (additive, not replacement)

**The problem:** 37 hand-authored scenarios. SOPBench has 903 generated.
Coverage depends on the scenario author's imagination.

**Our position:** Manual authoring with expert validation is the primary
method. We do NOT want to replace it with generation.

**What we will add:**

For **Procedural Compliance** scenarios specifically (where constraint
permutation is most valuable), add a generator that:

1. Takes a policy document and its tool schemas
2. Enumerates constraint combinations (e.g., "customer has loyalty tier X
   AND order is in category Y AND return window is Z")
3. For each combination, generates a scenario JSON with:
   - initial_state_patch reflecting those constraints
   - evaluation_criteria derived from the constraint analysis
   - user_simulation with a standard template
4. Validates each generated scenario against the oracle (section 2.1)
5. Flags scenarios for expert review before inclusion

This is additive — generated scenarios go into a `scenarios/generated/`
directory and are tagged with `"generation_method": "constraint_permutation"`.
Expert-authored scenarios remain the core benchmark.

**Priority:** Lower than 2.1 and 2.2. The first 37 expert scenarios are
more valuable than 900 generated ones without expert validation.

---

## 3. Implementation plan

### Phase 1: Multi-dimensional scoring (immediate)

Change evaluator to classify each check into a dimension and report per-dimension pass/fail. This is a reporting change — the underlying checks don't change.

Files: `evaluator/__init__.py`, `metrics.py`, `cli.py`

### Phase 2: Scenario self-validation (next)

Add a validator that checks scenario internal consistency and optionally
runs a reference trajectory. This catches authoring errors before they
reach the benchmark.

Files: `evaluator/scenario_validator.py` (extend existing), `scenario_loader.py`

### Phase 3: Detailed failure reports (with Phase 1)

Update the CLI and runner to produce per-scenario failure reports showing
exactly which dimension failed and what checks within it.

### Phase 4: Systematic generation (later)

Build a constraint-permutation generator for Procedural Compliance scenarios.
Tag outputs for expert review.

---

## 4. Why this beats SOPBench on their own terms

After these changes:

| Dimension | SOPBench | pi-bench |
|---|---|---|
| Executable environment | Yes | Yes (already) |
| Deterministic verification | Yes (3 axes) | Yes (4 axes + semantic) |
| Scenario validation | Yes (triple representation) | Yes (reference trajectory + consistency checks) |
| Trajectory evidence | Yes (903 released) | Planned (per-run traces saved) |
| Systematic generation | Yes (constraint permutation) | Planned (additive to expert authoring) |
| Policy interpretation | No (clear SOPs only) | Yes (ambiguous, conflicting, incomplete) |
| Pressure resistance | No (static inputs) | Yes (live user simulators) |
| Capability decomposition | No (one score) | Yes (9 columns, 3 groups) |
| Policy swapping | No (fixed per domain) | Yes (same domain, different policies) |

We match them on rigor and exceed them on scope.
