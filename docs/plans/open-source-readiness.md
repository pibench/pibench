# Plan: Open Source Readiness

## Standard

HarmBench-level quality. Every file reviewed. Clean public API. Works
out of the box. No internal references, no stale code, no dead paths.

## Current state

- 38 scenarios, average 7.3 checks (35 below target of 10+)
- 49 source files, 7298 lines
- Observability is bolt-on (separate directory, --observe flag)
- Pipeline works end-to-end (tested with Haiku and gpt-4o)
- 9-column leaderboard with 3 groups, dimensional failure reports

## What must be done before open source

### Phase 1: Core quality (must-have)

**1.1 Deepen all scenarios to 10-15+ checks**
- 35 scenarios need deepening (plan at docs/plans/deepen-scenarios.md)
- Each scenario: dry-run validate → test Haiku → if Haiku passes 10/10, discard
- Handoff to separate session with the deepening plan
- Estimate: 2-3 sessions

**1.2 Clean up the codebase for public consumption**
- Remove all absolute path references (grep for /Users/dzen)
- Remove all hardcoded API keys (already done for run_mismatch_10x.py, verify no others)
- Remove backup/ and archive/ from the repo (or .gitignore them)
- Remove __pycache__ from tracking
- Add .gitignore for .env, __pycache__, .venv, .gitnexus
- Review every import — no circular deps, no dead imports
- Review every public function — docstrings, type hints
- Remove dead code paths (unused functions, unreachable branches)

**1.3 Tests**
- Verify existing tests pass with the mock domain fix
- Add tests for:
  - scenario_loader.load() + load_domain()
  - evaluator dimension classification
  - generator produces valid scenarios
  - deterministic tool execution (same inputs → same outputs)
  - environment isolation (mutating one env doesn't affect another)
- Target: 80%+ coverage on evaluator, runner, scenario_loader

**1.4 Documentation**
- README.md — already good, verify accuracy after all changes
- docs/scenario-schema.md — already good, verify field list is complete
- CONTRIBUTING.md — how to write scenarios, how to run tests
- LICENSE — pick license (Apache 2.0 or MIT)
- CHANGELOG.md — what's in this release

**1.5 CLI polish**
- `pi run` — works, tested
- `pi run-domain` — works, tested
- `pi list` — works
- Add `pi validate` — dry-run all scenarios, report issues
- Add `--mode minimal` — run 1 scenario per column (9 total)
- Verify `pip install -e .` works cleanly
- Verify `pi --help` is clear

### Phase 2: Observability (nice-to-have, bolt-on)

This is separate from the core package. Users who don't want observability
never see it. Users who do get a one-command setup.

**2.1 Structure**
```
pi-bench/
├── src/pi_bench/           # Core benchmark (no observability dependency)
│   ├── evaluator/
│   ├── runner/
│   ├── orchestrator/
│   ├── generator/
│   └── ...
├── observability/          # Bolt-on (separate directory, not in pip install)
│   ├── docker-compose.yml
│   ├── config/
│   ├── dashboards/
│   └── README.md
├── src/pi_bench/observability/  # Emitter (optional, in package)
│   ├── __init__.py
│   └── emitter.py
├── scenarios/
├── domains/
├── scripts/
├── tests/
├── docs/
├── README.md
├── pyproject.toml
└── LICENSE
```

The emitter module (`src/pi_bench/observability/`) is in the package
but has zero effect unless `--observe` is passed. It fails silently if
the stack isn't running. The infrastructure (`observability/`) is a
separate directory with its own README.

**2.2 Observability deliverables**
- docker-compose.yml — Loki, Tempo, Mimir, Grafana (DONE)
- Config files for all services (DONE)
- Emitter that pushes structured JSON to Loki (DONE)
- Grafana dashboard JSON — 4 dashboards (TODO):
  1. Live progress (episode completion, scenario status tiles)
  2. Leaderboard (9-column bar chart, 3-group summary)
  3. Failure analysis (dimension heatmap, most-failed scenarios)
  4. Trajectory explorer (trace drill-down)
- observability/README.md — setup instructions (TODO)
- `--observe` flag wired in CLI (DONE)

**2.3 Observability testing**
- Bring up stack locally
- Run a benchmark with --observe
- Verify events appear in Grafana
- Screenshot the dashboards for docs

### Phase 3: Scale (post-launch)

**3.1 Systematic generation**
- Define DAGs for all 3 domains' key procedures
- Generate 100+ scenarios (DAG-native columns only)
- Expert review before inclusion
- Add to extensive mode

**3.2 Additional domains**
- Healthcare, Legal, HR
- Same methodology, new tools/policies/scenarios

**3.3 Ablation suite**
- 7 diagnostic modes
- Requires scenario variants (structured policy, no pressure, etc.)

## Priority order

```
1. Scenario deepening (Phase 1.1)     ← handoff to separate session
2. Codebase cleanup (Phase 1.2)       ← can do in parallel
3. Tests (Phase 1.3)                  ← after cleanup
4. Docs (Phase 1.4)                   ← after cleanup
5. CLI polish (Phase 1.5)             ← after docs
6. Grafana dashboards (Phase 2.2)     ← can do in parallel
7. Observability testing (Phase 2.3)  ← after dashboards
8. Open source push                   ← after all Phase 1 + Phase 2 basics
```

Items 1 and 2 can run in parallel (different sessions).
Items 6 can run in parallel with 2-5.
Phase 3 is post-launch.

## What the open-source release looks like

```bash
# Install
pip install pi-bench

# Quick test (9 scenarios, ~5 min)
pi run-domain finra --agent-llm gpt-4o-mini --mode minimal

# Full benchmark (38+ scenarios, ~30 min)
pi run-domain finra --agent-llm gpt-4o

# With observability
cd observability && docker compose up -d
pi run-domain finra --agent-llm gpt-4o --observe
open http://localhost:3000

# List scenarios
pi list

# Validate all scenarios
pi validate
```

Output:
```
PI-BENCH RESULTS
======================================================================
  Compliance:  32.4%  (12/37 scenarios)
  Overall:     28.6%  (macro-avg across columns)

  Policy Understanding (33.3%)
  ------------------------------------------------------------------
    Policy Activation                    40.0%  (2/5)
    Policy Interpretation                28.6%  (2/7)
    Evidence Grounding                   33.3%  (1/3)
  ...

  Failure Modes (25/37 scenarios failed)
  ------------------------------------------------------------------
    Decision Correctness            60.0% checks passed  (15 scenarios failed)
    Action Permissibility           85.0% checks passed  (6 scenarios failed)
    Required Outcomes               45.0% checks passed  (20 scenarios failed)
    ...
```
