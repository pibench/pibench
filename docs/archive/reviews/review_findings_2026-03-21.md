# Review Findings — 2026-03-21

This document consolidates the current findings from the code review, scenario-field inventory, and taxonomy/reporting review.

It is meant to be the current working ledger. Older notes such as [`LAYER3_AUDIT_STATUS.md`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/LAYER3_AUDIT_STATUS.md) are still useful context, but this file reflects the current code and current scenario set.

Related reference:

- [`scenario_field_inventory.md`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/scenario_field_inventory.md)

## High-Level Picture

The runtime pipeline itself is straightforward:

1. Load a scenario JSON into task text, environment state, and user-simulation config.
2. Run the orchestrator loop: agent message -> optional tool calls -> environment execution -> user reply -> repeat.
3. Evaluate the finished trajectory and trace against deterministic checks declared in `evaluation_criteria`.
4. Emit pass/fail style results and optional aggregate metrics.

The confusion is not that there are two separate pipelines. The confusion is that the scenario JSONs contain both:

- runtime fields that really drive execution and scoring
- richer analysis metadata intended for reporting and capability breakdowns

The runtime path is mostly working. The reporting/categorization path is only partially wired.

## 1. Runtime Correctness Findings

### 1.1 `load_domain()` drops scenario-specific environment state

Files:

- [`src/pi_bench/scenario_loader.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/scenario_loader.py)
- [`src/pi_bench/runner/core.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/runner/core.py)

Problem:

- `load()` correctly builds a per-scenario environment using `environment_setup.initial_state_patch`, plus `employee` and `now`.
- `load_domain()` only preserves the task objects, then rebuilds a generic environment from the domain defaults.
- `run_domain()` calls `domain["get_environment"]()` for every task, so local domain runs do not actually use each scenario's seeded environment state.

Impact:

- Local multi-scenario runs can execute against the wrong DB state.
- This is a correctness issue, not just a reporting issue.

### 1.2 Parallel trials share mutable protocol instances

Files:

- [`src/pi_bench/runner/core.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/runner/core.py)
- [`src/pi_bench/agents/litellm_agent.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/agents/litellm_agent.py)
- [`src/pi_bench/a2a/purple_adapter.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/a2a/purple_adapter.py)
- [`src/pi_bench/users/user.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/users/user.py)

Problem:

- `run_domain()` submits the same `agent` and `user` objects to every thread.
- The current implementations store mutable per-run state on `self` such as seed values, A2A task IDs, A2A context IDs, and an HTTP client that `stop()` closes.

Impact:

- `max_concurrency > 1` is unsafe.
- Trials can cross-contaminate each other or fail nondeterministically.

### 1.3 `NL_JUDGE` is treated as a hard pass/fail gate

Files:

- [`src/pi_bench/evaluator/__init__.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/__init__.py)
- [`src/pi_bench/evaluator/nl_assertion.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/nl_assertion.py)

Problem:

- The evaluator intends `NL_JUDGE` to be tier-2 only: it should affect `semantic_score`, not `all_passed`.
- But `evaluate_nl_judge_checks()` emits `type="nl_assertion_llm_judge"` instead of `type="NL_JUDGE"`.

Impact:

- `NL_JUDGE` failures can incorrectly affect binary reward.
- `semantic_score` can stay `1.0` even when the semantic judge failed.

### 1.4 `multi_tool` resume logic is broken

File:

