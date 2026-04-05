# Orchestrator & Runner: Sprint & Task Breakdown

**Blueprint:** `docs/plans/orchestrator-runner-blueprint.md`
**BDD scenarios:** 20 orchestrator (RED) + 13 runner (RED) = 33 total
**Target:** All 33 GREEN across 5 new files, ~600 lines

---

## Sprint Overview

| Sprint | Goal | Tasks | BDD GREEN | Demoable Output |
|--------|------|-------|-----------|-----------------|
| S1 | Foundation types + protocols | 3 | 0 (unit tests) | Import types, create messages, validate them |
| S2 | Orchestrator text routing | 3 | 14 | Run text-only conversations with stub agents |
| S3 | Orchestrator complete | 3 | 6 | Full orchestrator with tools, solo, observer |
| S4 | Evaluator pipeline | 3 | 0 (tested via runner) | Evaluate simulation runs, get rewards |
| S5 | Runner | 5 | 13 | Multi-trial runs with parallelism and save |
| **Total** | | **17** | **33** | |

---

## Sprint 1: Foundation Types & Protocols

**Goal:** Shared vocabulary (message factories, validation) and
structural interfaces (AgentProtocol, UserProtocol).

**Demo:** Import `pi_bench.types` and `pi_bench.protocols`. Create
messages with factories, validate them, verify stubs satisfy protocols.

### S1-T1: Message types module

**Description:** Create `types.py` with message factory functions,
validation, and stop signal detection. Factory for tool call dicts
uses name `build_tool_call` (not `make_tool_call` — avoids collision
with `environment.make_tool_call` which executes tools).

**File:** `src/pi_bench/types.py` (create, ~80 lines)

**Functions:**
- `make_assistant_msg(content=None, tool_calls=None, cost=0.0) -> dict`
- `make_user_msg(content=None, tool_calls=None, cost=0.0) -> dict`
- `make_tool_msg(call_id, content, requestor, error=False) -> dict`
- `make_system_msg(content) -> dict`
- `build_tool_call(name, arguments=None, requestor="assistant", call_id=None) -> dict`
- `validate_message(msg) -> bool`
- `is_stop_signal(msg) -> bool`

**Acceptance criteria:**
- All factory functions return plain dicts with correct keys
- `build_tool_call` auto-generates UUID `id` when None
- `validate_message` enforces content XOR tool_calls
- `is_stop_signal` detects `###STOP###`, `###TRANSFER###`, and `###OUT-OF-SCOPE###`

**Validation:** Unit test in `tests/test_types.py`:
- Create each message type, assert shape and defaults
- Validate four cases: content-only (True), tool_calls-only (True),
  both (False), neither (False)
- Stop signal: True for ###STOP###, True for ###TRANSFER###, False for
  regular text

**Dependencies:** None.

---

### S1-T2: Agent and User protocols

**Description:** Define `AgentProtocol` and `UserProtocol` as
`typing.Protocol` classes with `runtime_checkable`.

**File:** `src/pi_bench/protocols.py` (create, ~50 lines)

**Acceptance criteria:**
- `AgentProtocol`: `model_name: str`, `init_state(system_messages, tools, message_history) -> dict`, `generate(message, state) -> tuple[dict, dict]`, `is_stop(message) -> bool`, `set_seed(seed) -> None`, `stop(message, state) -> None`
- `UserProtocol`: `model_name: str`, `init_state(scenario, message_history) -> dict`, `generate(message, state) -> tuple[dict, dict]`, `is_stop(message) -> bool`, `set_seed(seed) -> None`, `stop(message, state) -> None`
- Both are `@runtime_checkable`

**Validation:** Unit test: create minimal stub classes, verify
`isinstance(stub, AgentProtocol)` returns True.

**Dependencies:** None (parallel with S1-T1).

---

### S1-T3: Integration smoke test

**Description:** Verify both modules import together, factories create
valid messages, stubs satisfy protocols.

**File:** No new files — verification only.

**Acceptance criteria:**
- `from pi_bench.types import *` succeeds
- `from pi_bench.protocols import AgentProtocol, UserProtocol` succeeds
- Factory-created messages pass `validate_message`
- Stop signal messages pass `is_stop_signal`

**Validation:** `python -c "from pi_bench.types import ...; from pi_bench.protocols import ..."`

