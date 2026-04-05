# Helpdesk Admin-Reset Gap Note

Date: 2026-03-21

Scope: compare the generated admin-reset helpdesk scenarios against the authored
helpdesk corpus in `workspace/scenarios/helpdesk/` and capture what the
generator must match before the output is repo-ready.

## What the authored helpdesk corpus already does

The authored helpdesk set is not a thin prompt collection. It is a structured
benchmark corpus with:

- full metadata envelopes (`schema_version`, `meta`, `leaderboard`, `label`,
  `decision_contract`, `policy_context`, `environment_setup`,
  `user_simulation`, `ablation_hints`, `evidence_pointer_contract`,
  `evaluation_criteria`)
- explicit `leaderboard.primary` plus `subskills[]` and `stressors[]`
- a realistic user narrative with pressure script, not just a single request
- dense checks, usually in the 16-25 total-check range
- both hard policy checks and semantic checks where the scenario depends on
  disclosure, wording, or justification quality
- environment patches that line up with the policy and the tool surface

The lightest authored helpdesk scenario is still `SCEN_047_ADMIN_RESET_FULL_PROCEDURE`
at 16 total checks; the rest are denser.

## What the admin-reset generator must match

### 1. Metadata richness

The generated scenario should keep the full authored shape, not a minimal stub.
At minimum it should include:

- `meta.scenario_id`
- `meta.domain = helpdesk_access_control_v1`
- `meta.policy_pack`
- `meta.created_at`
- `meta.timezone`
- `meta.notes`
- `leaderboard.primary`
- `leaderboard.subskills[]`
- `leaderboard.stressors[]`
- `label`
- `decision_contract`
- `policy_context`
- `environment_setup`
- `user_simulation`
- `ablation_hints`
- `evidence_pointer_contract`
- `evaluation_criteria`

### 2. Leaderboard / subskills / stressors

The generator should not flatten helpdesk admin-reset into one generic
`Authorization` bucket. It should preserve the authored distinction between:

- `Procedural Compliance`
- `Authorization & Access Control`
- `Policy Activation`
- `Evidence Grounding`
- `Temporal / State Reasoning`
- `Privacy & Information Flow`

Stressors should be explicit, especially:

- `User Pressure`
- `Deadline / Urgency`
- `Long Trajectory`
- `Ambiguous Authority`

### 3. User narrative

The user story needs a real operational context:

- a plausible employee role
- a believable request that is not obviously malicious
- a hidden blocker that only becomes visible through policy or DB/tool checks
- pressure language that tempts the agent to skip the procedure

The generator should avoid “policy quiz” prompts. The user should sound like a
real internal requester, not a benchmark author.

### 4. Check depth

The generated scenario should have enough checks to force the full procedure:

- at least one `decision_equals`
- at least one permissibility check
- multiple outcome checks for the required tool sequence
- ordering checks where the policy requires sequencing
- semantic checks only when the scenario tests disclosure, justification, or
  wording quality

For admin-reset helpdesk content, repo-ready depth is usually closer to the
authored corpus than to the current generator baseline:

- call out the employee lookup
- verify identity
- check admin/privileged status
- check approval/ticket requirements
- escalate when approval is missing
- log the ticket
- record the decision

### 5. Environment consistency

The environment setup must align with the story and the tools:

- `policy_text_ref` must point at `domains/helpdesk/policy.md`
- `environment_setup` must match the employee and ticket story in the prompt
- `now` and `timezone` must make the lockout / urgency / after-hours logic
  consistent
- the patch should include the employee/account/approval state needed by the
  tools
- any approval reference in the story must be present in the environment or
  DB patch

### 6. Tool anchors for ordering checks

Authored helpdesk scenarios rely on explicit `tool_called` anchors so ordering
checks can validate cleanly. The generator should emit both:

- the argument-bearing `tool_called_with`
- the plain `tool_called` anchor for the same tool when sequencing matters

This is the main repo-readiness trap for generated scenarios: ordering checks
look fine in the JSON, but they fail dry-run unless the plain anchors exist.

## Repo-ready acceptance rule

Treat a generated admin-reset scenario as repo-ready only if it matches the
authored helpdesk corpus on:

- metadata completeness
- leaderboard / subskills / stressors
- narrative realism
- check depth
- environment consistency
- ordering anchors

If it is missing any of those, keep it in generator staging or strengthen it
before landing it under `workspace/scenarios/helpdesk/`.
