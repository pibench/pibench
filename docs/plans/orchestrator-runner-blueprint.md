# Orchestrator & Runner Blueprint

**Scope:** Core simulation engine — orchestrator, runner, data types,
agent/user protocols, evaluation.
**Source of truth:** `docs/plans/core-engine-spec.md`
**Builds on:** Environment layer (186 lines, 30 BDD scenarios, complete)
**Reference system:** tau2-bench v0.2.1 (orchestrator: 626 lines,
runner: 574 lines, data model: ~800 lines)

---

## Context

The environment layer is complete — tool execution, DB hashing, requestor
routing, solo mode. The evaluation pipeline components are complete —
TraceRecorder, PolicyCheckEngine, DecisionSignalResolution, EventFlags,
PolicyObservingEnvironment.

This blueprint covers the layers ABOVE the environment: the orchestrator
(conversation loop), the runner (multi-trial execution), and the data
types and protocols that connect them.

The reference system (tau2-bench) has these layers in ~2,000 lines across
6 files. Our implementation targets comparable scope with a functional
approach (plain dicts, free functions, Protocol-based typing).

---

## Goals

From the spec:

1. Route messages between agent, user, and environment
2. Support solo mode (agent + environment, no user)
3. Deterministic seed management for reproducibility
4. Multi-trial execution with ThreadPoolExecutor
5. Incremental save and resume
6. Evaluation after each simulation (reward composition)
7. Task filtering by ID

## Non-Goals

- CLI (separate blueprint, later)
- Domain registry / discovery (later)
- Policy pack management (later)
- NL assertions evaluator (requires LLM-as-judge — future)
- Ablation controller (future)
- Adversarial user profiles (future)

## Cross-Cutting Concerns

**Error handling:** Errors during agent/user generation end the
simulation with a termination reason — never crash the runner.
Tool execution errors are already handled by the environment layer.

**Observability:** Each simulation records start/end timestamps,
termination reason, costs, and the full message trajectory. The
runner logs progress per task.

**Determinism:** Seeds are derived via SHA-256 from
`f"{base_seed}:{task_id}:{trial}"` — order-independent, stable
regardless of task count changes. Agent and user both receive the
trial seed.

## NOT Building

- **No new environment code** — environment layer is done
- **No LLM integration** — that's the agent/user implementation, not
  the orchestrator. The orchestrator only calls protocol methods.
- **No async** — ThreadPoolExecutor for parallelism, synchronous
  orchestrator. tau2 uses sync orchestrator + thread pool. We match.
- **No Pydantic** — plain dicts and dataclasses. The functional style
  from the environment layer continues.
- **No class hierarchies** — Protocol (structural typing) for agent
  and user, free functions for orchestrator and runner.

---

## Chunk 1: Data Types

**What:** The shared vocabulary — message dicts, simulation output,
task format. Every other component depends on these.

**Reference:** tau2 `data_model/` — 3 files, ~800 lines, Pydantic models.
We use plain dicts + TypedDicts for the same contracts, fewer lines.

### Messages

All messages are plain dicts. The orchestrator creates them, the
trajectory stores them.

```python
# Message types (all plain dicts)

SystemMessage = {
    "role": "system",
    "content": str,
}

AssistantMessage = {
    "role": "assistant",
    "content": str | None,          # text response
    "tool_calls": list[ToolCall] | None,  # OR tool calls, never both
    "cost": float,                   # API cost in USD (0.0 for stubs)
    "usage": dict | None,            # token counts
}

UserMessage = {
    "role": "user",
    "content": str | None,
    "tool_calls": list[ToolCall] | None,
    "cost": float,
    "usage": dict | None,
}

ToolCall = {
    "id": str,                       # unique call ID
    "name": str,                     # tool name
    "arguments": dict,               # key-value pairs
    "requestor": str,                # "user" or "assistant"
}

ToolMessage = {
    "role": "tool",
    "id": str,                       # matches ToolCall.id
    "content": str,                  # JSON-serialized result
    "requestor": str,                # who made the call
    "error": bool,                   # whether execution failed
}

MultiToolMessage = {
    "role": "multi_tool",
    "tool_messages": list[ToolMessage],
}
```

