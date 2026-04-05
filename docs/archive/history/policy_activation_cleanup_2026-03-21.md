# Policy Activation Cleanup

Date: 2026-03-21

This note records the tightening of the `Policy Activation` leaderboard column
so the benchmark does not get inflated by easy or misclassified scenarios.

## Final Definition

`Policy Activation` now means:

- the agent must catch a hidden, blocking, or scope-defining rule
- the user frames the task around the wrong variable or wrong policy branch
- the key failure is missing which rule actually governs the case

This column is **not** for:

- obvious threshold checks
- explicit prohibited-action lookups
- cases where the hard part is really procedure, safety, or justification

## Active Policy Activation Scenarios

The active benchmark now keeps these scenarios in `Policy Activation`:

- `SCEN_019_WIRE_VS_ACH_SPEED`
- `SCEN_025_MISLEADING_DESCRIPTION`
- `SCEN_040_FINAL_SALE_RESTOCKING_TRADEOFF`
- `SCEN_041_ACTIVATED_TABLET_HOLIDAY_WINDOW`

These all require the agent to reject the user's surface framing and identify
the hidden blocker or governing clause.

## Removed From Active Policy Activation

Two scenarios were retired from the active benchmark and moved to
`scenarios/archive/20260321_activation_cleanup/`:

- `SCEN_010_CTR_THRESHOLD_WIRE`
  - Too obvious as a primary activation test.
  - The main challenge is procedural follow-through after an explicit threshold.

- `SCEN_032_PROHIBITED_SOFTWARE_INSTALL`
  - Too obvious as a primary activation test.
  - The main challenge is boundary enforcement against an explicitly prohibited request.

## Reclassified

- `SCEN_029_WRONG_JUSTIFICATION`
  - moved from `Policy Activation` to `Evidence Grounding`
  - rationale: the hard part is grounding the denial in the correct clause and facts, not noticing that a rule exists

## Authoring Rule Going Forward

When deciding whether a scenario belongs in `Policy Activation`, ask:

1. Is the user's framing pointing the agent at the wrong policy branch?
2. Is there a hidden blocker, latent trigger, or scope-defining fact?
3. Would a competent agent fail mainly because it missed which rule governs the case?

If the answer is no, do not tag it as `Policy Activation`.
