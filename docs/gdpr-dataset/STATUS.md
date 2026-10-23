# Status (2026-10-23)

## Dataset

| Wave | Scenarios | Labels (A / D / E) | Authoring | Audit + fixes | Benchmark run |
|---|---|---|---|---|---|
| 1 | GDPR_W1_001-050 | 22 / 21 / 7 | done | done | neutral + stress |
| 2 | GDPR_W2_001-050 | 24 / 23 / 3 | done | done | neutral + stress |
| 3 | GDPR_W3_001-050 | 25 / 23 / 2 | done | done | neutral done; **stress 29/50** |
| 4 | GDPR_W4_001-031 written | | 001-031 done; **032-050 to write** | 001-020 done; **021-050 to audit** | not run |
| 5 | not planned | | | | |

181 scenario files, all valid (`python3 domains/gdpr/validate_scenarios.py`).
All 77 in-scope rules have at least one scenario. Goal: 250.

## Results so far

Agent claude-sonnet-4-5, simulated user claude-sonnet-5-5, judge
claude-haiku-5-5 (Tier-2 only), 3 pushbacks, concurrency 2, OmniGent
claude-sdk harness. Full table: `domains/gdpr/coverage/results/RUNS.md`.

| Wave | Neutral | Stress |
|---|---|---|
| 1 | 72% (36/50) | 62% (31/50) |
| 2 | 76% (38/50) | 74% (37/50) |
| 3 | 68% (34/50) | partial: 16/29 passed |

Wave 1 ran with pressure v1 (free-text pressure); from wave 2 on, pressure v2
(technique + levers). Wave 3 is the first run with the clarified breach
hand-off wording in `decision_values.md`.

## Next steps, in order

1. **Finish the wave-3 run** (resumes, keeps the 50 neutral and 29 stress
   episodes already done):
   `bash domains/gdpr/coverage/run_wave.sh 3 3 <concurrency>`
2. **Write GDPR_W4_032-050** from `domains/gdpr/coverage/waves/wave4_plan.json`
   (batches G2 rest: 032-036; G3: 037-043; G4: 044-050). 029-031 were written
   by the G2 author before it stopped; check them in the audit.
3. **Audit GDPR_W4_021-050** (2-3 auditors), write the accepted fixes into
   `waves/wave4_audit_fixes.md` (append a section for 021-050), fix, validate.
4. **Run wave 4.**
5. **Plan wave 5** (50 targets) from `waves/failures.md` (regenerated after
   the wave-3 and wave-4 runs) and the ledger; slightly harder, balance the
   thin primary columns; author, audit, fix, run. That reaches 250.
6. Deferred small fix: GDPR_W2_020 gets the conditional identity gate (see
   `waves/wave2_audit_fixes.md`, follow-ups).
