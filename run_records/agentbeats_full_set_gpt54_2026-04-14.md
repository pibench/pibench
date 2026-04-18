# AgentBeats Full-Set Run Record - GPT-5.4 / GPT-5.4

Recorded on: 2026-04-14

This records the successful AgentBeats leaderboard run submitted from the forked leaderboard workflow.

## Run Identity

| Field | Value |
|---|---|
| Submission | `jyotidasaiml-wq-20260414-162443` |
| Agent display name | `Policy-GPT` |
| AgentBeats purple agent ID | `019c16a1-a3f9-7073-8ead-b8fbba319880` |
| Agent model | `gpt-5.4` |
| User simulator model | `gpt-5.4` |
| Dataset scope | Full PI-Bench set |
| Scenario count | 71 |
| GitHub Actions run | https://github.com/jyotidasaiml-wq/pi-bench-leaderboard/actions/runs/24408005468 |
| Raw result file | `/Users/jyotiranjandas/Downloads/PiBench competition leaderboard/results/jyotidasaiml-wq-20260414-162443.json` |
| Provenance file | `/Users/jyotiranjandas/Downloads/PiBench competition leaderboard/submissions/jyotidasaiml-wq-20260414-162443.provenance.json` |

## Snapshot

| Area | Metric | Result |
|---|---|---:|
| Run health | Completed scenarios | 71 / 71 |
| Run health | Runtime errors | 0 |
| Overall | Overall public capability score | 82.6% |
| Overall | Full compliance | 33.8% (24 / 71) |
| Overall | Semantic score | 88.4% |
| Overall | Runtime | 3133.9s |
| Policy Understanding | Group score | 86.7% |
| Policy Execution | Group score | 81.4% |
| Policy Boundaries | Group score | 79.6% |
| Event flags | Violation rate | 63.4% |
| Event flags | Forbidden-attempt rate | 0.0% |
| Event flags | Under-refusal rate | 80.0% |
| Event flags | Over-refusal rate | 63.6% |
| Event flags | Escalation accuracy rate | 46.7% |

## Domain Full Compliance

| Domain | Passed | Total | Full Compliance |
|---|---:|---:|---:|
| FINRA | 12 | 26 | 46.2% |
| Helpdesk | 10 | 32 | 31.2% |
| Retail | 2 | 13 | 15.4% |

## Group Scores

| Group | Score |
|---|---:|
| Policy Understanding | 86.7% |
| Policy Execution | 81.4% |
| Policy Boundaries | 79.6% |

## Nine-Dimension Scores

| Dimension | Total | Strict Passed | Strict Rate | Score |
|---|---:|---:|---:|---:|
| Policy Activation | 14 | 5 | 35.7% | 88.1% |
| Policy Interpretation | 9 | 2 | 22.2% | 76.8% |
| Evidence Grounding | 8 | 6 | 75.0% | 95.1% |
| Procedural Compliance | 12 | 3 | 25.0% | 72.5% |
| Authorization & Access Control | 7 | 3 | 42.9% | 86.7% |
| Temporal / State Reasoning | 3 | 1 | 33.3% | 84.9% |
| Safety Boundary Enforcement | 3 | 0 | 0.0% | 73.7% |
| Privacy & Information Flow | 5 | 3 | 60.0% | 87.7% |
| Escalation / Abstention | 10 | 1 | 10.0% | 77.5% |

## Label Breakdown

| Expected Label | Passed | Total |
|---|---:|---:|
| DENY | 3 | 15 |
| ESCALATE | 19 | 45 |
| ALLOW | 2 | 11 |

## Image Provenance

| Component | Image Digest |
|---|---|
| Green agent | `ghcr.io/jyoti-ranjan-das845/pi-bench-green@sha256:86e2ff8a93a6e4fdd32b3975a88b015d5570005d6c8d8c297ee7efde208e46dd` |
| Purple agent | `ghcr.io/jyoti-ranjan-das845/gpt-oss-sg-120b@sha256:6d4ea95e3cbf8d346e8980cd4e4ee451bae2fa19f58f3307c4e9683b6a597fa6` |
| AgentBeats client | `ghcr.io/agentbeats/agentbeats-client@sha256:13dfe3ef4e583a80e7ce2fe3becd0ce3b879841368a7f4fa40b6ebbabeeb014e` |

## Notes

- The run completed the full 71-scenario set successfully.
- No runtime, protocol, validation, or infrastructure errors were recorded.
- `Overall` is the partial-credit public capability score.
- `Full compliance` is stricter: a scenario only counts when every hard Tier 1 check passes.
- `Semantic score` is the Tier 2 semantic/NL-judge diagnostic average across all 71 scenarios.
