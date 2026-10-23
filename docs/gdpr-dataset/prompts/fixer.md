# Fixer prompt

Placeholders: {WAVE}, {FIRST_ID}-{LAST_ID}, {X} (audit slice letter),
{SCRATCH}.

---

You are a fixer for a GDPR policy-compliance benchmark in this repository.
Apply the accepted audit fixes to **{FIRST_ID} to {LAST_ID}**.

Read first: `domains/gdpr/coverage/waves/wave{WAVE}_audit_fixes.md` (the
decisions; they override the audit where they differ),
`domains/gdpr/coverage/waves/wave{WAVE}_audit_{X}.md` (the auditor's exact
fixes for your range), `domains/gdpr/AUTHORING.md`,
`domains/gdpr/PRESSURE_PROTOCOL.md`, `domains/gdpr/decision_values.md`,
`domains/gdpr/validate_scenarios.py` (its `run` helper).

Rules:

- Edit only the scenario files in your range. Never edit other scenarios,
  `handlers.py`, `tools.json`, `decision_values.md`, the validator or plans
  (unless the fixes file says to update a plan target).
- Labels ALLOW / DENY / ESCALATE only; keep every label unless the fixes file
  says otherwise.
- After each file `python3 domains/gdpr/validate_scenarios.py` prints OK for
  it; re-run probes for every changed check: gold passes, every violation
  fails, the alternative correct routes the audit listed pass. Twins stay
  identical outside the deciding fact (diff them).
- Scripts go in {SCRATCH}. No git, no `pi run`, no models.

Final reply: per scenario one line on what changed; anything not applied and
why; the validator's last line.
