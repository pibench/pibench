# Layer 3 Audit Status

**Date:** 2026-03-22
**Branch:** `claude/review-branch-docs-Orhda`

---

## What was done (Layers 1-3 bug fixes)

### Fix 1: `**llm_args` collision in LiteLLMAgent and LiteLLMUser
- **Files:** `src/pi_bench/agents/litellm_agent.py`, `src/pi_bench/users/user.py`
- Reserved keys (`model`, `messages`, `seed`, `thinking`) stripped at init
- Spread reordered: `**llm_args` comes first, explicit keys overwrite
- Prevents silent model/message override from user-supplied kwargs

### Fix 2: `domain_dir.name` in `load_domain()`
- **File:** `src/pi_bench/scenario_loader.py`
- `get_environment()` now passes `domain_dir.name` (resolved canonical name) instead of raw `domain_name`

### Fix 3: Missing directory error in `load_domain()`
- **File:** `src/pi_bench/scenario_loader.py`
- Raises `FileNotFoundError` if `scenarios_dir` doesn't exist (was silently returning 0 tasks)

### Fix 4: Defensive task lookup in retry loop
- **File:** `src/pi_bench/runner/core.py`
- `next(t for t in tasks ...)` replaced with `next(..., None)` + `continue` to prevent `StopIteration`

### Fix 5: Docstring sync in seeds.py
- **File:** `src/pi_bench/runner/seeds.py`
- Docstring said `hexdigest()[:8]` but code uses `[:16]`. Fixed docstring.

### Fix 6: `observer_mode` in checkpoint metadata
- **File:** `src/pi_bench/runner/checkpoint.py`
- `make_info()` now accepts and saves `observer_mode` for reproducibility

### Fix 7: Renamed `domains/finance/` to `domains/finra/`
- Standardized on `finra` as the single domain name everywhere
- Removed `"finra": "finance"` alias from `_DOMAIN_ALIASES`
- Updated `domains/finra/__init__.py` line 363: `domain_name="finance"` -> `"finra"`
- Updated `tests/step_defs/test_domain_smoke.py`: assertion `"finance"` -> `"finra"`
- Updated docs (`SHARED_DB_PLAN.md`, `IMPLEMENTATION_GUIDE.md`) path references

### Test results after all fixes
- **74 core tests passed** (no regressions)
- **69 domain smoke tests passed** (all 12 finra scenarios)
- **143 total passing**, 10 skipped (expected: hooks/tau2 not implemented)
- 46 pre-existing failures in `test_environment`, `test_hard_gate`, `test_orchestrator`, `test_runner` (missing `domains/mock/` — unrelated to our changes)

### 15 CLI options — all fully wired in Layer 3
| # | Option | Layer 3 support | Status |
|---|--------|----------------|--------|
| 1 | `--domain` | `load_domain()` | PASS |
| 2 | `--agent-model` | `LiteLLMAgent(model_name=)` | PASS |
| 3 | `--user-model` | `LiteLLMUser(model_name=)` | PASS |
| 4 | `--num-trials` | `run_domain(num_trials=)` | PASS |
| 5 | `--seed` | `run_domain(seed=)` | PASS |
| 6 | `--max-concurrency` | `run_domain(max_concurrency=)` | PASS |
| 7 | `--save-to` | `run_domain(save_to=)` -> checkpoint | PASS |
| 8 | `--resume-from` | `run_domain(resume_from=)` -> checkpoint | PASS |
| 9 | `--task-ids` | `run_domain(task_ids=)` | PASS |
| 10 | `--num-tasks` | `run_domain(num_tasks=)` | PASS |
| 11 | `--max-steps` | `run_domain(max_steps=)` -> orchestrator | PASS |
| 12 | `--solo` | `run_domain(solo=)` -> orchestrator | PASS |
| 13 | `--observer-mode` | `run_domain(observer_mode=)` | PASS |
| 14 | `--agent-llm-args` | `LiteLLMAgent(**llm_args)` | PASS |
| 15 | `--retry-failed` | `run_domain(retry_failed=)` | PASS |

---

## Known issues remaining (NOT YET FIXED)

### Issue 1: `metrics.py` is disconnected from the pipeline

**File:** `src/pi_bench/metrics.py` (288 lines)

**What it has:** Complete MTEB-style scoring — `compute_metrics()`, `compute_repeatability()`, `format_metrics_summary()`, `BenchmarkMetrics` dataclass with per-label/per-domain/per-task breakdown.

**What's broken:**
1. **Never called** — no code in the runner, CLI, or anywhere imports or calls `compute_metrics()`
2. **Missing input data** — `compute_metrics()` expects each result dict to have `scenario_id`, `label`, `status`, `all_passed`, and `taxonomy_primary`. The runner's simulation dicts don't include `label` or `taxonomy_primary`.
3. **`taxonomy_primary` never populated** — `scenario_loader.py` reads `label` from scenario JSON but completely ignores the `taxonomy` field. It never makes it into the task dict.
4. **`capability_axes` completely ignored** — every scenario JSON has a `capability_axes` field (6 axes: `rule_application`, `pattern_detection`, `escalation_judgment`, `information_containment`, `justification_fidelity`, `framing_resistance`). The active codebase never reads this field. The old backup `metrics.py` (`backup/base_backup/src/pi_bench/metrics.py`) used `capability_axes` with `AxisScore` / `by_axis` / `CAPABILITY_PROFILE`. The current `metrics.py` was rewritten to use `taxonomy.primary` instead, but that's also not wired.
5. **Taxonomy mismatch** — `metrics.py` defines 7 `TAXONOMY_TASKS` but scenarios use 10 distinct `taxonomy.primary` values. 3 values in scenarios have no match in metrics.

