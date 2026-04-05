# Hooks — Sprint & Task Breakdown

Source spec: `docs/specs/hooks.md`
Source blueprint: `docs/plans/hooks-blueprint.md`

---

## Sprint 1: Hook Registry + Orchestrator Integration

**Goal:** The orchestrator accepts hooks and invokes them at named
points. A registry validates and manages hook registration. All 9
BDD scenarios pass. Hardcoded concerns still present (removed in
Sprint 2 after plugins exist to replace them).

**Demo:** Run a simulation with a logging plugin that prints at each
hook point. Run without plugins — same trajectory.

### Task 1.1: Create pi_plugins package with HookRegistry

**Scope:** Create `workspace/src/pi_plugins/__init__.py` and
`workspace/src/pi_plugins/registry.py` with:
- `HookRegistry(hook_names: list[str])` — constructor
- `register(hook_name: str, fn: Callable) -> None` — validates name, appends fn
- `register_plugin(plugin: dict[str, Callable]) -> None` — bulk register
- `to_dict() -> dict[str, list[Callable]]` — export for orchestrator
- `invoke_hooks(hooks: dict, name: str, context: dict) -> None` — call all fns, catch exceptions

**Acceptance criteria:**
- `register("on_init", fn)` succeeds
- `register("on_banana", fn)` raises `ValueError` with "on_banana" in message
- `to_dict()` returns plain dict with registered callables in insertion order
- `invoke_hooks` calls all fns for a hook point
- If one fn raises, remaining fns still execute and simulation continues

**Validation:** BDD scenarios 1, 3, 4, 6, 7 pass.

### Task 1.2: Add hooks parameter to orchestrator run()

**Scope:** Modify `orchestrator/core.py`:
- `run()` accepts `hooks: dict[str, list[Callable]] | None = None`
- Store `hooks or {}` in `state["hooks"]`
- Import `invoke_hooks` from `pi_plugins.registry` — NO. Instead,
  inline a 5-line `_fire_hooks(state, name, context)` function in
  core.py that iterates `state["hooks"].get(name, [])`. This keeps
  pi_bench free of pi_plugins imports.

Modify `orchestrator/routing.py`:
- Call `_fire_hooks` at each routing boundary
- Build context dicts as fresh copies at each point

**Hook points and context shapes:**

| Hook | When | Context Keys |
|------|------|-------------|
| `on_init` | After state setup | `trajectory, agent_system_prompt, user_system_prompt, env, tools` |
| `before_agent_call` | Before agent.generate() | `current_message, step_count, trajectory` |
| `after_agent_call` | After agent.generate() | `message, step_count, trajectory` |
| `before_user_call` | Before user.generate() | `current_message, step_count, trajectory` |
| `after_user_call` | After user.generate() | `message, step_count, trajectory` |
| `before_tool_call` | Before each make_tool_call() | `tool_name, arguments, requestor, env` |
| `after_tool_call` | After each make_tool_call() | `tool_name, arguments, result, requestor, env` |
| `on_done` | After loop ends | `trajectory, termination_reason, duration, step_count` |

**Acceptance criteria:**
- `run(..., hooks=None)` works identically to current behavior
- `run(..., hooks=registry.to_dict())` invokes all registered callables
- Context dicts are shallow copies — plugin mutations don't affect state
- `trajectory` in context is a copy of the list (not a reference)
- No `pi_plugins` import in any `pi_bench/` file
- Hook invocation order matches registration order

**Validation:** All 9 BDD scenarios GREEN.

---

## Sprint 2: Built-in Plugins + Clean Orchestrator

**Goal:** All hardcoded concerns move to plugins. Running with all
built-in plugins produces output equivalent to the pre-hooks
orchestrator. The orchestrator is clean — pure routing.

**Demo:** Run a simulation with all 4 plugins enabled. Output includes
db_snapshots, system prompts, costs, trace — same as before hooks.

### Task 2.1: DB snapshot plugin

**Scope:** Create `workspace/src/pi_plugins/db_snapshot.py`:
- `db_snapshot_plugin() -> dict[str, Callable]`
- Hooks: `on_init` (capture initial state), `after_tool_call` (capture post-tool state)
- Accumulates snapshots in a closure list
- Plugin exposes `get_snapshots() -> list[dict]`