**Dependencies:** S1-T1, S1-T2.

---

## Sprint 2: Orchestrator Core (Text Routing)

**Goal:** The routing state machine with text-only routing (no tool
calls). Fresh start, agent↔user conversation, stop signals, error
handling, limits, metadata.

**Demo:** Run orchestrator with stub text-only agents. See greeting,
alternating conversation, stop-signal termination. 14 BDD scenarios GREEN.

### S2-T1: Orchestrator init + step + run (text path)

**Description:** Create the orchestrator module with `init_orchestrator`,
`step`, `_route_to_agent`, `_route_to_user`, `run`, and
`get_trajectory`. Handles text-only messages (no tool_calls yet).
The `step` function dispatches based on `to_role`: "agent" calls
`_route_to_agent`, "user" calls `_route_to_user`. Stop signals from
either side end the simulation. Step count increments on EVERY step
(including env). Limit checks fire only when to_role != environment.
Message validation runs after every generate() call.
Per-role history filtering for resume: agent doesn't see user tool
calls, user doesn't see agent tool calls.

**File:** `src/pi_bench/orchestrator/__init__.py` (create, ~130 lines)

**Acceptance criteria:**
- `init_orchestrator` creates state dict with greeting message routed to user
- `step` routes text between agent and user
- Stop signals set `done=True` with correct termination reason
- `run` loops step until done, returns SimulationRun dict
- SimulationRun has: id, task_id, start_time, end_time, duration,
  termination_reason, messages (with turn_index), trial, seed
- `get_trajectory` assigns turn indices in order

**Validation:** BDD scenarios turning GREEN:
1. Fresh start sends greeting then routes to user
2. Fresh start with seed sets agent and user seeds
3. User text response routes to agent
4. Agent text response routes to user
5. Agent stop signal ends simulation
6. User stop signal ends simulation
7. User transfer signal ends simulation
8. Full trajectory is returned in message order
9. Simulation output contains required metadata

**Dependencies:** S1-T1, S1-T2.

---

### S2-T2: Limit checking (max_steps) and step counting

**Description:** Implement `_check_limits` in the run loop. Max steps
ends simulation. Step count only increments on agent/user steps (not
environment — but environment routing doesn't exist yet, so all steps
count). This task also verifies step counting works correctly with
text-only conversations.

**File:** `src/pi_bench/orchestrator/__init__.py` (extend)

**Acceptance criteria:**
- When `step_count >= max_steps`: `done=True`, `termination_reason="max_steps"`
- Step count verified in trajectory metadata

**Validation:** BDD scenarios turning GREEN:
10. Max steps reached ends simulation

**Dependencies:** S2-T1.

---

### S2-T3: Error handling (agent_error, user_error)

**Description:** Wrap `agent.generate` and `user.generate` in
try/except. Errors set `done=True` with `termination_reason="agent_error"`
or `"user_error"`. Call `agent.stop()` and `user.stop()` at end of `run`.

**File:** `src/pi_bench/orchestrator/__init__.py` (extend)

**Acceptance criteria:**
- Agent RuntimeError → `termination_reason="agent_error"`
- User RuntimeError → `termination_reason="user_error"`
- Simulation does not crash
- `agent.stop()` and `user.stop()` always called at end

**Validation:** BDD scenarios turning GREEN:
11. Agent generation error ends simulation
12. User generation error ends simulation

Note: "Max errors reached" scenario requires tool routing (Sprint 3)
and is NOT expected to go GREEN here.

**Dependencies:** S2-T1.

---

**Sprint 2 total: 12 GREEN** (scenarios 1-12 from orchestrator, excluding
max_errors, step_count_excludes_env, solo, observer, tool routing)