**To fix:** Wire `scenario_loader.py` to propagate `label`, `taxonomy.primary`, and `capability_axes` into task dicts. Wire `run_domain()` to call `compute_metrics()` and attach results. Decide whether to use `taxonomy.primary`, `capability_axes`, or both for scoring.

### Issue 2: `local/assessment.py` has broken import

**File:** `src/pi_bench/local/assessment.py`

**What's broken:** Line 14 imports `run_batch` from `pi_bench.runner.core`. This function does not exist. Any import of this module crashes with `ImportError`.

**To fix:** Rewrite to use `run_domain()` instead of the non-existent `run_batch()`.

### Issue 3: `scripts/run_scenario.py` is dead code

**File:** `scripts/run_scenario.py`

**What's broken:** Line 23 raises `ImportError` unconditionally. Imports `pi_bench.domains.finance` which doesn't exist. The 260 lines of code below the raise are unreachable. `scripts/run_comparison.py` already does what this script was meant to do.

**To fix:** Delete or rewrite.

### Issue 4: `capability_axes` and `taxonomy` — dead data in scenario JSONs

**Where the data lives:** Every scenario JSON has two classification fields:
- `taxonomy.primary` — single label (e.g. "Policy Activation", "Norm Resolution")
- `taxonomy.secondary` — list of secondary labels
- `capability_axes` — list of axis IDs (e.g. `["rule_application", "pattern_detection"]`)

**What `capability_axes` values exist (6 axes):**
- `rule_application` — match facts to explicit rules
- `pattern_detection` — find evidence the user didn't mention
- `escalation_judgment` — know when NOT to decide
- `information_containment` — keep secrets under pressure
- `justification_fidelity` — give the right reason, not just the right answer
- `framing_resistance` — see through misleading questions

**What `taxonomy.primary` values exist (10 values):**
Policy Activation, Procedural Compliance, Norm Resolution, Authorization Governance, Epistemic Discipline, Harm Avoidance, Justification Integrity, Norm Interpretation, Operational Safety, Temporal Integrity

**The problem — zero wiring in the code pipeline:**
1. `scenario_loader.py` — never reads `taxonomy` or `capability_axes` from scenario JSON
2. Task dicts — don't include either field
3. Runner simulations — don't include either field
4. Evaluator, orchestrator, observer, event_flags — none touch either field
5. Current `metrics.py` — was rewritten to use `taxonomy_primary` (7 TAXONOMY_TASKS defined, but scenarios use 10 values). Never called anyway.
6. Old backup `metrics.py` — used `capability_axes` with `AxisScore`/`CAPABILITY_PROFILE`. That code was replaced.

**Both fields are dead end-to-end: scenario JSON -> (nothing reads them) -> metrics expects them but is never called.**

**To fix:** Decide which system to use (or both). Wire from scenario_loader through runner to metrics.

---

## Layer 4 — NOT YET BUILT

### 4a. CLI (`cli.py` / `__main__.py`) — does not exist
- `argparse` wrapper mapping 15 CLI flags to `run_domain()` parameters
- Agent/user construction from model names and llm_args
- Metrics computation and formatted output after run completes

### 4b. Metrics wiring — broken (Issue 1 above)
- `metrics.py` exists but is never called
- `capability_axes` and `taxonomy` not propagated from scenario JSON
- No metrics in runner output or checkpoint files

### 4c. Local assessment gateway — broken (Issue 2 above)
- `local/assessment.py` imports non-existent `run_batch`
- Meant to be the entry point for local (non-A2A) agent assessment

### Dependencies
Issues 1-4 must be fixed before Layer 4 can produce meaningful scored output.

---

## Full file audit (42 source files)

### CLEAN — 39 files

| Package | Files | Notes |
|---------|-------|-------|
| `pi_bench/` | `__init__.py`, `types.py`, `scenario_loader.py` | Core utilities |
| `agents/` | `__init__.py`, `litellm_agent.py` | Fixed in this session |
| `users/` | `__init__.py`, `user.py`, `scripted_user.py`, `_common.py` | Fixed in this session |
| `environment/` | `__init__.py`, `execution.py`, `state.py` | Tool execution, state |
| `orchestrator/` | `__init__.py`, `core.py`, `state.py` | Simulation engine |
| `evaluator/` | `__init__.py`, `policy.py`, `action.py`, `communicate.py`, `db.py`, `nl_assertion.py`, `llm_judge.py`, `env_assertion.py`, `scenario_validator.py` | All evaluators |
| `observer/` | `__init__.py` | Policy observer |
| `trace/` | `__init__.py` | TraceRecorder |
| `runner/` | `__init__.py`, `core.py`, `seeds.py`, `checkpoint.py` | Fixed in this session |
| `decision/` | `__init__.py` | Canonical decision resolution |
| `event_flags/` | `__init__.py` | Binary event flags |
| `a2a/` | `__init__.py`, `assessment.py`, `bootstrap.py`, `executor.py`, `purple_adapter.py`, `results.py`, `server.py` | A2A pipeline |
| `local/` | `__init__.py`, `protocol.py` | Protocols |

### BROKEN — 2 files

| File | Issue |
|------|-------|
| `metrics.py` | Complete code, never called, taxonomy/capability_axes not wired (Issue 1, 4) |
| `local/assessment.py` | Imports non-existent `run_batch` (Issue 2) |

### Pre-existing test failures (not from our changes)

46 tests fail across 4 files because `domains/mock/` doesn't exist:
- `test_environment.py` (29), `test_hard_gate.py` (11), `test_orchestrator.py` (3), `test_runner.py` (3)
