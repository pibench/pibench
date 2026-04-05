# Taxonomy Reconciliation Notes (2026-03-21)

This note reconciles the three different classification systems currently present in the repo and explains which one the active scenarios were actually authored against.

## 1. Verified Classification Systems

### 1.1 Scenario primary taxonomy: 9 categories

The active scenario JSONs use a 9-category primary taxonomy under `taxonomy.primary`.

This 9-category design is documented in the older benchmark authoring material:

- `backup/base_backup/scratchpad/scenario-contributor-guide.md`
- `backup/base_backup/scratchpad/matrix-and-metrics-reference.md`

Those docs define the following primary categories:

1. `Policy Activation`
2. `Norm Interpretation`
3. `Norm Resolution`
4. `Authorization Governance`
5. `Temporal Integrity`
6. `Procedural Compliance`
7. `Operational Safety`
8. `Epistemic Discipline`
9. `Justification Integrity`

The current active scenario set uses exactly these same nine names.

### 1.2 Capability axes: 6 axes

The scenario JSONs also carry `capability_axes[]`, which is a different classification system from `taxonomy.primary`.

This 6-axis design is documented in:

- `backup/base_backup/README.md`
- `backup/base_backup/src/pi_bench/metrics.py`

The six axes are:

1. `rule_application`
2. `pattern_detection`
3. `escalation_judgment`
4. `information_containment`
5. `justification_fidelity`
6. `framing_resistance`

This is a multi-label capability view, not a single primary scenario bucket.

### 1.3 Current `metrics.py`: 7 reporting tasks

The active `src/pi_bench/metrics.py` defines a third system:

1. `Policy Activation`
2. `Policy Interpretation`
3. `Procedural Compliance`
4. `Authorization & Access Control`
5. `Harm Avoidance`
6. `Privacy & Information Flow`
7. `Escalation Judgment`

This 7-task list does not match the 9-category scenario taxonomy, and it is also different from the older 6-axis `capability_axes[]` design.

## 2. What the Active Scenario Data Actually Uses

Active `taxonomy.primary` counts in `scenarios/*/scen_*.json`:

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

Important fact:

- none of the following `metrics.py`-only names appear as `taxonomy.primary` in the active scenarios:
  - `Policy Interpretation`
  - `Authorization & Access Control`
  - `Harm Avoidance`
  - `Privacy & Information Flow`
  - `Escalation Judgment`

This is also true in the backup scenario copies under `backup/base_backup/scenarios`.

## 3. Mismatch Classification

This is not a pure naming cleanup. The current 7-task metrics taxonomy is a lossy rewrite relative to the authored 9-category scenario taxonomy.

| Scenario taxonomy | Current `metrics.py` relation | Classification | Why |
|---|---|---|---|
| `Policy Activation` | `Policy Activation` | Exact match | Same concept |
| `Procedural Compliance` | `Procedural Compliance` | Exact match | Same concept |
| `Authorization Governance` | `Authorization & Access Control` | Likely rename | Same general idea: identity, permissions, authority |
| `Norm Interpretation` | `Policy Interpretation` | Merge candidate | `metrics.py` collapses ambiguity handling into one broader bucket |
| `Norm Resolution` | `Policy Interpretation` | Merge candidate | Conflicting-rule resolution is separate in authored taxonomy but folded into the same broader bucket in `metrics.py` |
| `Operational Safety` | `Harm Avoidance` and `Privacy & Information Flow` | Split/overlap | Authored category covers prohibited actions and prohibited disclosures together |
| `Epistemic Discipline` | `Escalation Judgment` | Partial overlap only | `Epistemic Discipline` is specifically about recognizing policy uncertainty or scope gaps, not all escalation behavior |
| `Temporal Integrity` | no clear equivalent | Missing category | Active scenarios test cross-account history, deadlines, cumulative patterns, and state tracking |
| `Justification Integrity` | no clear equivalent | Missing category | Active scenarios test right action with wrong reason |

## 4. Why This Is Not Just a Rename Problem

Three concrete facts make this more than a label mismatch:

1. `Norm Interpretation` and `Norm Resolution` are distinct in the authored matrix.
   - The older matrix treats "ambiguous rule meaning" and "conflicting rules" as different rows.
   - Current `metrics.py` combines both into `Policy Interpretation`.

2. `Operational Safety` is broader than either `Harm Avoidance` or `Privacy & Information Flow`.
   - Active scenarios in this bucket include both "do not take the prohibited action" and "do not reveal restricted information."
   - The current 7-task metrics split those concerns into two separate buckets, but the scenario authors did not.

3. `Temporal Integrity` and `Justification Integrity` are first-class authored categories with active scenarios.
   - They are not represented in the current 7-task metrics vocabulary at all.

## 5. Relationship to `capability_axes[]`

`capability_axes[]` is not a replacement for `taxonomy.primary`.

The active data uses them differently:

- `taxonomy.primary` is one main scenario family
- `taxonomy.secondary[]` gives additional authored context
- `capability_axes[]` is a lower-level multi-label decomposition

Examples:

- `Justification Integrity` scenarios are usually tagged with `justification_fidelity`
- `Temporal Integrity` scenarios often use `pattern_detection` or `framing_resistance`
- `Epistemic Discipline` scenarios usually use `escalation_judgment`

So the axes are cross-cutting capabilities, while the primary taxonomy is the top-level scenario classification.

## 6. Practical Conclusion

The repo currently contains:

1. a 9-category scenario taxonomy that the scenarios were actually written against
2. a 6-axis capability system used for multi-label tagging in scenario JSON
3. a later 7-task reporting taxonomy in `src/pi_bench/metrics.py` that does not line up cleanly with either of the above

The safest interpretation is:

- `taxonomy.primary` is the authored benchmark row label
- `capability_axes[]` is a secondary cross-cutting capability annotation
- the current `metrics.py` taxonomy is not the source of truth

## 7. Recommendation

If the goal is to make reporting faithful to the current benchmark data:

1. Treat the 9-category `taxonomy.primary` vocabulary as the canonical scenario taxonomy.
2. Keep `capability_axes[]` as a secondary breakdown, not the primary row label.
3. Do not rename scenario JSON categories to the current 7-task `metrics.py` names without an explicit migration decision.
4. If a 7-task public score is still desired, define it as an intentional derived mapping from the 9-category taxonomy instead of pretending the labels already match.
