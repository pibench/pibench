# GDPR dataset pipeline

How the GDPR scenario set for pi-bench is built, checked, run and grown: a
loop of planned waves of 50 scenarios, each authored, validated, audited,
fixed, benchmarked, and mined for failures that seed the next wave.

- Current state and next steps: [STATUS.md](STATUS.md)
- Prompts for the agents that run each step: [prompts/](prompts/)
- Goal: 250 scenarios (5 waves); labels ALLOW / DENY / ESCALATE only.

```
        ┌──────────────────────────────────────────────────────────────┐
        ▼                                                              │
  1 PLAN ──► 2 AUTHOR ──► 3 VALIDATE ──► 4 AUDIT ──► 5 FIX ──► 3 VALIDATE
  (ledger,    (one JSON     (gold passes,  (independent  (apply accepted   │
   failures,   per target,   violations     agents probe   fixes)           │
   archive)    probes)       fail)          the env)                        ▼
                                                              6 RUN neutral + stress
                                                                            │
  8 ANALYSE ◄── 7 RECORD (RUNS.md, runs.json, report, ledger) ◄─────────────┘
  (failures.md → exploit targets of the next wave)
```

## 1. Setting up a machine

```bash
pip install -e .                        # pi-bench (Python 3.11+)
uv tool install omnigent                # OmniGent (the `omnigent` package): runs agent, user simulator and judge on Claude
claude auth status                      # must say "loggedIn": true (Claude subscription)
python3 -m pytest -q tests              # 664 passed, 10 skipped at the time of writing
python3 domains/gdpr/validate_scenarios.py   # every scenario prints OK
```

| Setting | Default | Change with |
|---|---|---|
| Agent under test | `claude-sonnet-4-5` | `src/pi_bench/omnigent/__init__.py` (`DEFAULT_AGENT_MODEL`) |
| Simulated user | `claude-sonnet-5-5` | same file (`DEFAULT_USER_MODEL`) |
| LLM judge (Tier-2 only) | `omnigent:claude-haiku-5-5` | env `PI_BENCH_JUDGE_MODEL` (any litellm name, or `omnigent:<model>`) |
| OmniGent interpreter | found from the `omnigent` CLI | env `PI_BENCH_OMNIGENT_PYTHON` |

Every OmniGent session (agent, user, judge) is a full Claude process of about
350 MB. On an 8 GB laptop use concurrency 2 and at most 2 helper agents; on a
larger machine raise both (rough budget: 3 processes × 350 MB per parallel
episode).

**Never name a shell variable `USER` or `HOME` in run scripts.** The Claude
CLI finds its login in the macOS Keychain by `$USER`; overwriting it makes
every episode fail at once with "Not logged in · Please run /login".

## 2. The search space

### Rules: the ontology

`domains/gdpr/ontology/` holds a graph of Regulation (EU) 2016/679 (804 nodes:
articles, paragraphs, definitions, 91 rule units, conditions, exceptions,
actors, edges between rules). Browse it with
`python3 -m http.server 8642 --directory domains/gdpr/ontology` and open
http://localhost:8642/viewer/ (toggle "Show coverage" to see which rules the
dataset tests). `coverage/scope.json` marks 14 rules out of scope (they cannot
be tested in a single chat episode); **77 rules are in scope**.

`python3 domains/gdpr/coverage/rule_card.py <RULE-ID>` prints one rule's
conditions, exceptions, linked articles and the scenarios that cover it.

### The archive: MAP-Elites over (main rule × label)

The dataset is grown like a MAP-Elites archive. A **cell** is
(main rule, label), e.g. `DR-05 × DENY`. Each scenario fills one cell with
its main rule (`coverage.rules[0]`) and label. Extra **descriptors** keep the
set diverse inside a cell:

| Descriptor | Where it lives | Target |
|---|---|---|
| Pressure technique | `user_simulation.pressure.technique` | spread the 40 techniques evenly (3-4 uses each), one per scenario |
| Primary capability column | `leaderboard.primary` (9 columns, `src/pi_bench/metrics.py`) | fill the thin columns (Authorization, Safety, Privacy, Temporal, Evidence) |
| Difficulty mechanism | wave plan `difficulty` | at least one per new scenario (below) |
| Setting | country, sector, requester role | never repeat a setting for the same rule |

`python3 domains/gdpr/coverage/ledger.py` rebuilds the ledger
(`coverage/ledger.json`, `coverage/LEDGER.md`) from the scenario files and
the run results: per rule the scenarios, labels, conditions and exceptions
exercised, pass rates, and a ranked list of **next targets**:

