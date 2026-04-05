# tau2-bench Understanding

Reference codebase: `reference/tau2-bench/` (v0.2.1.dev0, installed as editable package)

## Architecture: 3-Role Simulation Loop

```
Agent (LLM under test)  <-->  Environment (deterministic)  <-->  User Simulator (LLM customer)
                    \_______________Orchestrator________________/
```

- **Agent** reads a domain policy (free-form text) and has access to tools
- **User Simulator** is an LLM playing the customer, driven by a scenario script
- **Environment** holds an in-memory DB and dispatches tool calls deterministically

## Core Classes

| Class | File | Role |
|---|---|---|
| `BaseAgent` | `src/tau2/agent/base.py` | ABC with `generate_next_message(message, state)` |
| `LLMAgent` | `src/tau2/agent/llm_agent.py:51` | Standard agent: reads policy, uses tools |
| `LLMGTAgent` | `src/tau2/agent/llm_agent.py:155` | Ground-truth agent given expected resolution steps |
| `LLMSoloAgent` | `src/tau2/agent/llm_agent.py:313` | No-user mode, uses a ticket, calls `done()` to stop |
| `BaseUser` | `src/tau2/user/base.py:97` | ABC for user simulators |
| `UserSimulator` | `src/tau2/user/user_simulator.py:66` | LLM-driven customer (roles flipped before LLM call) |
| `DummyUser` | `src/tau2/user/user_simulator.py:194` | No-op, used in solo mode |
| `Environment` | `src/tau2/environment/environment.py:34` | Holds DB + ToolKit, dispatches tool calls |
| `ToolKitBase` | `src/tau2/environment/toolkit.py:65` | Metaclass auto-discovers `@is_tool` decorated methods |
| `DB` | `src/tau2/environment/db.py:7` | Pydantic model with `load(path)` and `get_hash()` |
| `Orchestrator` | `src/tau2/orchestrator/orchestrator.py` | Main simulation loop |
| `Task` | `src/tau2/data_model/tasks.py:399` | Scenario definition + evaluation criteria |
| `Registry` | `src/tau2/registry.py:207` | Global singleton mapping names to constructors |

## Simulation Flow

```
tau2 run  -->  cli.py:main()
           -->  run.py:run_domain()
           -->  run.py:run_tasks()          # ThreadPoolExecutor for parallelism
           -->  run.py:run_task()            # single task
           -->  Orchestrator.run()
           -->  evaluate_simulation()
```

### Orchestrator.run() (orchestrator.py:386)

```
initialize()                    # load DB state, run init actions, seed conversation
while not done:
    step()                      # one message exchange between roles
    check termination           # max_steps, max_errors, stop tokens
stop agent and user
build SimulationRun
```

### Orchestrator.step() (orchestrator.py:449)

Three routing cases per step:

| from --> to | Action |
|---|---|
| AGENT/ENV --> USER | `user.generate_next_message(message, state)` |
| USER/ENV --> AGENT | `agent.generate_next_message(message, state)` |
| AGENT/USER --> ENV | `environment.get_response(tool_call)` for each tool call |

Termination: `###STOP###` from agent or user, `max_steps`, or `max_errors`.

## Environment Internals

### Tool Discovery

`@is_tool(ToolType.READ/WRITE/GENERIC/THINK)` decorator marks methods as tools.
The `ToolKitType` metaclass auto-discovers all decorated methods at class definition time.

### get_response (environment.py:390)

Catches exceptions, serializes result to JSON, returns `ToolMessage(error=True/False)`.
Unknown tools or invalid arguments produce `error=True` without crashing.

### Database

`DB` is a Pydantic model loaded from JSON. `get_hash()` returns a deterministic hash of the full state.
`set_state()` replays initialization data + actions to reach a known starting point.

## Mock Domain

Data files in `data/tau2/domains/mock/`:
- `db.json` -- initial database state
- `policy.md` -- free-form policy text the agent reads
- `tasks.json` -- scenario definitions with evaluation criteria

### DB Shape

```json
{
  "tasks": { "task_1": { "task_id", "title", "description", "status" } },
  "users": { "user_1": { "user_id", "name", "tasks": ["task_1"] } }
}
```

`TaskStatus = Literal["pending", "completed"]`

### Tools (6 total, defined in domains/mock/tools.py)