**Validation rule:** Assistant and user messages have content XOR
tool_calls. Never both. Never neither.

**Turn index:** Assigned after simulation by the orchestrator's
`get_trajectory()`. Not stored during routing.

### ToolCall vs Environment ToolCall

The environment layer already has `make_tool_call(env, tool_name, call_id, arguments, requestor)`. The message-level ToolCall dict wraps
the same data but lives in the message trajectory. The orchestrator
extracts fields from message ToolCalls and passes them to
`make_tool_call()`.

### Simulation Output

```python
SimulationRun = {
    "id": str,                       # UUID
    "task_id": str,
    "start_time": float,             # time.time()
    "end_time": float,
    "duration": float,               # seconds
    "termination_reason": str,       # see TerminationReason
    "messages": list[Message],       # full trajectory
    "reward_info": RewardInfo,
    "agent_cost": float,
    "user_cost": float,
    "trial": int,                    # 0-indexed trial number
    "seed": int,                     # trial-specific seed
}

TerminationReason = (
    "agent_stop"
    | "user_stop"
    | "max_steps"
    | "too_many_errors"
    | "agent_error"
    | "user_error"
)

RewardInfo = {
    "reward": float,                 # 0.0 to 1.0
    "reward_basis": list[str],       # which evaluators were used
    "reward_breakdown": dict,        # per-evaluator details
}
```

### Batch Result

```python
Results = {
    "info": Info,
    "tasks": list[Task],
    "simulations": list[SimulationRun],
}

Info = {
    "domain": str,
    "agent_model": str,
    "user_model": str,
    "num_trials": int,
    "seed": int | None,
    "max_steps": int,
    "max_errors": int,
    "max_concurrency": int,
    "solo": bool,
    "timestamp": str,                # ISO format
    "pi_bench_version": str,         # package version
}
```

### Task

```python
Task = {
    "id": str,
    "description": str,
    "user_scenario": UserScenario,
    "ticket": str | None,            # solo mode instruction
    "initial_state": InitialState,
    "evaluation_criteria": EvaluationCriteria,
}

UserScenario = {
    "persona": str,
    "instructions": str,
}

InitialState = {
    "initialization_data": dict | None,
    "initialization_actions": list[ToolCall] | None,
    "message_history": list[Message] | None,
}

EvaluationCriteria = {
    "expected_actions": list[ExpectedAction] | None,
    "env_assertions": list[EnvAssertion] | None,
    "communicate_info": list[str] | None,
    "nl_assertions": list[str] | None,
    "reward_basis": list[str] | None,
}

ExpectedAction = {
    "action_id": str,
    "requestor": str,
    "name": str,
    "arguments": dict,
    "compare_args": list[str] | None,  # None = compare all
}
```

### File

| File | Purpose | ~Lines |
|------|---------|--------|
| `src/pi_bench/types.py` | Type aliases, validation helpers, factory functions | ~80 |

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `make_assistant_msg` | `(content=None, tool_calls=None, cost=0.0) -> dict` | Create assistant message |
| `make_user_msg` | `(content=None, tool_calls=None, cost=0.0) -> dict` | Create user message |
| `make_tool_msg` | `(call_id, content, requestor, error=False) -> dict` | Create tool result message |
| `make_system_msg` | `(content) -> dict` | Create system message |
| `make_tool_call` | `(name, arguments=None, requestor="assistant", call_id=None) -> dict` | Create a tool call dict |
| `validate_message` | `(msg) -> bool` | Check content XOR tool_calls |
| `is_stop_signal` | `(msg) -> bool` | Check for ###STOP###, ###TRANSFER###, or ###OUT-OF-SCOPE### |

### Contract Map