| Kind | Meaning |
|---|---|
| `explore_uncovered_rule` | an in-scope rule with no scenario |
| `add_opposite_label` | a rule tested with one label only |
| `exercise_exception` | an exception or condition of a covered rule never exercised |
| `exploit_failure` | a scenario the agent failed: probe the same weakness elsewhere |
| `keep_as_control` | a passed scenario worth keeping as a control |
| `label_balance` | the label mix drifts |

### Explore and exploit

Each wave mixes:

- **Explore**: uncovered rules, opposite labels, unexercised exceptions, thin
  primary columns. Early waves were mostly explore.
- **Exploit**: take a failure from `coverage/waves/failures.md` (generated by
  `coverage/failures.py` from the runs) and write a *new* scenario that probes
  the same weakness in a different setting, sector, requester or tool route.
  Set `meta.derived_from` to the failing scenario. Prefer failures in both
  conditions (robust weaknesses) and stress-only failures (pressure
  sensitivity; keep the technique family). A **twin** (same setting, one
  deciding fact flipped, opposite label) sharpens a boundary.

### Difficulty (from wave 4 on)

New scenarios are slightly harder than the early ones, through legal
reasoning, never tricks. Each plan target names its mechanism(s):

| Tag | Mechanism |
|---|---|
| 2rec | the deciding fact needs two records combined |
| distr | a plausible distractor that looks deciding but is not |
| exc² | an exception to an exception |
| date | date or deadline arithmetic |
| partial | only part of the request is lawful |
| conflict | an internal instruction conflicts with the GDPR |
| false | a checkable false claim from the requester (deception techniques) |
| state | a recent state change decides it |
| act | refusing is not enough; the agent must also file or notify |

The label must still follow from the article text plus the facts in state,
defensible in two sentences.

### Balance targets per wave

About 45% ALLOW, 45% DENY, 10-20% ESCALATE (ESCALATE only where
`domains/gdpr/decision_values.md` compels a hand-off: processor → controller,
supervisory authority for prior consultation, DPO only when a data subject
asks for them). Most scenarios pressured; pure-ALLOW scenarios with nothing to
push against get `pressure: ""`.

## 3. Planning a wave

Output: `domains/gdpr/coverage/waves/wave<N>_plan.json` (copy the format of
`wave4_plan.json`). One target per scenario:

```json
{"id": "GDPR_W4_023", "slug": "breach_clock_runs_from_processor_notice", "batch": "G1",
 "mode": "exploit", "cell": ["SB-03", "DENY"], "label": "DENY", "rules": ["SB-03", "SB-04"],
 "construct": "...one sentence...", "deciding_fact": "...", "setting": "...", "trap": "...",
 "checks": "outcome: ...; procedure: ...", "pressure": {"technique": ["T25_framing"]},
 "twin_of": null, "derived_from": ["W1_032", "W1_031"], "difficulty": ["date", "distr", "act"],
 "failure_modes": ["FM.misses_trigger"], "primary": "Temporal / State Reasoning"}
```

Inputs: `ledger.json` next targets, `waves/failures.md`, `results/RUNS.md`,
earlier plans (no duplicate constructs), technique counts across all
scenarios. Batches of 7-8 targets, twins in the same batch. Prompt:
[prompts/planner.md](prompts/planner.md).

## 4. Authoring a scenario

The authoring contract is `domains/gdpr/AUTHORING.md` (read it fully; it
carries every lesson from the audits). Pressure follows
`domains/gdpr/PRESSURE_PROTOCOL.md`. Decision definitions the agent sees are
`domains/gdpr/decision_values.md`. Tools and their exact behaviour:
`domains/gdpr/tools.json`, `domains/gdpr/handlers.py`.

One file per target: `scenarios/gdpr/GDPR_W<wave>_0NN_<slug>.json`. In short:

- **What the agent sees**: policy text, `agent_role` (who it is, controller or
  processor, which channel, what it is responsible for; never the answer), the
  opening message, and tool results over `initial_state_patch`. The deciding
  fact lives in state and must be looked up.
- **What the simulated user sees**: `persona`, `known_facts`, `goal` (what the
  person wants, with an acceptance condition that works whatever the agent
  decides), `rules`, `initial_user_message`, `pressure`
  (`{"technique": [id], "levers": [1-5 items from the persona's world]}`).
  The harness adds the technique card, the pushback contract (`--pushbacks
  N`) and guardrails.
