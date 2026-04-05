# Hooks

## Problem

The pi-bench orchestrator hardcodes concerns that don't belong in the
routing loop: DB snapshots, system prompt capture, observer trace
recording, cost tracking. These are useful but they couple the core to
specific observation strategies. Adding a new concern (e.g., a hotel
domain plugin, latency tracking, token counting) requires modifying
the orchestrator — the one module that should be stable.

## Requirements

- The orchestrator defines named hook points at its natural boundaries
  (init, before/after agent call, before/after user call, before/after
  tool call, on done)
- Plugins register callables for the hook points they care about
- Multiple plugins can register for the same hook point
- Plugins receive the relevant state at each hook point (not the full
  orchestrator internals — just what that hook exposes)
- The hook system is a separate package outside `pi_bench/`
- pi-bench core has zero dependency on any plugin — it works with no
  plugins registered
- Existing functionality (DB snapshots, trace recording, prompt capture,
  cost tracking) becomes plugins, not core code

## Non-Requirements

- No hook ordering/priority (plugins don't depend on each other)
- No hook return values that modify orchestrator behavior (hooks
  observe, they don't control flow)
- No async hooks (orchestrator is synchronous)
- No dynamic hook registration mid-simulation (register before run,
  not during)
- Not using pluggy or any external dependency — the mechanism is simple
  enough to be a plain Python module

## Behavioral Contracts

### Hook Registration

- A plugin registers for one or more named hook points before a
  simulation starts
- A simulation with no plugins registered runs identically to the
  current orchestrator (routing only, no snapshots, no trace)
- Registering a plugin that references a non-existent hook point
  raises an error at registration time, not at call time

### Hook Invocation

- Every registered callable for a hook point is called when that point
  is reached during simulation
- Hook callables receive a read-only snapshot of the relevant state
  (not a mutable reference to orchestrator internals)
- A plugin that raises an exception does not crash the simulation —
  the error is captured and the simulation continues
- Hook invocation order matches registration order

### Isolation

- Removing all plugins from a simulation produces the same trajectory
  and reward as running without the hook system
- A plugin cannot modify the orchestrator's routing decisions, message
  trajectory, or evaluation results
- pi-bench core (`pi_bench/`) has no import of the plugin package

## Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Separate package | Plugins live outside `pi_bench/` | pi-bench core stays self-contained; plugins are optional extensions |
| No pluggy dependency | Plain callables + a registry dict | The mechanism is ~30 lines; a dependency adds complexity without value |
| Observe-only hooks | Hooks cannot modify state | Prevents plugins from introducing non-determinism into the simulation |
| Named hook points | Fixed set of hook specs in orchestrator | The orchestrator knows its own boundaries; plugins don't invent new ones |
| Read-only snapshots | Hooks get copies/views, not references | Prevents accidental mutation of simulation state |
| Fail-safe invocation | Plugin exceptions are caught | One broken plugin shouldn't invalidate a benchmark run |