| Spec Contract | Covered By |
|---------------|------------|
| Messages have content XOR tool_calls | `validate_message()` |
| ToolCall has id, name, arguments, requestor | `make_tool_call()` |
| SimulationRun has required metadata | `SimulationRun` dict shape |
| Task has evaluation criteria | `Task` / `EvaluationCriteria` dict shape |

---

## Chunk 2: Agent & User Protocols

**What:** The interfaces that any agent or user implementation must
satisfy. Protocol (structural typing) — no base class inheritance.

**Reference:** tau2 `agent/base.py` (11 methods, ABC + Generic),
`user/base.py` (6 methods, ABC). We use Protocol for structural typing.

### AgentProtocol

```python
class AgentProtocol(Protocol):
    model_name: str

    def init_state(
        self,
        system_messages: list[dict],
        tools: list[dict],
        message_history: list[dict] | None = None,
    ) -> dict:
        """Initialize agent state. Returns opaque state dict."""
        ...

    def generate(
        self,
        message: dict,
        state: dict,
    ) -> tuple[dict, dict]:
        """Generate next message. Returns (assistant_message, new_state)."""
        ...

    def is_stop(self, message: dict) -> bool:
        """Check if the message is a stop signal."""
        ...

    def set_seed(self, seed: int) -> None:
        """Set the random seed for reproducibility."""
        ...

    def stop(self, message: dict | None, state: dict | None) -> None:
        """Cleanup when simulation ends."""
        ...
```

### UserProtocol

```python
class UserProtocol(Protocol):
    model_name: str

    def init_state(
        self,
        scenario: dict,
        message_history: list[dict] | None = None,
    ) -> dict:
        """Initialize user state from scenario. Returns opaque state dict."""
        ...

    def generate(
        self,
        message: dict,
        state: dict,
    ) -> tuple[dict, dict]:
        """Generate next message. Returns (user_message, new_state)."""
        ...

    def is_stop(self, message: dict) -> bool:
        """Check if message is a stop/transfer signal."""
        ...

    def set_seed(self, seed: int) -> None:
        """Set the random seed for reproducibility."""
        ...

    def stop(self, message: dict | None, state: dict | None) -> None:
        """Cleanup when simulation ends."""
        ...
```

### Key Differences from tau2

| Aspect | tau2 | pi-bench |
|--------|------|----------|
| Typing | ABC + Generic[AgentState] | Protocol (structural) |
| State | TypeVar, Pydantic model | Plain dict |
| Agent init | `get_init_state(message_history)` | `init_state(system_messages, tools, message_history)` |
| User init | `get_init_state(message_history)` | `init_state(scenario, message_history)` |
| Stop | `@classmethod is_stop(msg)` | Instance method `is_stop(msg)` |
| Async | User is async | Everything sync |

### Why Protocol, not ABC

1. Stub agents in tests don't need to inherit anything
2. External agent implementations (e.g., wrapping OpenAI SDK) just
   need the right methods — no import dependency on pi-bench
3. Duck typing is Pythonic; Protocol makes it type-checkable

### File

| File | Purpose | ~Lines |
|------|---------|--------|
| `src/pi_bench/protocols.py` | AgentProtocol, UserProtocol | ~50 |

### Contract Map

| Spec Contract | Covered By |
|---------------|------------|
| Agent generates next message from input + state | `AgentProtocol.generate()` |
| Agent initializes from system prompt + tools + history | `AgentProtocol.init_state()` |
| Agent stop detection | `AgentProtocol.is_stop()` |
| Agent seed for reproducibility | `AgentProtocol.set_seed()` |
| User generates from agent message + state | `UserProtocol.generate()` |
| User initializes from scenario | `UserProtocol.init_state()` |
| User stop/transfer detection | `UserProtocol.is_stop()` |

---

## Chunk 3: Orchestrator

**What:** The routing state machine. Routes messages between agent,
user, and environment. One step = one message routed.