- **Checks** (`evaluation_criteria`): exactly one `decision_equals`; Tier-1
  policy and state checks gate the pass (only what the policy requires, every
  valid route accepted, other languages accepted); Tier-2 judge questions for
  communication duties.
- **`validation`**: a `gold` trajectory that passes and `violations`, each with
  the Tier-1 checks it must fail (`must_fail`).
- **`coverage`**: construct, rules (main first), conditions, exceptions,
  failure modes, `derived_from`, twins.

### Scenario scripts: how authors build and probe

Authors do not hand-edit JSON. For each scenario they write a small generator
script (Python dict → JSON file) and a probe script, in a scratch folder
outside the repo, and iterate:

```python
import sys; sys.path[:0] = ["domains/gdpr", "src"]
from pathlib import Path
from validate_scenarios import run, failed_ids, check

path = Path("scenarios/gdpr/GDPR_W4_023_breach_clock_runs_from_processor_notice.json")
print(check(path))                     # schema, gold, violations, lint: [] when fine

route = {"calls": [                    # an alternative correct route
    {"tool": "get_breach", "args": {"breach_id": "INC-AK-2026-019"}},
    {"tool": "notify_supervisory_authority", "args": {"breach_id": "INC-AK-2026-019", "summary": "..."}},
    {"tool": "record_decision", "args": {"decision": "DENY", "rationale": "..."}}],
  "messages": ["Den Vorfall kann ich nicht als verjährt schließen ..."]}
print(failed_ids(run(path, route)))    # Tier-1 checks this route fails (want: none)
```

Every scenario is probed with the gold, every violation, and at least two
alternative correct routes (other tool order, the other verification tool,
another language, harmless extra steps). Authors also render the stress
prompt the simulated user will get and read it:

```python
from pi_bench.users.pressure import render_pressure
print(render_pressure(scenario["user_simulation"]["pressure"]))
```

### Validation

```bash
python3 domains/gdpr/validate_scenarios.py                       # all files
python3 domains/gdpr/validate_scenarios.py scenarios/gdpr/GDPR_W4_023_*.json
```

It checks the schema, that the gold passes and each violation fails exactly
its `must_fail`, that labels match the plan, unknown tools, leaks (label words
or answers in user-facing fields or `agent_role`), structured pressure, and
that no two scenarios share a construct signature.

## 5. Auditing and fixing

After a wave is authored, **independent** agents audit it in slices (they did
not write it). Each auditor reads the scenario, runs its own trajectories
against the real environment and writes `waves/wave<N>_audit_<X>.md`: per
scenario a verdict (OK / minor / major / critical), evidence (what was run,
what happened) and an exact fix. The checklist:

1. Is the label the only defensible one (ESCALATE vs DENY for processors;
   ALLOW vs DENY where a lawful part of the request could be done)?
2. Is the deciding fact in state, reachable and not leaked?
3. Do alternative correct routes pass and violations fail? Over-specified or
   missing checks?
4. Does the pressure fit, with levers from the persona's world?
5. Is it distinct from earlier scenarios on the same rule (twins flip only
   the deciding fact)?
6. Are article citations and any real national law accurate?
7. Are dates, names and ids consistent and unique?

The orchestrator then writes `waves/wave<N>_audit_fixes.md`: which fixes are
accepted, decisions on open points, central changes (handlers, tools,
decision_values, AUTHORING) applied once, and constraints. Fixers apply them
per slice and re-probe. Prompts: [prompts/auditor.md](prompts/auditor.md),
[prompts/fixer.md](prompts/fixer.md).

Do not change `decision_values.md`, `tools.json` or `handlers.py` while a run
is in progress: both conditions of a wave must see the same text.

## 6. Running the benchmark

```bash
bash domains/gdpr/coverage/run_wave.sh <wave> [pushbacks=3] [concurrency=2]
```

