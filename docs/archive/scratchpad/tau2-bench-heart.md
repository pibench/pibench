# tau2-bench: The Heart

## The One File

**`src/tau2/orchestrator/orchestrator.py`** (661 lines)

This is the single file where Agent, User, and Environment all converge. Everything else is a leaf node — the Orchestrator is the trunk.

---

## What It Does (in plain English)

The Orchestrator is a **message router**. It passes messages between three actors in a loop until someone says stop (or things break).

```
Agent ←→ Orchestrator ←→ User
              ↕
         Environment
```

### The Core Loop (2 methods, that's it)

**`run()`** — starts the simulation, loops `step()`, wraps results into `SimulationRun`

**`step()`** — routes ONE message. Three paths:

| From | To | What happens |
|------|-----|-------------|
| AGENT/ENV | USER | User generates response. If tool call → ENV, else → AGENT |
| USER/ENV | AGENT | Agent generates response. If tool call → ENV, else → USER |
| AGENT/USER | ENV | Environment executes tool calls, returns results back to caller |

That's the entire simulation engine.

---

## State the Orchestrator Tracks

```python
self.trajectory      # list[Message] — full conversation history
self.db_snapshots    # list[DBSnapshot] — DB state after each tool call
self.agent_state     # opaque — LLM conversation state
self.user_state      # UserState — user simulator's conversation state
self.from_role       # who sent the current message
self.to_role         # who receives the current message
self.message         # the current message being routed
self.step_count      # how many steps taken
self.num_errors      # tool execution errors
self.done            # simulation finished?
self.termination_reason  # why it stopped
```

---

## Message Types

| Type | Sent by | Contains |
|------|---------|----------|
| `AssistantMessage` | Agent | text OR tool_calls (never both) |
| `UserMessage` | User | text OR tool_calls (never both) |
| `ToolMessage` | Environment | tool execution result |
| `MultiToolMessage` | Environment | wraps multiple ToolMessages |

**Key rule**: Messages have EITHER text OR tool_calls, never both, never empty.

---

## Termination Reasons

| Reason | Trigger |
|--------|---------|
| `AGENT_STOP` | Agent sends `###STOP###` |
| `USER_STOP` | User sends `###STOP###` |
| `MAX_STEPS` | `step_count >= max_steps` |
| `TOO_MANY_ERRORS` | `num_errors >= max_errors` |
| `AGENT_ERROR` | Agent violates protocol |
| `USER_ERROR` | User violates protocol |

---

## Execution Flow: `tau2 run` → Orchestrator

```
cli.py:main()
  → run.py:run_domain(RunConfig)
    → run.py:run_task() [per task × trial]
      → Creates Orchestrator(agent, user, env, task)
      → orchestrator.run()  ← THE LOOP
      → evaluate_simulation(SimulationRun)
      → Returns scored SimulationRun
    → Aggregates metrics, saves JSON
```

---

## The Three Actors (what Orchestrator calls on them)

### Agent (`agent/base.py`, `agent/llm_agent.py`)
- `generate_next_message(message, state) → (AssistantMessage, new_state)`
- `get_init_state(message_history) → state`
- `is_stop(message) → bool`
- `stop(message, state)` — cleanup

### User (`user/base.py`, `user/user_simulator.py`)
- `generate_next_message(message, state) → (UserMessage, new_state)`
- `get_init_state(message_history) → UserState`
- `is_stop(message) → bool` (static: checks for `###STOP###`)
- `stop(message, state)` — cleanup

### Environment (`environment/environment.py`)
- `get_response(tool_call) → ToolMessage`
- `set_state(init_data, init_actions, message_history)`
- `get_db_hash() → str`
- `sync_tools()`

---

## Solo Mode

Agent works alone (no user). `DummyUser` is a no-op placeholder. Agent can ONLY make tool calls — sending text (except `###STOP###`) is an error.

---

## What `initialize()` Does

1. Loads task's initial state (DB data, prior message history)
2. Initializes environment with that state
3. Sets seeds for reproducibility
4. Determines who speaks first based on message history (or defaults to Agent saying "Hi!")
5. Initializes agent_state and user_state with appropriate message history slices
6. Captures system prompts
7. Takes initial DB snapshot
8. Validates communication protocol if enabled

---

## Key Insight: Why This File Is the Heart

Every other file does ONE thing:
- `agent/` — wraps an LLM call
- `user/` — wraps another LLM call (simulating a human)
- `environment/` — executes tool calls against a DB
- `evaluator/` — scores the result after the fact
- `run.py` — plumbing (concurrency, CLI glue)
- `data_model/` — Pydantic schemas

**Only the Orchestrator connects them all.** It defines the protocol, the loop, the state transitions, the termination logic. If you're building your own benchmark, this is the file to understand (and potentially fork/replace).

---

## File Dependency Map

```
orchestrator.py imports from:
  ├── agent/base.py         (BaseAgent, AgentError)
  ├── agent/llm_agent.py    (LLMSoloAgent)
  ├── data_model/message.py (AssistantMessage, UserMessage, ToolMessage, MultiToolMessage)
  ├── data_model/simulation.py (DBSnapshot, SimulationRun, TerminationReason)
  ├── data_model/tasks.py   (Task, EnvFunctionCall, InitializationData)
  ├── environment/environment.py (Environment, EnvironmentInfo)
  ├── user/base.py          (BaseUser, UserError)
  ├── user/user_simulator.py (DummyUser, UserSimulator, UserState)
  └── utils/                (get_cost, format_time, get_now)
```

Everything flows IN to the orchestrator. Nothing flows out except `SimulationRun`.