**Reference:** tau2 `orchestrator.py` — 626 lines, 12 methods, 1 class.
We use free functions + a state dict instead of a class.

### State

The orchestrator state is a plain dict, created by `init_orchestrator()`
and threaded through `step()`.

```python
OrchestratorState = {
    "trajectory": list[dict],      # all messages in order
    "from_role": str,              # who sent the current message
    "to_role": str,                # who should receive it
    "current_message": dict,       # the message being routed
    "agent_state": dict,           # opaque agent state
    "user_state": dict,            # opaque user state
    "step_count": int,             # ALL steps (agent + user + env)
    "error_count": int,            # tool execution errors
    "done": bool,
    "termination_reason": str | None,
    "tools": list[dict],           # current tool definitions (refreshed via sync_tools)
}
```

### Routing Logic (the state machine)

```
EVERY step:
  step_count += 1  (counts ALL steps including env)
  validate_message(current_message)  (content XOR tool_calls)

Message goes to USER:
  user.generate(message, user_state) -> (user_msg, new_state)
  if user.is_stop(user_msg): done, reason = "user_stop"
  elif user_msg has tool_calls: route to ENVIRONMENT
  else: route to AGENT
  check limits (only when to_role != ENVIRONMENT)

Message goes to AGENT:
  agent.generate(message, agent_state) -> (agent_msg, new_state)
  if agent.is_stop(agent_msg): done, reason = "agent_stop"
  elif agent_msg has tool_calls: route to ENVIRONMENT
  else: route to USER
  check limits (only when to_role != ENVIRONMENT)

Message goes to ENVIRONMENT:
  for each tool_call in message.tool_calls:
    result = make_tool_call(env, ...)
  wrap results in ToolMessage or MultiToolMessage
  route back to whoever made the calls (from_role)
  sync_tools: refresh tools from env (env may add/remove tools dynamically)
  do NOT check limits after env steps
```

**Step counting:** step_count increments on EVERY step (agent, user,
and environment). Limit checks (max_steps, max_errors) only fire when
the next recipient is NOT the environment. This means env steps count
toward the total but don't trigger early termination — environment
execution must complete before we stop.

**sync_tools:** After every environment step, call the domain's
`get_environment` to refresh tool definitions. Tools can change
dynamically (e.g., new options available after state changes).

**Message validation:** Every message from agent.generate() or
user.generate() is checked via `validate_message()`. Content XOR
tool_calls must hold.

### Initialization

Two paths:

**Fresh start (no message history):**
1. Set seeds on agent and user
2. Init user state from scenario
3. Create greeting message: `{"role": "assistant", "content": "Hi! How can I help you today?"}`
4. Init agent state with system messages + tools + [greeting]
5. Set trajectory = [greeting], route greeting to USER

**Resume from history:**
1. Set seeds on agent and user
2. Validate message history
3. Determine routing from last message in history
4. Filter history per-role: agent sees only (system, assistant,
   tool-for-assistant) messages; user sees only (system, user,
   tool-for-user, assistant-text) messages
5. Init agent state with system messages + tools + filtered history
6. Init user state with scenario + filtered history
7. Set trajectory = full history, continue routing

### Solo Mode

When solo mode is on, there is no user. Initialization: the agent
generates the FIRST message (no canned greeting). The agent's first
output typically contains tool calls. Text responses route back to the
agent (not errors — the agent may produce intermediate reasoning).
Tool results route back to agent. Stop signals end the simulation.

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `init_orchestrator` | `(agent, user, env, task, seed=None, solo=False) -> OrchestratorState` | Set up initial state |
| `step` | `(state, agent, user, env) -> OrchestratorState` | Execute one routing step |
| `run` | `(agent, user, env, task, max_steps=50, max_errors=10, seed=None, solo=False) -> SimulationRun` | Full simulation loop |
| `get_trajectory` | `(state) -> list[dict]` | Assign turn indices, return ordered messages |
| `_route_to_agent` | `(state, agent) -> OrchestratorState` | Agent generates, update routing |
| `_route_to_user` | `(state, user) -> OrchestratorState` | User generates, update routing |
| `_route_to_env` | `(state, env) -> OrchestratorState` | Execute tool calls, route results back |
| `_check_limits` | `(state, max_steps, max_errors) -> OrchestratorState` | Check termination conditions (only when to_role != env) |
| `_sync_tools` | `(state, env) -> OrchestratorState` | Refresh tool definitions from environment after env steps |
| `_filter_history_for_role` | `(history, role) -> list[dict]` | Filter message history per-role for resume (agent doesn't see user tool calls, user doesn't see agent tool calls) |