- [`src/pi_bench/orchestrator/core.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/orchestrator/core.py)

Problems:

- `_filter_history()` computes per-requestor subsets of a `multi_tool` wrapper, but appends the original wrapper instead of a filtered one.
- `_role_from_message()` looks for top-level `requestor`, which `multi_tool` wrappers do not have.

Impact:

- Resume can route control to the wrong side.
- Resume can also expose tool results to the wrong participant.

### 1.5 User simulators restart from turn 0 on resume

Files:

- [`src/pi_bench/users/user.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/users/user.py)
- [`src/pi_bench/users/scripted_user.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/users/scripted_user.py)

Problem:

- `message_history` is accepted but not used to derive current turn count or script position.

Impact:

- Resumed conversations diverge immediately because the user repeats the opening message or restarts the pressure script.

### 1.6 A2A DB evaluation replays on mutated live state

Files:

- [`src/pi_bench/a2a/assessment.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/a2a/assessment.py)
- [`src/pi_bench/evaluator/db.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/evaluator/db.py)

Problem:

- The A2A path passes `{"get_environment": lambda: env}` into `evaluate()`.
- `evaluate_db()` assumes `get_environment()` returns a fresh environment, then replays tool calls onto it.

Impact:

- DB-scored A2A runs can double-apply mutations and produce false results.

### 1.7 Secondary runtime risks

These are smaller than the findings above but still worth keeping on the ledger:

- The normal runner attaches a trace but does not add conversation messages to it, so JSON-decision fallback only really works in the A2A path.
- `policy._check_escalation_after_block()` depends on matching the blocked tool name inside tool-result content, which the hard-gate error message does not include.

## 2. Scenario Schema Findings

The active scenario set has 34 files and every active file shares the same 12 top-level keys:

- `schema_version`
- `meta`
- `taxonomy`
- `label`
- `decision_contract`
- `policy_context`
- `environment_setup`
- `user_simulation`
- `ablation_hints`
- `evidence_pointer_contract`
- `capability_axes`
- `evaluation_criteria`

The detailed field-by-field inventory is in [`scenario_field_inventory.md`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/scenario_field_inventory.md). The main conclusions are below.

### 2.1 Fields that actively drive runtime behavior

These are the fields that the current pipeline really depends on:

- `schema_version`
- `meta.scenario_id`
- `meta.domain`
- `meta.notes`
- `label`
- `policy_context.policy_text_ref`
- `policy_context.policy_clauses[]`
- `environment_setup.now`
- `environment_setup.employee` for helpdesk scenarios
- `environment_setup.initial_state_patch`
- `user_simulation.*`
- `evaluation_criteria.*`

### 2.2 Fields that are present everywhere but not read

These currently look like authoring or analysis metadata rather than runtime contract:

- `decision_contract.*`
- `ablation_hints.*`
- `evidence_pointer_contract.*`
- `capability_axes[]`
- `meta.policy_pack`
- `meta.created_at`
- `meta.timezone`
- rebuild-only `meta.mismatch_type`
- rebuild-only `meta.previous_version`
- rebuild-only `meta.rebuild_reason`

### 2.3 Wrapper-level inconsistencies in `environment_setup`

These fields exist in scenario JSON but are not consistently carried through the active loader path:

- `environment_setup.customer`
- `environment_setup.account`
- `environment_setup.agent_role`
- `environment_setup.agent`

Current behavior:

- `scenario_loader.load()` only copies `employee` and `now` out of `environment_setup` into the environment DB.
- `customer`, `account`, `agent_role`, and `agent` are effectively ignored in the active path.

### 2.4 `initial_state_patch` is really domain fixture data

This is the most important schema boundary decision:

- `environment_setup.initial_state_patch` is not a single benchmark-wide schema.
- It is domain-specific environment state that tools read and mutate.

That means the clean schema split is:

1. benchmark-core scenario schema
2. optional analysis metadata
3. per-domain fixture schema for `initial_state_patch`

Notable currently unused patch sections:

- FINRA: `dual_authorization`
- Retail: `product_warranty`, `return_history_last_90_days`
- Helpdesk: `approval_tickets`, `business_hours`, `database_access`, `device_inventory`, `hr_remote_work_policy`, `it_security_on_call`, `printer_access`, `requested_resource`, `shared_drives`, `software_catalog.*`, `admin_dashboard`, `byod_policy`, `personal_device_procedures`

### 2.5 Data/code mismatches inside domain fixtures

The clearest concrete mismatch is in helpdesk:

- active scenario data uses `software_catalog.prohibited_categories` and `software_catalog.prohibited_examples`
- the active `install_software` handler checks `db["prohibited_software"]`

So even within `initial_state_patch`, some current fields do not line up with current tool logic.

## 3. Reporting, Taxonomy, and Capability Breakdown Findings

### 3.1 The flat benchmark score works

The simple score is just:

- run scenarios
- count how many passed

That part is straightforward.

### 3.2 The capability breakdown is only partially wired

The intended richer report is:

- take the same scenario results
- group them by capability category
- show where a model is strong or weak

The current gap is:

- scenario files carry category metadata
- the active runtime does not propagate that metadata into result objects
- the metrics layer expects taxonomy fields that are not currently attached

### 3.3 `taxonomy.*` and `capability_axes[]` are dead data in the active runtime

Files:

- [`src/pi_bench/scenario_loader.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/scenario_loader.py)
- [`src/pi_bench/runner/core.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/runner/core.py)
- [`src/pi_bench/metrics.py`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/src/pi_bench/metrics.py)

Current state:

- `scenario_loader.py` does not put `taxonomy` or `capability_axes` into the task dict.
- `run_domain()` does not attach them to per-simulation results.
- `metrics.py` expects `taxonomy_primary` in result dicts, but nothing populates it.
- `capability_axes[]` is not read at all.

### 3.4 This is not just a missing field copy

There are two separate issues:

1. Wiring gap
   - category metadata is not propagated into results

2. Vocabulary mismatch
   - the scenario taxonomy labels do not match the labels defined in `metrics.py`

There is also verified taxonomy drift in the repo history:

- the active scenarios were authored against a 9-category primary taxonomy
- the scenario JSONs also carry a separate 6-axis `capability_axes[]` system
- the current `src/pi_bench/metrics.py` introduces a third, different 7-task reporting vocabulary

See:

- [`docs/taxonomy_reconciliation_2026-03-21.md`](/Users/dzen/Spaces/projects/lab/agentbeats/workspace/docs/taxonomy_reconciliation_2026-03-21.md)

### 3.5 Current active scenario taxonomy values

Active `taxonomy.primary` values in the current 34-scenario set:

| Category | Count |
|---|---:|
| `Policy Activation` | 6 |
| `Authorization Governance` | 6 |
| `Procedural Compliance` | 4 |
| `Operational Safety` | 3 |
| `Norm Resolution` | 3 |
| `Temporal Integrity` | 3 |
| `Norm Interpretation` | 3 |
| `Epistemic Discipline` | 3 |
| `Justification Integrity` | 3 |

This exactly matches the older 9-category scenario matrix documented in:

- `backup/base_backup/scratchpad/scenario-contributor-guide.md`
- `backup/base_backup/scratchpad/matrix-and-metrics-reference.md`

### 3.6 Current `metrics.py` taxonomy values

`metrics.py` currently defines these seven reporting tasks:

- `Policy Activation`
- `Policy Interpretation`
- `Procedural Compliance`
- `Authorization & Access Control`
- `Harm Avoidance`
- `Privacy & Information Flow`
- `Escalation Judgment`

### 3.7 What matches and what does not

| Scenario taxonomy | Current `metrics.py` relation | Classification |
|---|---|---|
| `Policy Activation` | `Policy Activation` | Exact match |
| `Procedural Compliance` | `Procedural Compliance` | Exact match |
| `Authorization Governance` | `Authorization & Access Control` | Likely rename |
| `Norm Interpretation` | `Policy Interpretation` | Merge candidate |
| `Norm Resolution` | `Policy Interpretation` | Merge candidate |
| `Operational Safety` | `Harm Avoidance` and `Privacy & Information Flow` | Split/overlap |
| `Epistemic Discipline` | `Escalation Judgment` | Partial overlap only |
| `Temporal Integrity` | none | Missing category |
| `Justification Integrity` | none | Missing category |

Additional verified points:

- none of these `metrics.py`-only names appear as `taxonomy.primary` in the active scenarios or the backup scenario set:
  - `Policy Interpretation`
  - `Authorization & Access Control`
  - `Harm Avoidance`
  - `Privacy & Information Flow`
  - `Escalation Judgment`
- this means the current mismatch is not safely describable as "just rename the labels"
- the active scenario data was not authored against the current 7-task `metrics.py` vocabulary

### 3.8 `capability_axes[]` is a second categorization system

Observed active `capability_axes` values:

- `rule_application`
- `pattern_detection`
- `escalation_judgment`
- `information_containment`
- `justification_fidelity`
- `framing_resistance`

This is a different style of categorization from `taxonomy.primary`:

- `taxonomy.primary` is one primary bucket per scenario
- `capability_axes[]` is multi-label and lower-level

So the codebase currently has two classification schemes in the scenario files:

1. `taxonomy.primary` / `taxonomy.secondary`
2. `capability_axes[]`

Neither is fully wired into current reporting.

Important historical clarification:

- the older backup `metrics.py` used `capability_axes[]` as its primary scoring vocabulary
- the current `metrics.py` no longer does that
- so the repo has drifted through at least two different reporting designs

### 3.9 Current recommendation on reporting source of truth

Based on the active scenario data and the older authoring docs:

- `taxonomy.primary` should be treated as the canonical top-level scenario taxonomy
- `capability_axes[]` should be treated as a secondary, cross-cutting capability annotation
- the current 7-task `metrics.py` taxonomy should not be treated as canonical without an explicit migration decision

## 4. Decision Points Before Cleanup

Before removing or renaming fields, these choices need to be explicit:

### 4.1 Choose the reporting source of truth

Pick one:

- `taxonomy.primary` as the main capability breakdown
- `capability_axes[]` as the main capability breakdown
- both, but with different purposes

Current evidence supports:

- `taxonomy.primary` for the benchmark row/task breakdown
- `capability_axes[]` for a secondary cross-cutting capability view

### 4.2 Choose the canonical vocabulary

If `taxonomy.primary` stays:

- either keep the current 9-category scenario vocabulary and rewrite `metrics.py` around it
- or define an explicit derived mapping from the 9-category taxonomy to a smaller public reporting vocabulary

What should not happen implicitly:

- silently treating the current 7-task `metrics.py` labels as if they already match the scenario taxonomy
- renaming scenario categories without deciding what information loss is acceptable

### 4.3 Separate benchmark schema from domain fixture schema

Keep these separate in docs and validation:

- benchmark-core scenario fields
- optional authoring / analysis metadata
- per-domain DB seed fields under `initial_state_patch`

### 4.4 Decide what to do with dormant metadata

Candidates for removal or explicit "authoring-only" status:

- `decision_contract.*`
- `ablation_hints.*`
- `evidence_pointer_contract.*`
- `capability_axes[]` if not adopted
- rebuild-only `meta.*` fields

## 5. Recommended Next Steps

1. Fix the six runtime correctness issues first.
2. Decide whether `taxonomy.primary`, `capability_axes[]`, or both should drive reporting.
3. Freeze a canonical category vocabulary.
4. Wire the chosen category fields through loader -> task -> simulation result -> metrics.
5. Split the scenario schema into:
   - benchmark-core schema
   - authoring metadata schema
   - per-domain `initial_state_patch` schemas
6. Remove or formally deprecate unused fields after the wiring decision is made.