**Acceptance criteria:**
- Registers for `on_init` and `after_tool_call`
- After simulation, `get_snapshots()` returns init + per-tool snapshots
- Snapshot includes trigger, turn_idx, db_hash, db_state
- Output matches the hardcoded DB snapshots from current orchestrator

**Validation:** Unit test — run simulation, compare plugin snapshots to hardcoded ones.

### Task 2.2: Prompt capture plugin

**Scope:** Create `workspace/src/pi_plugins/prompt_capture.py`:
- `prompt_capture_plugin() -> dict[str, Callable]`
- Hook: `on_init` — reads system prompts from context
- Exposes `get_prompts() -> dict` with agent_system_prompt, user_system_prompt

**Acceptance criteria:**
- After simulation, `get_prompts()` returns both prompts
- Agent prompt is the policy + task description joined
- User prompt is user_scenario as JSON (or None)

**Validation:** Unit test — verify captured prompts match current init.py output.

### Task 2.3: Cost tracking plugin

**Scope:** Create `workspace/src/pi_plugins/cost_tracking.py`:
- `cost_tracking_plugin() -> dict[str, Callable]`
- Hook: `on_done` — sums costs from trajectory
- Exposes `get_costs() -> dict` with agent_cost, user_cost

**Acceptance criteria:**
- After simulation, costs match `sum_cost()` output
- Messages without `cost` field contribute 0.0

**Validation:** Unit test — mock messages with known costs, verify sums.

### Task 2.4: Trace recorder plugin

**Scope:** Create `workspace/src/pi_plugins/trace_recorder.py`:
- `trace_recorder_plugin(trace: TraceRecorder) -> dict[str, Callable]`
- Hooks: `before_tool_call` (capture pre-hash), `after_tool_call` (record entry)
- Bridges existing `pi_bench.trace.TraceRecorder` to the hook system

**Acceptance criteria:**
- After simulation, trace has entries for each tool call
- Each entry has pre/post hashes, tool name, arguments, result, requestor
- Output matches current observer trace recording from routing.py

**Validation:** Unit test — run simulation with plugin, verify trace entries.

### Task 2.5: Remove hardcoded concerns from orchestrator

**Scope:** Now that plugins exist, remove hardcoded code:

From `orchestrator/init.py`:
- Remove system prompt capture (lines building agent_system_prompt, user_system_prompt)
- Remove DB snapshot init (snapshot_db call)

From `orchestrator/routing.py`:
- Remove observer trace recording (pre_hash, is_observed, trace.record block)
- Remove DB snapshot per-tool-call (snapshot_db call)

From `orchestrator/core.py`:
- Remove agent_cost, user_cost from output (sum_cost calls)
- Remove agent_system_prompt, user_system_prompt, db_snapshots from output

From `orchestrator/helpers.py`:
- Remove snapshot_db, unwrap_env, is_observed (moved to plugins)
- Keep sum_cost if runner still needs it, else remove

**Acceptance criteria:**
- `run()` output has only core fields: id, task_id, messages,
  termination_reason, duration, step_count, trial, seed
- No observer/snapshot/cost code in orchestrator
- pi_bench has no import of pi_plugins

**Validation:** BDD scenario 9 still passes. Run with all 4 plugins —
output equivalent to pre-cleanup.

### Task 2.6: Integration — all plugins together

**Scope:** Integration test verifying all 4 plugins work simultaneously.

**Acceptance criteria:**
- Same trajectory with or without plugins
- All 4 plugin outputs (snapshots, prompts, costs, trace) are correct
- Plugins don't interfere with each other
- No fields lost compared to pre-hooks orchestrator output

**Validation:** Integration test — run with all plugins, compare to
hardcoded baseline from before Sprint 1.

---

## Summary

| Sprint | Tasks | Demoable Output |
|--------|-------|-----------------|
| 1 | 2 tasks | Hook system works. Plugins can observe. |
| 2 | 6 tasks | Hardcoded code removed. All functionality via plugins. |

Total: 8 atomic tasks, 2 sprints.

## Also (from review)

- Replace `Any` types with `AgentProtocol`/`UserProtocol` in
  orchestrator signatures (separate cleanup task, not part of hooks)
- Solo mode stays — needed for agent-only policy scenarios
