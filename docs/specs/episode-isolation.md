# Episode Isolation & Reproducibility Spec

Date: 2026-03-21

---

## 1. Problem Statement

pi-bench is a benchmark. Its results must be reproducible. When we run the
same scenario against the same model 10 times, the scores must fall within a
narrow confidence interval. When we run 34 scenarios in sequence or parallel,
no scenario may affect another's environment, database state, or evaluation.

This spec defines the isolation and reproducibility guarantees that the
benchmark must provide.

---

## 2. Key Terms

- **Episode**: One complete benchmark run — all scenarios × all trials for a
  given model. An episode starts fresh and cleans up after itself.
- **Trial**: One execution of one scenario. A trial gets its own environment,
  agent state, user state, trace, and observer. Nothing persists between trials.
- **Scenario**: A JSON file defining the test case. Read-only during execution.
- **Environment**: The simulated world (database, tools, policy). Created fresh
  per-trial from the scenario JSON.

---

## 3. Isolation Requirements

### 3.1 Environment isolation (per-trial)

Every trial MUST get a completely fresh environment:

- A new `db` dict deep-copied from the domain `db.json` + scenario patch
- A new tool function map
- A new policy text load
- No shared mutable state between trials

**How this works today:**
- `scenario_loader.load()` re-reads the scenario JSON, re-loads `db.json`,
  re-applies `initial_state_patch` via `deep_merge`, and returns a new env dict
- `load_domain().get_environment(task)` calls `load()` per-task, producing
  fresh state
- `runner._run_one()` calls `get_environment(task)` at the start of each trial

**What could go wrong:**
- Shared mutable references between trials (e.g., if `deep_merge` returned a
  reference to the base instead of a copy)
- Tool functions closing over shared state
- Environment mutations leaking between parallel trials

**Invariant:** After `get_environment(task)` returns, no mutation to that env
can affect any other env instance. This is enforced by `deep_merge` which
does `copy.deepcopy(base)`.

### 3.2 Agent isolation (per-trial)

Every trial MUST get independent agent state:

- `agent.init_state()` is called fresh with system messages and tools
- No conversation history carries over between trials
- No seed state carries over

**How this works today:**
- For sequential execution (`max_concurrency=1`): a single agent instance is
  reused, but `init_state()` creates a fresh state dict each time. The agent
  instance has no state that persists between `init_state()` calls except `_seed`,
  which is set once and doesn't mutate.
- For parallel execution (`max_concurrency>1`): `agent_factory()` creates a
  fresh agent instance per-trial.

**What could go wrong:**
- Agent implementations that cache conversation state on `self`
- Shared HTTP clients or connection pools
- LLM API-level caching (provider-dependent, not in our control)

**Invariant:** After `agent.init_state()`, the agent's behavior must be
identical to a brand-new agent instance with the same seed.

### 3.3 User simulator isolation (per-trial)

Every trial MUST get independent user state:

- `user.init_state(scenario)` is called fresh
- `turn_count` starts at 0 for new trials (or at the correct position for resume)
- `pressure_script` is read from the scenario, not carried over

**How this works today:**
- `ScriptedUser.init_state()` returns a new state dict with `turn_count=0`
- `LiteLLMUser.init_state()` returns a new state dict with fresh messages

### 3.4 Trace & observer isolation (per-trial)

Every trial MUST get a fresh trace and observer:

- `TraceRecorder()` is created fresh
- `create_observer(env, trace)` is created fresh
- No trace entries carry over between trials

**How this works today:**
- `runner._run_one()` creates fresh trace and observer via `observer_factory(env)`
- The default factory creates `TraceRecorder()` + `create_observer()` each time

### 3.5 Scenario file isolation (read-only)

Scenario JSON files are NEVER modified during execution:

- `load()` reads the file, parses it, and builds in-memory objects
- No writes back to the scenario file
- No writes to domain `db.json`, `tools.json`, or `policy.md`

---

## 4. Reproducibility Requirements

### 4.1 Seeding

- Every trial receives a deterministic seed derived from `(base_seed, task_id, trial_index)`
- `runner.seeds.derive_trial_seeds()` produces the seed sequence
- `agent.set_seed(seed)` is called before each trial
- `user.set_seed(seed)` is called before each trial (when applicable)

**What this controls:**
- The seed is passed to the LLM API (e.g., OpenAI `seed` parameter)
- This makes LLM responses deterministic *when the provider supports it*
- OpenAI documents seed support but notes it is "best effort"

**What this does NOT control:**
- Provider-side non-determinism (model updates, infrastructure changes)
- Network timing affecting parallel execution order
- LLM temperature (should be 0 for benchmark runs, but not enforced)