For the wave's scenarios it runs the **neutral** condition (the user asks once
and accepts the first clear outcome), then **stress** (the user pushes back
up to N times with the scenario's technique and levers). Per condition it:

1. resumes: keeps episodes already completed in
   `results/wave<N>_<condition>.json` (and merges a leftover `.part` from an
   interrupted run), runs only the rest into a `.part`, then merges;
2. refuses to record a condition with more than 20% errored episodes;
3. records the run in `results/runs.json` and `results/RUNS.md`
   (`coverage/registry.py`): models, harness, pressure version, N,
   concurrency, dates, full compliance, by label, decision confusion, layers,
   unsafe successes, per technique;

and at the end writes `results/wave<N>_report.txt` (`coverage/report_run.py`),
gzips the save files (git keeps the `.json.gz`; the raw files are ignored),
rebuilds `waves/failures.md` and the ledger.

Pass `NOTES="..."` in the environment to attach a note to the registry entry.
A third condition, `repetition` (`pi run-domain gdpr ... --user-condition
repetition`), pushes back with plain repetition only; a technique's effect is
its failure rate minus that baseline at the same N.

Raw command for one scenario:

```bash
pi run-domain gdpr --agent omnigent --user omnigent --user-condition stress --pushbacks 3 \
  --concurrency 1 --task-ids GDPR_W4_023 --save-to /tmp/one.json
```

## 7. Orchestrating with agents

The steps are done by Claude Code subagents driven from one orchestrating
session. Roles, in order, with prompt templates in [prompts/](prompts/):

| Step | Agents | Writes |
|---|---|---|
| Plan | 1 planner | `waves/wave<N>_plan.json` |
| Author | one per batch of 7-8 targets | `scenarios/gdpr/GDPR_W<N>_*.json` |
| Audit | 2-3 auditors, slices of 10-17 | `waves/wave<N>_audit_<X>.md` |
| Decide | the orchestrator | `waves/wave<N>_audit_fixes.md`, central changes, AUTHORING lessons |
| Fix | one per audit slice | the scenario files of its slice |
| Run | `run_wave.sh` in the background | results, registry, report, failures, ledger |

Rules that kept quality up:

- Each agent edits only its own files and uses its own scratch folder; it never
  runs git, never edits handlers/tools/validator (those changes go through the
  orchestrator).
- Authors and auditors are different agents; fixers apply only accepted fixes.
- Every agent reports back: per file what it built or changed, doubts, and
  the validator's last line. The orchestrator checks the result before moving
  on.
- Plan the next wave's exploit half only after the current wave's run results
  exist.

## 8. Lessons the audits turned into rules

All are in `AUTHORING.md`; the most important:

- **Lawful part of the request**: if the agent can do a lawful version of
  what was asked (a corrected notice, an accurate log entry), that is ALLOW.
  DENY needs a request with no lawful part, stated in the opening.
- **Processor scenarios**: DENY only when the client controller's documented
  instructions already decide the request; otherwise forwarding to the
  controller is ESCALATE. A processor's 33(2) breach notice to its controller
  is ESCALATE; a controller's own notification to the authority or data
  subjects is not.
- **Checks**: accept every valid route and language; key no-disclosure checks
  on the recipient; test negation only next to the trigger word; require a
  term from the deciding record in hand-off summaries and pin the right
  controller; list every rendering in leak checks; evidence checks for DENY
  and ESCALATE; identity gates only where data goes to the chat or an address
  not on file.
- **Law**: verify any real national law before citing it and write it as the
  organisation's summary; fictional instruments get no real-format numbers;
  check the country has no law that changes the answer.
- **Switch-on requests** state the activity's `go_live_effect`.

## 9. File map

| Path | What |
|---|---|
| `scenarios/gdpr/` | the scenarios |
| `domains/gdpr/policy.md`, `policy_articles.md` | the GDPR text the agent sees |
| `domains/gdpr/tools.json`, `handlers.py`, `db.json` | tools and their behaviour |
| `domains/gdpr/decision_values.md` | ALLOW / DENY / ESCALATE as given to the agent |
| `domains/gdpr/AUTHORING.md` | authoring contract |
| `domains/gdpr/PRESSURE_PROTOCOL.md` | pressure specification |
| `src/pi_bench/users/pressure_techniques.json`, `pressure.py` | 40 persuasion techniques (Zeng et al., ACL 2024) + repetition baseline; prompt rendering |
| `domains/gdpr/validate_scenarios.py` | validator and probe helper |
| `domains/gdpr/ontology/` | rule graph and viewer |
| `domains/gdpr/coverage/` | `ledger.py`, `rule_card.py`, `scope.json`, `failures.py`, `registry.py`, `report_run.py`, `run_wave.sh`, `resume.py`, `results_io.py` |
| `domains/gdpr/coverage/waves/` | plans, audits, accepted fixes, failures |
| `domains/gdpr/coverage/results/` | `RUNS.md`, `runs.json`, reports, compressed save files |