| Method | ToolType | Description |
|---|---|---|
| `get_users()` | READ | Returns all users |
| `create_task(user_id, title, description)` | WRITE | Creates task, attaches to user |
| `update_task_status(task_id, status)` | WRITE | Changes task status |
| `transfer_to_human_agents(summary)` | GENERIC | Returns "Transfer successful" |
| `assert_number_of_tasks(user_id, n)` | assertion-only | Returns bool (not an agent tool) |
| `assert_task_status(task_id, status)` | assertion-only | Returns bool (not an agent tool) |

The `assert_*` methods are NOT decorated with `@is_tool` -- they are only called by the evaluator via `run_env_assertion`, never by the agent.

## Evaluation (Fully Deterministic)

Entry: `evaluator/evaluator.py:evaluate_simulation()` (line 21)

If termination reason is not `AGENT_STOP` or `USER_STOP`, reward = 0.0 immediately.

### Four Evaluators

1. **DB Hash Check** (`evaluator_env.py`)
   - Replays predicted trajectory through environment --> gets predicted DB hash
   - Replays gold actions through environment --> gets gold DB hash
   - Match = 1.0, mismatch = 0.0

2. **Env Assertions** (`evaluator_env.py`)
   - Calls assertion functions on the predicted final environment
   - Each assertion is a function returning bool with an expected value
   - Example: `assert_task_status("task_1", "completed") == True`

3. **Action Matching** (`evaluator_action.py`)
   - Extracts all `ToolCall` objects from full trajectory
   - Checks each golden action was made by the agent (name + args)
   - `compare_args` allows partial argument matching (avoids false negatives from optional fields)
   - All golden actions must be found --> 1.0, else 0.0

4. **Communicate Check** (`evaluator_communicate.py`)
   - Case-insensitive substring search across all AssistantMessage.content
   - All required strings must appear --> 1.0, else 0.0

### Reward Combination

```
reward = db_reward * env_assertion_reward * action_reward * communicate_reward
```

Only multiplied when that `RewardType` is in `task.evaluation_criteria.reward_basis`.

### RewardInfo (what gets saved)

```python
reward: float                           # final combined reward
db_check: DBCheck                       # db_match bool + db_reward float
env_assertions: list[EnvAssertionCheck]
action_checks: list[ActionCheck]
communicate_checks: list[CommunicateCheck]
reward_breakdown: dict[RewardType, float]
```

## Task Data Model

```python
class Task:
    id: str
    user_scenario: UserScenario            # sent to UserSimulator
    ticket: Optional[str]                  # for solo mode
    initial_state: Optional[InitialState]  # DB data + actions + message history
    evaluation_criteria: Optional[EvaluationCriteria]

class EvaluationCriteria:
    actions: list[Action]                  # expected tool calls
    env_assertions: list[EnvAssertion]     # post-run DB state assertions
    communicate_info: list[str]            # strings agent must say
    nl_assertions: list[str]              # NL assertions (WIP, LLM judge)
    reward_basis: list[RewardType]         # which checks to combine

class Action:
    action_id, requestor, name, arguments
    compare_args: Optional[list[str]]      # partial arg matching
```

Scenario labels: `ALLOW` / `DENY` / `ESCALATE`

## CLI Reference

| Command | What it does |
|---|---|
| `tau2 run --domain mock --agent llm_agent --agent-llm anthropic/claude-sonnet-4-20250514` | Run simulations |
| `tau2 view` | Interactive terminal viewer of simulation runs |
| `tau2 check-data` | Verify data directory integrity |
| `tau2 play` | You play the agent role manually |
| `tau2 domain <name>` | Print domain policy + tool descriptions |
| `tau2 evaluate-trajs <paths>` | Re-evaluate saved trajectories |

Key flags: `--task-ids`, `--num-trials`, `--max-concurrency`, `--save-to`

## Design Decisions Relevant to pi-bench

1. **pi-bench tasks use `ENV_ASSERTION` in reward_basis, not `DB` hash** -- DENY scenarios expect the DB to stay unchanged; assertion functions are more expressive for checking that something did *not* happen.

2. **`compare_args` in Action** avoids false negatives from optional fields (directly addresses the DB hash mismatch issue where the agent added an optional `description` field).

3. **`initialization_actions`** in `InitialState` set up preconditions (e.g., mark a task as completed before the scenario starts).

4. **User simulator flips roles** -- it calls the LLM as "assistant" then wraps the response as a `UserMessage`. The `simulation_guidelines.md` is the user's behavioral policy.

5. **No LLM judge in production evaluation** -- `nl_assertions` exist but are marked WIP/experimental. All four production evaluators are deterministic.