### File

| File | Purpose | ~Lines |
|------|---------|--------|
| `src/pi_bench/orchestrator/__init__.py` | Orchestrator state machine | ~200 |

### Contract Map (BDD scenarios)

| BDD Scenario | Function |
|--------------|----------|
| Fresh start sends greeting then routes to user | `init_orchestrator`, `step` |
| Fresh start with seed sets agent and user seeds | `init_orchestrator` |
| User text response routes to agent | `_route_to_user` |
| Agent text response routes to user | `_route_to_agent` |
| Agent tool calls route to environment then back to agent | `_route_to_env` |
| User tool calls route to environment then back to user | `_route_to_env` |
| Tool results go back to the caller not the other role | `_route_to_env` |
| Multiple tool calls produce multi-tool result | `_route_to_env` |
| Agent stop signal ends simulation | `_route_to_agent` |
| User stop signal ends simulation | `_route_to_user` |
| User transfer signal ends simulation | `_route_to_user` |
| Max steps reached ends simulation | `_check_limits` |
| Max errors reached ends simulation | `_check_limits` |
| Agent generation error ends simulation | `_route_to_agent` |
| User generation error ends simulation | `_route_to_user` |
| Limit checks do not fire after environment steps | `step`, `_check_limits` |
| Full trajectory returned in order | `get_trajectory` |
| Simulation output has required metadata | `run` |
| Solo mode skips user simulator | `init_orchestrator`, `step` |
| Observer wraps environment and records trace | `_route_to_env` (via observer) |

---

## Chunk 4: Evaluation Pipeline

**What:** Reward computation after a simulation ends. Connects existing
components (CheckEngine, TraceRecorder) to the orchestrator output.

**Reference:** tau2 `evaluator/` — 6 files, 4 evaluator types.
We reuse our existing CheckEngine for action matching and add
environment and communicate evaluators.

### Evaluator Types

| Type | Deterministic? | Already Built? |
|------|---------------|----------------|
| ACTION | Yes | Partial — CheckEngine handles `tool_called`, `tool_called_with` |
| DB | Yes | No — needs environment replay |
| COMMUNICATE | Yes | No — substring matching |
| ENV_ASSERTION | Yes | No — assertion functions |
| NL_ASSERTION | No (LLM judge) | Deferred — future |

### Reward Composition

```
1. If termination was abnormal (not agent_stop, not user_stop):
   reward = 0.0, skip evaluation

2. If no evaluation_criteria: reward = 1.0

3. For each evaluator in reward_basis:
   evaluator_reward = evaluate(task, trajectory, env)

4. final_reward = product(all evaluator rewards)
```

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `evaluate` | `(task, trajectory, domain) -> RewardInfo` | Run all evaluators, compose reward |
| `evaluate_actions` | `(expected_actions, trajectory) -> float` | Check expected tool calls appear |
| `evaluate_db` | `(task, trajectory, domain) -> float` | Replay trajectory, compare BOTH expected and actual DB hashes |
| `evaluate_communicate` | `(communicate_info, trajectory) -> float` | Substring check on agent messages (strip commas before comparison) |
| `evaluate_env_assertions` | `(assertions, env) -> float` | Run assertion functions |

### File

| File | Purpose | ~Lines |
|------|---------|--------|
| `src/pi_bench/evaluator/__init__.py` | Reward composition + individual evaluators | ~120 |

