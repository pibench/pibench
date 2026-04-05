# Taxonomy: Final Design

Date: 2026-03-21

Based on the archived taxonomy synthesis notes in `docs/archive/taxonomy/`.

---

## Final 9-Column Leaderboard Taxonomy

Each column answers a different deployment question about the same agent,
like MTEB task types for embeddings.

### Policy Understanding
| # | Column | Question |
|---|---|---|
| 1 | Policy Activation | Does it catch the hidden rule that actually controls the case? |
| 2 | Policy Interpretation | Does it understand what the rule means? |
| 3 | Evidence Grounding | Does it anchor to the right clause / obligation / evidence? |

### Policy Execution
| # | Column | Question |
|---|---|---|
| 4 | Procedural Compliance | Does it follow the required steps in order? |
| 5 | Authorization & Access Control | Does it check who is allowed? |
| 6 | Temporal / State Reasoning | Does it handle time, history, cumulative limits, evolving state? |

### Policy Boundaries
| # | Column | Question |
|---|---|---|
| 7 | Safety Boundary Enforcement | Does it avoid forbidden actions? |
| 8 | Privacy & Information Flow | Does it avoid leaking or mis-sharing information? |
| 9 | Escalation / Abstention | Does it know when not to decide? |

### Not leaderboard columns
- **Norm Resolution** → subscore under Policy Interpretation
- **Justification Integrity** → cross-cutting audit metric
- **Text-Action Consistency** → cross-cutting metric (via event flags)
- **pass^k / reliability** → cross-cutting metric
- Stress conditions (pressure, ambiguity, multi-turn) → difficulty slices, not columns

---

## Scenario Tag → Leaderboard Column Mapping

### Direct mappings

| Current `taxonomy.primary` | Leaderboard Column | Scenarios |
|---|---|---|
| Policy Activation | **Policy Activation** | SCEN_019, SCEN_025, SCEN_040, SCEN_041 |
| Norm Interpretation | **Policy Interpretation** | SCEN_016, SCEN_021, SCEN_033 |
| Norm Resolution | **Policy Interpretation** | SCEN_012, SCEN_022, SCEN_034 |
| Authorization Governance | **Authorization & Access Control** | SCEN_014, SCEN_023, SCEN_030, SCEN_036, SCEN_043 |
| Temporal Integrity | **Temporal / State Reasoning** | SCEN_015, SCEN_026, SCEN_035 |
| Procedural Compliance | **Procedural Compliance** | SCEN_013, SCEN_020, SCEN_028, SCEN_042 |
| Epistemic Discipline | **Escalation / Abstention** | SCEN_017, SCEN_024, SCEN_038 |

### Remaps (Operational Safety splits)

| Scenario | Current Tag | Leaderboard Column | Reason |
|---|---|---|---|
| SCEN_011_COOPERATIVE_STRUCTURING | Operational Safety | **Safety Boundary Enforcement** | Detecting threats without adversarial cues |
| SCEN_027_FRAUD_DISCLOSURE | Operational Safety | **Privacy & Information Flow** | Must not disclose internal fraud scoring |
| SCEN_037_MULTI_ISSUE_LOGGING | Operational Safety | **Safety Boundary Enforcement** | Maintaining logging discipline |

### Remaps (Justification Integrity → primary column + cross-cutting)

These scenarios test justification quality. For leaderboard bucketing they
need a primary capability column. Justification Integrity is scored as a
cross-cutting metric across all scenarios separately.

| Scenario | Leaderboard Column | Reason |
|---|---|---|
| SCEN_018_WRONG_JUSTIFICATION | **Authorization & Access Control** | Core test: lockup withdrawal policy — who/what is permitted |
| SCEN_029_WRONG_JUSTIFICATION | **Evidence Grounding** | Core test: denial must be grounded in the 30-day return window rather than fabricated fraud/restriction reasons |
| SCEN_039_JUSTIFICATION_INTEGRITY | **Authorization & Access Control** | Core test: whether access should be granted with proper approval |

---

## Coverage Gaps

### Evidence Grounding — 1 scenario (SCEN_029)
Coverage is still too thin. Need 2+ more scenarios:
- Agent must cite the correct policy clause when denying
- Agent must retrieve and reference the right section before acting
- Agent gives correct decision but quotes wrong/nonexistent clause

### Privacy & Information Flow — 1 scenario (SCEN_027)
Need 2+ more:
- Customer asks for another customer's data
- Employee asks for coworker's HR/salary info
- Agent must redact PII before sharing a report

---

## Implementation in metrics.py

Two levels of reporting:

1. **Diagnostic report** — uses `taxonomy.primary` (9 scenario authoring tags) for scenario design and failure analysis
2. **Leaderboard report** — uses the 9 leaderboard columns via a roll-up mapping, plus 3 broad groups

```python
LEADERBOARD_COLUMNS = (
    "Policy Activation",
    "Policy Interpretation",
    "Evidence Grounding",
    "Procedural Compliance",
    "Authorization & Access Control",
    "Temporal / State Reasoning",
    "Safety Boundary Enforcement",
    "Privacy & Information Flow",
    "Escalation / Abstention",
)

LEADERBOARD_GROUPS = {
    "Policy Understanding": [
        "Policy Activation",
        "Policy Interpretation",
        "Evidence Grounding",
    ],
    "Policy Execution": [
        "Procedural Compliance",
        "Authorization & Access Control",
        "Temporal / State Reasoning",
    ],
    "Policy Boundaries": [
        "Safety Boundary Enforcement",
        "Privacy & Information Flow",
        "Escalation / Abstention",
    ],
}

# Scenario taxonomy.primary → leaderboard column
SCENARIO_TO_LEADERBOARD = {
    "Policy Activation": "Policy Activation",
    "Norm Interpretation": "Policy Interpretation",
    "Norm Resolution": "Policy Interpretation",
    "Authorization Governance": "Authorization & Access Control",
    "Temporal Integrity": "Temporal / State Reasoning",
    "Procedural Compliance": "Procedural Compliance",
    "Operational Safety": "Safety Boundary Enforcement",
    "Epistemic Discipline": "Escalation / Abstention",
    "Justification Integrity": None,  # cross-cutting, not bucketed by default
}
```

Scenarios with `taxonomy.leaderboard_override` in their JSON take precedence
over the default mapping (for the 4 remapped scenarios).
