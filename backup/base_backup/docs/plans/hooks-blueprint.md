# Hooks — Blueprint

Source spec: `docs/specs/hooks.md`
Reference system: pluggy (pytest's hook system) — studied for pattern, not used as dependency

## Context

pi-bench's orchestrator currently hardcodes DB snapshots, observer trace
recording, system prompt capture, and cost tracking directly in its
routing logic. This blueprint adds named hook points to the orchestrator
and moves all non-routing concerns into plugins that live in a separate
package (`pi_plugins/`) outside `pi_bench/`.

## Goals

- Orchestrator defines named hook points at its natural boundaries
- Plugins register callables for hook points they care about
- pi-bench core works with zero plugins (pure routing)
- Existing functionality migrates to plugins

## Non-Goals

- Hook ordering/priority
- Hooks that modify orchestrator behavior (observe-only)
- Async hooks
- Dynamic mid-simulation registration
- External dependency (pluggy, etc.)

## Cross-Cutting Concerns

**Error handling:** Plugin exceptions are caught and logged. A broken
plugin never crashes a simulation. The orchestrator wraps every hook
invocation in try/except.

## NOT Building

- **Middleware chain** — hooks observe, they don't intercept or modify.
  No need for request/response wrapping.
- **Event bus / pub-sub** — overkill. Named call points with direct
  function calls are sufficient.
- **Plugin discovery** — plugins are registered explicitly in code, not
  discovered from entry points or file scanning.

---

## Component: Hook Registry

### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| Plain dict `{name: [fns]}` passed to orchestrator | Zero abstraction, obvious | No validation of hook names |
| Registry class with `register()` + validation | Catches typos at registration, encapsulates invocation | One more type |
| Decorator-based (pluggy-style) | Familiar pattern | Over-engineered for ~8 hook points |

**Decision:** Registry class. It validates hook names at registration
time (spec contract requires this), encapsulates fail-safe invocation,
and provides a clean `create_hooks_dict()` to hand to the orchestrator.
The orchestrator itself only sees a plain dict — the Registry is the
external-facing API.

**Gradient source:** pluggy's PluginManager — register impls against
specs, validate at registration time.

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `HookRegistry.__init__` | `(hook_names: list[str]) -> None` | Create registry with valid hook names |
| `HookRegistry.register` | `(hook_name: str, fn: Callable) -> None` | Register a callable for a hook point; raises on invalid name |
| `HookRegistry.register_plugin` | `(plugin: dict[str, Callable]) -> None` | Register multiple hooks from a plugin dict |
| `HookRegistry.to_dict` | `() -> dict[str, list[Callable]]` | Export as plain dict for the orchestrator |
| `invoke_hooks` | `(hooks: dict[str, list[Callable]], name: str, context: dict) -> None` | Call all registered fns for a hook point; catches exceptions |

### Data Types

| Type | Fields |
|------|--------|
| `HookRegistry` | `_valid_names: set[str], _hooks: dict[str, list[Callable]]` |

### Contract Map

| Spec Contract | Satisfied By |
|---------------|-------------|
| "A plugin registers for one or more named hook points" | `HookRegistry.register()`, `HookRegistry.register_plugin()` |
| "Registering a plugin that references a non-existent hook point raises an error" | `HookRegistry.register()` validates against `_valid_names` |
| "Every registered callable is called when that point is reached" | `invoke_hooks()` iterates all fns |
| "A plugin that raises an exception does not crash the simulation" | `invoke_hooks()` wraps each call in try/except |
| "Hook invocation order matches registration order" | `_hooks` uses list (preserves insertion order) |

---

## Component: Hook Points (orchestrator integration)

### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| Add `hooks` param to `run()` only | Minimal change to core | Must thread through to routing fns |
| Store hooks in state dict | Available everywhere, no param threading | Mixes hook config into simulation state |
| Pass hooks to `step()` as well | Explicit | More params |

**Decision:** Store in state dict under `state["hooks"]`. The state dict
already flows through all routing functions. Hooks are set once at init
and never change — storing them in state avoids threading a new param
through every internal function. Default is `{}` (empty dict, no hooks).

**Gradient source:** The existing orchestrator pattern — state dict
carries all per-simulation config.

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `run` | `(..., hooks: dict | None = None) -> dict` | Accepts optional hooks dict |
| (internal) | `invoke_hooks(state, name, context)` called at each point | Fires hooks from `state["hooks"]` |

### Hook Points & Context

| Hook Name | When | Context Keys |
|-----------|------|-------------|
| `on_init` | After state setup | `trajectory, agent_system_prompt, user_system_prompt, env_info` |
| `before_agent_call` | Before `agent.generate()` | `current_message, step_count, trajectory` |
| `after_agent_call` | After `agent.generate()` | `message, step_count, trajectory` |
| `before_user_call` | Before `user.generate()` | `current_message, step_count, trajectory` |
| `after_user_call` | After `user.generate()` | `message, step_count, trajectory` |
| `before_tool_call` | Before `make_tool_call()` | `tool_name, arguments, requestor` |
| `after_tool_call` | After `make_tool_call()` | `tool_name, arguments, result, requestor, env` |
| `on_done` | After simulation loop ends | `trajectory, termination_reason, duration, step_count` |

### Contract Map

| Spec Contract | Satisfied By |
|---------------|-------------|
| "Hook callables receive a read-only snapshot of the relevant state" | Context dicts are built fresh at each hook point (copies, not refs) |
| "A simulation with no plugins registered runs identically" | `hooks` defaults to `{}`, `invoke_hooks` is a no-op on empty dict |
| "Removing all plugins produces the same trajectory and reward" | Hooks are observe-only; no hook modifies state dict |
| "A plugin cannot modify the orchestrator's routing decisions" | Context is a fresh dict, not a reference to state |
| "pi-bench core has no import of the plugin package" | `invoke_hooks` is a 5-line function in the orchestrator that takes a plain dict |

---

## Component: Built-in Plugins

### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| One plugin per concern | Clean separation, easy to enable/disable | More files |
| One mega-plugin | Less files | Violates one-concept-per-file |

**Decision:** One plugin per concern. Each is a small module with a
function that returns a plugin dict (`{hook_name: callable}`).

**Gradient source:** engg skill — one concept per file.

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `db_snapshot_plugin` | `() -> dict[str, Callable]` | Returns hooks for `on_init` + `after_tool_call` — captures DB state |
| `prompt_capture_plugin` | `() -> dict[str, Callable]` | Returns hook for `on_init` — captures system prompts |
| `cost_tracking_plugin` | `() -> dict[str, Callable]` | Returns hook for `on_done` — sums agent/user costs |
| `trace_recorder_plugin` | `(trace: TraceRecorder) -> dict[str, Callable]` | Returns hooks for `before_tool_call` + `after_tool_call` — records trace |

### Data Types

Each plugin function returns `dict[str, Callable]` — no new types needed.
Plugins accumulate state in closures (e.g., `snapshots = []` captured
by the `after_tool_call` callable).

### Contract Map

| Spec Contract | Satisfied By |
|---------------|-------------|
| "Existing functionality becomes plugins, not core code" | Four plugins replace hardcoded code |
| "pi-bench core has no import of the plugin package" | Plugins live in `pi_plugins/`, imported by runner/CLI only |

---

## Package Structure

```
workspace/src/
  pi_bench/          # Core — self-contained, no plugin imports
    environment/
    orchestrator/    # Modified: run() accepts hooks, routing calls invoke_hooks
    evaluator/
    runner/
    types.py
    protocols.py

  pi_plugins/        # Separate package — depends on pi_bench, not vice versa
    registry.py      # HookRegistry class + invoke_hooks
    db_snapshot.py   # DB snapshot plugin
    prompt_capture.py # System prompt capture plugin
    cost_tracking.py # Cost tracking plugin
    trace_recorder.py # Trace recorder plugin (wraps existing TraceRecorder)
```