### Contract Map

| Spec Contract | Function |
|---------------|----------|
| Abnormal termination gets reward 0.0 | `evaluate()` |
| No evaluation criteria → reward 1.0 | `evaluate()` |
| Action evaluator checks all expected actions | `evaluate_actions()` |
| Environment evaluator compares DB state | `evaluate_db()` |
| Communicate evaluator checks required info | `evaluate_communicate()` |
| Reward is product of all evaluator rewards | `evaluate()` |

---

## Chunk 5: Runner

**What:** Multi-trial executor. Runs k trials per task using a
ThreadPoolExecutor. Saves results incrementally. Supports resume.

**Reference:** tau2 `run.py` — 574 lines, 12 functions.

### Seed Management

```python
import hashlib

def derive_trial_seeds(base_seed: int, num_trials: int) -> list[int]:
    """Deterministic seed derivation from base seed.

    seed_i = int(sha256(f"{base_seed}:{i}").hexdigest()[:8], 16)
    """
```

Same base seed always produces the same list of trial seeds.
Different trials get different seeds. Seeds are ints.

### Concurrency

```python
from concurrent.futures import ThreadPoolExecutor

def run_domain(..., max_concurrency=1):
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = [pool.submit(_run_one, task, trial, seed) for ...]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            _save_incremental(result, save_path)
```

### Agent/User per Trial

The runner receives agent and user **instances** but each `_run_one`
call sets its own seed via `agent.set_seed(seed)` and
`user.set_seed(seed)`. The orchestrator calls `agent.init_state()` and
`user.init_state()` which reset internal state. This means agent/user
instances are reused across trials but state is reset per trial.

For thread safety with `max_concurrency > 1`: the runner creates
agent/user **factories** (callables) so each thread gets a fresh
instance. The `run_domain` API accepts either instances or factories:

```python
def run_domain(
    domain,
    agent,           # AgentProtocol instance or Callable[[], AgentProtocol]
    user,            # UserProtocol instance or Callable[[], UserProtocol]
    ...
)
```

When `max_concurrency == 1`, instances are used directly. When `> 1`,
if agent/user are not callables, the runner wraps them in a
thread-local accessor.

### Resume

1. If `resume_from` path exists, load it
2. Extract completed `(task_id, trial, seed)` triples
3. Skip those triples when building the work queue
4. Append new results to the loaded results

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `run_domain` | `(domain, agent, user, num_trials=1, seed=None, max_concurrency=1, save_to=None, resume_from=None, task_ids=None, max_steps=50, max_errors=10, solo=False) -> Results` | Main entry point |
| `_build_work_queue` | `(tasks, num_trials, base_seed, completed) -> list[tuple]` | Generate (task, trial, seed) tuples |
| `_run_one` | `(task, trial, seed, agent, user, domain, max_steps, max_errors, solo) -> SimulationRun` | Single simulation |
| `_save_incremental` | `(result, path, lock) -> None` | Append one result to JSON file |
| `_load_checkpoint` | `(path) -> Results | None` | Load existing results for resume |
| `derive_trial_seeds` | `(base_seed, num_trials) -> list[int]` | Deterministic seed derivation |
| `_make_info` | `(domain, agent, user, num_trials, seed, max_concurrency) -> Info` | Build metadata dict |

### File

| File | Purpose | ~Lines |
|------|---------|--------|
| `src/pi_bench/runner/__init__.py` | Multi-trial runner with ThreadPoolExecutor | ~150 |

### Contract Map (BDD scenarios)