Wait — let me recount. The "step count" scenario (#16) involves tool
calls, so it moves to Sprint 3. Let me be precise:

**Sprint 2 GREEN (14 scenarios):**
1-4 (fresh start + text routing), 9-12 (stop signals + limits + errors),
17-18 (trajectory + metadata) = 10 scenarios.

Actually, let me map precisely:
- S2-T1 turns GREEN: #1, #2, #3, #4, #9, #10, #11, #17, #18 = 9
- S2-T2 turns GREEN: #12 = 1
- S2-T3 turns GREEN: #14, #15 = 2

**Sprint 2 total: 12 GREEN scenarios.**

Remaining for Sprint 3: #5, #6, #7, #8, #13, #16, #19, #20 = 8 scenarios.

---

## Sprint 3: Orchestrator Complete (Tools, Solo, Observer)

**Goal:** Add tool call routing, error counting, solo mode, and
observer integration. All 20 orchestrator BDD scenarios GREEN.

**Demo:** Full orchestrator with tool calls executing against the
mock domain, solo mode, and observer trace recording.

### S3-T1: Tool call routing + error counting

**Description:** Implement `_route_to_env(state, env)`. When a message
has `tool_calls`, execute each via `environment.make_tool_call`. Single
result → ToolMessage. Multiple results → MultiToolMessage. Route back
to caller. Increment `error_count` for tool errors. Step count
increments (like all steps) but limit checks do NOT fire after env
steps. After env execution, call `_sync_tools` to refresh tool
definitions. Also implement `termination_reason="too_many_errors"` in
`_check_limits`.

**File:** `src/pi_bench/orchestrator/__init__.py` (extend, ~40 lines)

**Acceptance criteria:**
- Agent tool calls → environment → results back to agent
- User tool calls → environment → results back to user
- Single call → ToolMessage, multiple → MultiToolMessage
- Error count increments for `error: True` results
- Step count increments for env steps but limit check skipped
- `too_many_errors` termination when `error_count >= max_errors`
- Tools refreshed via `_sync_tools` after every env step

**Validation:** BDD scenarios turning GREEN:
5. Agent tool calls route to environment then back to agent
6. User tool calls route to environment then back to user
7. Tool results go back to the caller not the other role
8. Multiple tool calls produce multi-tool result
13. Max errors reached ends simulation
16. Limit checks do not fire after environment steps

**Dependencies:** S2-T1 (orchestrator core).

---

### S3-T2: Solo mode

**Description:** When `solo=True`, skip user simulator entirely. Agent
generates the FIRST message (no canned greeting). Tool calls route to
environment, text responses loop back to agent. Stop signals end
simulation. No user init, no user seed.

**File:** `src/pi_bench/orchestrator/__init__.py` (extend, ~20 lines)

**Acceptance criteria:**
- `run(agent, user=None, ..., solo=True)` works
- No user messages in trajectory
- Tool calls execute normally
- Agent stop signal terminates

**Validation:** BDD scenario turning GREEN:
19. Solo mode skips user simulator

**Dependencies:** S3-T1 (tool routing needed for solo).

---

### S3-T3: Observer integration

**Description:** When the environment is wrapped with an observer,
tool calls go through `observed_tool_call`. Detect observer by
checking for `"observer"` key in the env dict. The orchestrator
unwraps: uses `env["env"]` for tool execution and `env["observer"]`
for recording.

**File:** `src/pi_bench/orchestrator/__init__.py` (extend, ~15 lines)

**Acceptance criteria:**
- Observer-wrapped env: tool calls route through `observed_tool_call`
- Observer trace records all tool calls
- Trace entry count matches trajectory tool call count
- Non-observer environments unchanged

**Validation:** BDD scenario turning GREEN:
20. Observer wraps environment and records trace

**Dependencies:** S3-T1, existing `observer/__init__.py`.

---

**Sprint 3 total: 8 GREEN → cumulative 20/20 orchestrator GREEN.**

---

## Sprint 4: Evaluator Pipeline

**Goal:** Reward computation after simulation. Connects orchestrator
output to evaluation criteria.

**Demo:** `evaluate(task, simulation_run, domain)` returns RewardInfo.
Abnormal → 0.0. Normal with expected actions → positive reward.

### S4-T1: Evaluator skeleton + abnormal termination

**Description:** Create `evaluator/__init__.py` with main `evaluate`
function. Abnormal termination → reward 0.0. No evaluation criteria →
reward 1.0. Set up reward composition loop.

**File:** `src/pi_bench/evaluator/__init__.py` (create, ~40 lines)

**Acceptance criteria:**
- Abnormal termination (max_steps, too_many_errors, agent_error,
  user_error) → `{"reward": 0.0, ...}`
- No evaluation criteria → `{"reward": 1.0, ...}`
- Returns RewardInfo dict with `reward`, `reward_basis`, `reward_breakdown`

**Validation:** Unit test: exercise abnormal and no-criteria cases.

**Dependencies:** S1-T1 (types).

---

### S4-T2: Action + communicate evaluators

**Description:** Implement `evaluate_actions` (check expected tool calls
in trajectory) and `evaluate_communicate` (substring check on agent
messages). Wire both into `evaluate` via `reward_basis`.

**File:** `src/pi_bench/evaluator/__init__.py` (extend, ~60 lines)

**Acceptance criteria:**
- `evaluate_actions`: all found → 1.0, none → 0.0
- Match by name + requestor + compared arguments
- `evaluate_communicate`: all info strings found → 1.0, none → 0.0
- Case-insensitive substring on assistant messages, commas stripped before comparison

**Validation:** Unit tests for each evaluator.

**Dependencies:** S4-T1.

---

### S4-T3: Reward composition

**Description:** Final reward = product of all evaluator rewards.
Read `reward_basis` from task's `evaluation_criteria`. Unknown
evaluator types are skipped. `reward_breakdown` records per-evaluator
values.

**File:** `src/pi_bench/evaluator/__init__.py` (extend, ~20 lines)

**Acceptance criteria:**
- `reward_basis: ["ACTION"]` → runs action evaluator only
- `reward_basis: ["ACTION", "COMMUNICATE"]` → product of both
- `reward_breakdown` has per-evaluator entries
- Empty reward_basis → 1.0

**Validation:** Unit test: compose rewards from multiple evaluators.

**Dependencies:** S4-T1, S4-T2.

---

**Sprint 4 has 0 direct BDD scenarios** — evaluator is tested through
runner BDD scenarios in Sprint 5. Sprint 4 has its own unit tests.

---

## Sprint 5: Runner

**Goal:** Multi-trial execution with ThreadPoolExecutor, deterministic
seeds, incremental save, resume, task filtering. All 13 runner BDD
scenarios GREEN.

**Demo:** `run_domain(domain, agent, user, num_trials=4, seed=42, max_concurrency=2)` executes trials in parallel, returns Results with
evaluated rewards.

### S5-T1: Seed derivation + work queue

**Description:** Implement `derive_trial_seeds` (SHA-256 from base
seed) and `_build_work_queue` (generate task/trial/seed tuples,
exclude completed).

**File:** `src/pi_bench/runner/__init__.py` (create, ~40 lines)

**Acceptance criteria:**
- `derive_trial_seeds(42, 4)` → 4 distinct ints, deterministic
- Same base seed → same list every time
- `_build_work_queue` generates correct count of tuples
- Completed pairs are excluded

**Validation:** Unit tests for pure functions.

**Dependencies:** None.

---

### S5-T2: Single simulation + run_domain

**Description:** Implement `_run_one` (creates fresh env, calls
orchestrator.run, calls evaluator.evaluate) and `run_domain` (builds
work queue, submits to ThreadPoolExecutor, collects results, builds
Results dict with Info metadata).

Note: `run_domain` accepts agent/user as instances or factories
(callables). When `max_concurrency > 1`, each thread gets a fresh
instance via factory or thread-local wrapping. Each `_run_one` call
gets its own orchestrator run with its own state. Seeds set via
`agent.set_seed(seed)` and `user.set_seed(seed)` before
`init_state()`.

**File:** `src/pi_bench/runner/__init__.py` (extend, ~80 lines)

**Acceptance criteria:**
- Fresh environment created per trial
- Seeds passed to orchestrator
- Evaluator called with task + result
- `Results` dict has `info`, `tasks`, `simulations`
- `info` has domain, agent_model, user_model, num_trials, seed,
  max_concurrency, timestamp
- `task_ids` filter: only run matching tasks
- ThreadPoolExecutor with max_workers=max_concurrency

**Validation:** BDD scenarios turning GREEN:
1. Single trial returns one simulation run per task
2. Multiple trials return k runs per task
3. Each trial gets a unique seed
4. Same base seed produces same set of trial seeds
5. Deterministic agent with same seed = same trajectory
6. Concurrent trials all complete
7. Max concurrency limits parallel threads
8. Result contains metadata about the run configuration
9. Abnormal termination gets reward 0.0
10. Normal completion gets evaluated reward
13. Running specific task IDs only runs those tasks

**Dependencies:** S5-T1, Sprint 2-3 (orchestrator), Sprint 4 (evaluator).

---

### S5-T3: Incremental save

**Description:** When `save_to` is provided, write results to JSON
after each simulation completes. Uses `threading.Lock` for concurrent
safety.

**File:** `src/pi_bench/runner/__init__.py` (extend, ~20 lines)

**Acceptance criteria:**
- File written after each simulation
- Final file has all simulations
- Concurrent writes serialized via Lock
- Valid JSON with `simulations` list

**Validation:** BDD scenario turning GREEN:
11. Results are saved incrementally as runs complete

**Dependencies:** S5-T2.

---

### S5-T4: Resume from checkpoint

**Description:** When `resume_from` is provided, load existing results,
extract completed (task_id, trial) pairs, skip them in work queue,
merge old + new results. Track `new_runs_count`.

**File:** `src/pi_bench/runner/__init__.py` (extend, ~20 lines)

**Acceptance criteria:**
- Loads checkpoint, skips completed `(task_id, trial, seed)` triples
- Only new simulations run
- Final result merges old + new
- `new_runs_count` field in result

**Validation:** BDD scenario turning GREEN:
12. Resume skips already-completed runs

**Dependencies:** S5-T2, S5-T3.

---

**Sprint 5 total: 13 GREEN → cumulative 33/33 all GREEN.**

---

## Dependency Graph

```
S1-T1 (types) ──────┐
                     ├──> S1-T3 (smoke) ──> S2-T1 (orchestrator core)
S1-T2 (protocols) ──┘                        │
                                              ├──> S2-T2 (limits)
                                              └──> S2-T3 (errors)
                                                     │
                                              S3-T1 (tool routing)
                                              ┌──────┤
                                              │      │
                                    S3-T2 (solo)   S3-T3 (observer)

S4-T1 (eval skeleton) ──> S4-T2 (action+communicate) ──> S4-T3 (composition)

S5-T1 (seeds+queue) ──> S5-T2 (run_domain) ──> S5-T3 (save) ──> S5-T4 (resume)
```

## Parallelization Opportunities

| Parallel Group | Tasks | Gate |
|---------------|-------|------|
| Group A | S1-T1 + S1-T2 | None |
| Group B | S2-T2 + S2-T3 | After S2-T1 |
| Group C | S3-T2 + S3-T3 | After S3-T1 |
| Group D | S4-T1 + S4-T2 + S4-T3 | After S1-T1 (runs parallel to Sprint 2-3) |
| Group E | S5-T1 | Independent (any time) |

**Maximum parallelism:** Sprint 4 (evaluator) can run entirely in
parallel with Sprints 2-3 (orchestrator). S5-T1 (seeds) has zero
dependencies and can start any time.

---

## Pre-Implementation Fixes Required

These are blockers identified in review. Fix BEFORE starting Sprint 1.

### FIX-1: Add model_name to orchestrator stubs

All stub agents/users in `test_orchestrator.py` need `model_name`
attribute. The runner stubs already have it. The orchestrator's
`run()` function reads `agent.model_name` for metadata.

### FIX-2: Fix save scenario step definition

The "incremental save" scenario has `Given a save path` but the
`When I run with num_trials 1` step does NOT pass `save_to` to
`run_domain`. Need a new `When` step or modify existing to accept
optional `save_path`.

### FIX-3: Fix runner stub closure leakage

`_stub_user_completes()` uses a closure `call_count = {"n": 0}` that
is NOT reset between runs. The "run twice" scenarios will fail because
the user stops immediately on the second run. Fix: reset `call_count`
in `init_state()`.

### FIX-4: Thread safety for concurrent stubs

Stubs share mutable closures across threads. For `max_concurrency > 1`,
this causes races. Fix: `_run_one` in the runner should create fresh
agent/user instances per work item, OR stubs use thread-local storage.

---

## Validation Strategy

| Sprint | Validation Method |
|--------|------------------|
| S1 | Unit tests in `tests/test_types.py` |
| S2 | 12 orchestrator BDD scenarios GREEN |
| S3 | 8 more orchestrator BDD scenarios GREEN (20/20 total) |
| S4 | Unit tests in `tests/test_evaluator.py` |
| S5 | 13 runner BDD scenarios GREEN (33/33 total) |

**Final gate:** `pytest tests/step_defs/ -v` → 152 passed (119 existing + 33 new).