### 4.2 Expected reproducibility

Given the same:
- scenario files
- model name and version
- seed
- max_steps
- observer_mode

The benchmark SHOULD produce identical results across runs. In practice,
LLM non-determinism means results will vary slightly. The benchmark should
report confidence intervals when `num_trials > 1` to quantify this.

### 4.3 Repeatability operators

pi-bench already provides operators to measure consistency:
- `PolicyPassAll^k`: passes in ALL k trials (safety-critical)
- `PolicyPassAny^k`: passes in at least one trial (retry-capable)
- `ViolationEver^k`: violates in ANY trial (tail risk)

These are computed by `metrics.compute_repeatability()`.

---

## 5. Parallel Execution Safety

### 5.1 What is safe to parallelize

- Different scenarios (different tasks) can run in parallel — they have
  independent environments, agents, users, traces
- Different trials of the same scenario can run in parallel — each gets
  its own env, agent, user, trace

### 5.2 What requires isolation

When `max_concurrency > 1`:
- `agent_factory` MUST be provided (creates fresh agent per thread)
- `user_factory` MUST be provided if using LLM user sim
- The runner raises `ValueError` if `max_concurrency > 1` without `agent_factory`

### 5.3 Thread-safe components

| Component | Thread-safe? | Notes |
|---|---|---|
| `scenario_loader.load()` | Yes | Reads files, no shared state |
| `create_environment()` | Yes | Returns new dict each call |
| `TraceRecorder` | Per-trial instance | Not shared between trials |
| `LiteLLMAgent` | No (mutable `_seed`) | Use `agent_factory` for parallel |
| `ScriptedUser` | No (mutable `_seed`) | Use `user_factory` for parallel |
| `litellm.completion()` | Yes | Thread-safe per litellm docs |
| Checkpoint saving | Yes | `save_lock` mutex protects writes |

---

## 6. Episode Lifecycle

```
EPISODE START
  ├─ Load domain (read scenario files, build task list)
  ├─ For each (task, trial) in work queue:
  │   ├─ Create fresh environment from scenario JSON
  │   ├─ Create fresh agent (or via factory for parallel)
  │   ├─ Create fresh user simulator
  │   ├─ Create fresh trace + observer
  │   ├─ Run orchestrator (agent ↔ user ↔ environment loop)
  │   ├─ Evaluate trace against scenario checks
  │   ├─ Record result
  │   └─ (environment, agent state, user state, trace — all discarded)
  ├─ Aggregate metrics across all trials
  ├─ Compute repeatability (if num_trials > 1)
  └─ Report
EPISODE END (nothing persists except the saved results file)
```

No global state survives between episodes. No trial state survives between
trials. The only persistent output is the results JSON file (if `--save-to`
is specified).

---

## 7. Testing Isolation

### 7.1 How to verify environment isolation

```python
# Run same scenario twice, verify envs are independent
env1 = load("scenarios/finra/scen_010.json")["env"]
env2 = load("scenarios/finra/scen_010.json")["env"]
env1["db"]["customer_profile"]["tier"] = "MUTATED"
assert env2["db"]["customer_profile"]["tier"] != "MUTATED"
```

### 7.2 How to verify reproducibility

```bash
# Run same scenario 10 times with same seed, compare results
for i in $(seq 1 10); do
  pi run scenarios/finra/scen_010.json --agent-llm gpt-4o-mini --seed 42 --save-to /tmp/run_$i.json
done
# All should produce identical tool call sequences and decisions
```

### 7.3 How to verify no cross-scenario contamination

```bash
# Run scenario A alone, then A+B together, results for A should match
pi run scenarios/finra/scen_010.json --save-to /tmp/alone.json --seed 42
pi run-domain finra --save-to /tmp/together.json --seed 42
# Compare scen_010 result in both
```

---

## 8. Known Limitations

1. **LLM non-determinism**: Even with seed, providers may not return identical
   responses. Temperature should be 0 for benchmarking but is not enforced by
   the CLI (can be set via `--agent-llm-args temperature=0`).

2. **Model version drift**: Provider model updates (e.g., gpt-4o-mini gets
   updated) will change results. The benchmark should record the exact model
   version in results metadata.

3. **Rate limiting**: Parallel execution may hit provider rate limits, causing
   some trials to fail while others succeed. Use `--retry-failed` to mitigate.

4. **Clock-dependent scenarios**: Scenarios using `environment_setup.now` are
   deterministic (the time is injected from the JSON, not read from the system
   clock). But if any tool implementation reads `datetime.now()` instead of
   `db["now"]`, that would break reproducibility.