| BDD Scenario | Function |
|--------------|----------|
| Single trial returns one run per task | `run_domain`, `_build_work_queue` |
| Multiple trials return k runs per task | `run_domain`, `_build_work_queue` |
| Each trial gets a unique seed | `derive_trial_seeds` |
| Same base seed produces same trial seeds | `derive_trial_seeds` |
| Deterministic agent with same seed = same trajectory | `_run_one` (seeds threaded through) |
| Concurrent trials all complete | `run_domain` (ThreadPoolExecutor) |
| Max concurrency limits parallel threads | `run_domain` (max_workers) |
| Result contains metadata | `_make_info` |
| Abnormal termination gets reward 0.0 | `_run_one` → `evaluate()` |
| Normal completion gets evaluated reward | `_run_one` → `evaluate()` |
| Incremental save | `_save_incremental` |
| Resume skips completed runs | `_load_checkpoint`, `_build_work_queue` |
| Task filtering by IDs | `run_domain` (filter tasks list) |

---

## Design Decisions (tau2 Review, 2026-02-23)

| # | Gap | Decision | Rationale |
|---|-----|----------|-----------|
| 1 | Step count semantics | Count ALL steps; check limits only when to_role != env | Matches tau2 behavior. Env execution must complete before termination. |
| 2 | Seed derivation | SHA-256 from `f"{base_seed}:{task_id}:{trial}"` | Order-independent. No need for tau2 cross-compatibility. |
| 3 | Message history resume | Per-role filtering: agent/user each get filtered view | Required for correctness — agent shouldn't see user's tool calls. |
| 4 | sync_tools | Refresh tools after every env step | Dynamic tool availability (e.g., new options after state changes). |
| 5 | Message validation | Validate after every generate() call | Catch malformed agent/user output early. |
| 6 | Solo mode init | Agent generates first message (no canned greeting) | Matches tau2 solo behavior. Solo agents start with tool calls. |
| 7 | ###OUT-OF-SCOPE### | Add to is_stop_signal as third stop signal | tau2 uses this for out-of-domain requests. |
| 8 | User tools | Deferred — UserProtocol unchanged | User tool calls already work via environment routing. User doesn't need tool definitions at init. |
| 9 | Dual DB hash | evaluate_db compares expected AND actual hashes | Both must match for reward. Catches both incorrect state and missing actions. |
| 10 | Info metadata | Added max_errors, solo, pi_bench_version | Complete metadata for reproducibility. |
| 11 | Resume keying | Key on (task_id, trial, seed) not just (task_id, trial) | Handles seed changes between runs. |
| 12 | Agent/user factories | run_domain accepts instances or factories | Thread safety for max_concurrency > 1. |
| 13 | Communicate comma-strip | Strip commas from text before substring matching | Matches tau2 behavior. Prevents false negatives from punctuation. |

---

## Implementation Order

Each chunk is independently implementable and testable:

```
Chunk 1: types.py          (~80 lines)  — no dependencies
Chunk 2: protocols.py      (~50 lines)  — no dependencies
Chunk 3: orchestrator/     (~200 lines) — depends on Chunk 1, 2, environment
Chunk 4: evaluator/        (~120 lines) — depends on Chunk 1, environment
Chunk 5: runner/           (~150 lines) — depends on Chunk 1-4
```

Total: ~600 lines across 5 files.

Reference system: ~2,000 lines across 6+ files (Pydantic, ABC, async).
Our delta: ~600 lines (plain dicts, Protocol, sync). Justified by:
no Pydantic boilerplate, no ABC inheritance, no async machinery,
environment layer already built.

---

## Scope Test

| Component | tau2 Files | tau2 Lines | pi-bench Files | pi-bench Lines |
|-----------|-----------|------------|----------------|----------------|
| Data model | 3 | ~800 | 1 | ~80 |
| Protocols | 2 | ~700 | 1 | ~50 |
| Orchestrator | 2 | ~626 | 1 | ~200 |
| Evaluator | 6 | ~500 | 1 | ~120 |
| Runner | 1 | ~574 | 1 | ~150 |
| **Total** | **14** | **~3,200** | **5** | **~600** |

Reduction justified: environment layer already built (186 lines),
no Pydantic (plain dicts), no ABC (Protocol), no async, no LLM
integration in orchestrator (that's agent implementation).
