# Core Engine Spec — pi-bench Runtime

**Date:** 2026-02-22
**What this is:** Requirements for the core simulation engine. Behavioral contracts only — no implementation decisions.

**What this is NOT:** A design doc, a class diagram, or code.

---

## Goal

Build a standalone simulation engine that runs multi-turn conversations
between an LLM agent, an LLM user simulator, and a deterministic
environment. The engine captures a full trace of all messages and tool
calls, then evaluates the trace against configurable criteria.

This engine is the foundation for pi-bench. Policy evaluation will be
layered on top later — this spec covers only the core engine.

---

## Architecture

Three roles, one orchestrator, one evaluator pipeline.

- **Agent** (LLM under test) — sees policy text, tool schemas, and the conversation
- **User Simulator** (LLM) — sees a scenario prompt and the agent's text messages
- **Environment** (deterministic) — in-memory DB and tool execution

The orchestrator routes messages between these three roles. The
environment is passive — it only responds to tool calls. Both the
agent and the user simulator can make tool calls.

After the simulation ends, the evaluator pipeline checks the trace
against expected outcomes.

---

## Data Model

### Messages

There are 5 message types: system, assistant, user, tool, and multi-tool.

Every message has a role, optional text content, and a turn index
(assigned after simulation).

**A message has EITHER text content OR tool calls. Never both. Never neither.**

#### Tool Call

A request to execute a tool. Fields:
- **id** — unique identifier (generate UUID if empty)
- **name** — tool name
- **arguments** — key-value pairs
- **requestor** — "user" or "assistant"

#### System Message

Contains system prompt text. Role is "system".

#### Assistant Message

From the agent. Has either text content or a list of tool calls.
Also tracks: cost (API cost in USD), usage (token counts).

#### User Message

From the user simulator. Same structure as assistant message — either
text content or tool calls. Also tracks cost and usage.

#### Tool Message

Result of a tool execution. Fields:
- **id** — matches the tool call's id
- **content** — tool output as a JSON string
- **requestor** — who made the call ("user" or "assistant")
- **error** — whether the execution failed

#### Multi-Tool Message

Wraps multiple tool messages when a single message contained
multiple tool calls.

### Validation

- Assistant and user messages must have content XOR tool calls (not both, not neither)
- Content must be a non-empty string if present
- Tool calls must be a non-empty list if present

### Tasks

A task defines one scenario. Contains:

- **id** — unique identifier
- **description** — purpose, relevant policies, notes
- **user scenario** — persona and instructions for the user simulator
- **ticket** — solo mode instruction (optional)
- **initial state** — how to set up the environment before the episode:
  - initialization data (override DB values)
  - initialization actions (tool calls to run during setup)
  - message history (prior conversation to resume from)
- **evaluation criteria** — what success looks like:
  - expected actions (golden tool calls the agent should make)
  - environment assertions (DB state checks)
  - communicate info (strings the agent should mention)
  - NL assertions (natural language claims about the conversation)
  - reward basis (which evaluators to use)

#### User Scenario

Contains:
- **persona** — user personality description
- **instructions** — what the user wants, what they know, what
  they don't know, and how they should behave

#### Expected Action

An expected tool call in the golden trajectory. Fields:
- **action id** — unique identifier
- **requestor** — "user" or "assistant"
- **name** — tool name
- **arguments** — expected argument values
- **compare args** — which arguments to compare (optional, defaults to all)

An action matches a tool call when: same name, same requestor, and
all compared argument values match.

#### Environment Assertion

A function call to the environment that must return a specific boolean
value. Used to check DB state after the episode.

#### Reward Types

The evaluation criteria specifies which reward types to use:
- **DB** — database state matches golden state
- **ACTION** — expected tool calls were made
- **COMMUNICATE** — required information was mentioned
- **ENV_ASSERTION** — environment assertions pass
- **NL_ASSERTION** — natural language assertions pass
- **POLICY** — policy compliance (future)

### Simulation Output

The result of running one episode. Contains:
- **id** — UUID
- **task id** — which task was run
- **timestamps** — start, end, duration
- **termination reason** — why the simulation ended (user stop, agent
  stop, max steps, too many errors, agent error, user error)
- **costs** — agent and user API costs
- **reward info** — evaluation results with per-evaluator breakdown
- **messages** — the full trajectory
- **trial and seed** — for reproducibility

A batch result contains metadata, the list of tasks, and all
simulation runs.

---

## Environment

The environment owns the in-memory database and executes tool calls.
It is deterministic — same inputs always produce same outputs.

### Capabilities

- **Execute a tool call** — takes a tool call, runs the named tool with
  the given arguments, returns a tool result. On failure, returns an
  error result instead of crashing.
- **Route by requestor** — "assistant" calls go to agent tools, "user"
  calls go to user tools.
- **State initialization** — can set up its state from: initialization
  data (DB overrides), initialization actions (setup tool calls), and
  message history (replay prior tool calls to reconstruct state).
- **Sync hook** — called after every tool execution. Allows derived
  state updates. Default behavior is no-op.
- **Domain identity** — knows its domain name and policy text.
- **Database hash** — computes a deterministic fingerprint of the
  current state, for comparing predicted vs. golden state.
- **Assertions** — can run assertion functions that check DB state
  and return boolean results.

### Tool Collection

A group of related tools that share a database.
- Look up and execute tools by name
- List all available tools and their schemas (JSON Schema format,
  for LLM function calling)
- Compute a hash of the current database state
- Update database state from a data dictionary

### Tool

A named operation. Has a name, description, parameter schema (JSON
Schema), and an implementation.

### Domain Configuration

A domain provides:
1. Policy text — markdown, injected into agent system prompt
2. Tool definitions — schemas for LLM function calling
3. Tool implementations — functions that execute against the DB
4. Initial database — starting state
5. Tasks — scenario definitions
6. Task splits — named subsets of tasks

---

## Agent

The agent is the LLM under test. It receives messages and produces
responses.

### Capabilities

- **Generate next message** — given a message and its current state,
  produces a response (either text or tool calls) and updated state
- **Initialize state** — set up from scratch or from prior message history
- **Stop detection** — can signal that it wants to end the conversation
- **Cleanup** — called when simulation ends
- **Seed** — can be set for reproducibility

The default implementation wraps an LLM via litellm. The system prompt
includes the policy text and available tool schemas.

---

## User Simulator

The user simulator is an LLM that pretends to be a customer. It
receives the agent's text messages and responds according to its
scenario.

### Capabilities

- **Generate next message** — given an agent message and its state,
  produces a user response and updated state
- **Initialize state** — set up from scenario instructions
- **Stop detection** — sends a stop signal when the conversation should
  end (task completed, agent transferred to human, too many failed attempts)
- **Role flipping** — internally flips user/assistant roles so the LLM
  sees itself as the "assistant" generating the user's responses

### Stop Signals

- `###STOP###` — user sim sends this to end the conversation
- `###TRANSFER###` — agent transferred to human

---

## Orchestrator

The orchestrator is a state machine that routes messages between the
three roles. It is the core loop of the simulation.

### Capabilities

- **Run** — execute the full simulation, return the complete result
- **Initialize** — set up initial state for all roles
- **Step** — execute one routing step

### State

The orchestrator tracks: the full trajectory, who sent the current
message, who should receive it, the current message, agent and user
state, step count, whether it's done, the termination reason, and
the error count.

### Initialization

1. Set seed for agent and user (if provided)
2. If the task has message history: validate it, determine routing
   state from the last message, initialize agent and user state from
   filtered history, set trajectory
3. Otherwise (fresh start): initialize user state, send the first
   greeting message, initialize agent state
4. Initialize environment state from task's initialization data,
   actions, and message history
5. Sync tools

### Step (the routing state machine)

One step = one message routed.

**Message goes to USER:** User simulator generates a response. If it's
a stop signal, end. If it contains tool calls, route to environment.
Otherwise route to agent.

**Message goes to AGENT:** Agent generates a response. If it's a stop
signal, end. If it contains tool calls, route to environment. Otherwise
route to user. In solo mode, text responses without tool calls are
looped back through the orchestrator and eventually terminate via
`max_steps` unless the agent stops or calls tools.

**Message goes to ENVIRONMENT:** Execute each tool call, collect results.
Route results back to whoever made the calls.

After routing: increment step count, sync environment tools. Check
limits (max steps, max errors) after non-environment steps only.

### Key Invariant

Tool results always go back to the caller. Agent calls → results to
agent. User calls → results to user.

---

## Evaluation Pipeline

After the simulation ends, the evaluator pipeline checks the trace
against the task's evaluation criteria. Each evaluator is independent.
Rewards are multiplied together.

### Environment Evaluator

Compares database state after the agent's trajectory vs. after
replaying golden actions.

1. If no evaluation criteria or no actions, reward is 1.0
2. Create a "predicted" environment by replaying the agent's full
   trajectory
3. Create a "golden" environment by replaying only the expected actions
4. Compare database hashes — match means 1.0, mismatch means 0.0
5. Run environment assertions on the predicted environment
6. Combine based on reward basis

### Action Evaluator

Checks that every expected action appears somewhere in the trajectory.
No ordering requirement.

1. Extract all tool calls from the trajectory
2. For each expected action, search for a matching tool call
3. All matched → 1.0, any missing → 0.0

### Communicate Evaluator

Checks that the agent mentioned all required information. Uses
case-insensitive substring matching on agent messages.

1. Concatenate all agent text messages
2. For each required info string, check if it appears
3. All found → 1.0, any missing → 0.0

### NL Assertions Evaluator

Uses an LLM to judge whether natural-language assertions are met by
the trajectory. This is the ONLY non-deterministic evaluator.

1. For each assertion, send trajectory + assertion to an LLM judge
2. Parse response: met (boolean) + justification
3. All met → 1.0, any failed → 0.0

### Reward Composition

1. If termination was abnormal (not agent/user stop), reward is 0.0
2. If no evaluation criteria, reward is 1.0
3. Run each evaluator specified in reward basis
4. Final reward = product of all evaluator rewards
5. Any single failure → overall failure

---

## CLI

```
pi run --domain mock --task-ids task_0,task_1 \
  --agent-llm anthropic/claude-sonnet-4-20250514 \
  --user-llm anthropic/claude-sonnet-4-20250514 \
  --num-trials 3 --max-steps 50 --save-to results/my_run

pi view results/my_run.json

pi check-data --domain mock
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| --domain | str | required | Domain name |
| --task-ids | str | None | Comma-separated task IDs (None = all) |
| --task-split | str | "base" | Named task subset |
| --agent-llm | str | required | Agent model (litellm format) |
| --user-llm | str | required | User sim model |
| --num-trials | int | 1 | Trials per task |
| --max-steps | int | 50 | Max orchestrator steps |
| --max-errors | int | 10 | Max tool errors before abort |
| --seed | int | None | Random seed |
| --save-to | str | None | Output JSON path |
| --max-concurrency | int | 1 | Parallel task execution |
| --solo | flag | False | Solo mode (no user sim) |
| --log-level | str | INFO | Logging level |

---

## Domain Registration

Domains are registered at startup. Each domain provides:

1. Policy text — markdown file, injected into agent system prompt
2. Tool definitions — schemas for function calling
3. Tool implementations — functions that execute against the DB
4. Initial database — starting state for the in-memory DB
5. Tasks — task definitions
6. Task splits — named subsets of tasks

Domains can be registered programmatically or discovered from a
directory.

---

## Behavioral Contracts

These are the observable behaviors that BDD tests verify. Each contract
becomes exactly one Gherkin scenario. If all pass, the system works.

### Environment

1. **Tools execute and return results** — a valid tool call returns
   a JSON result; a write tool mutates the database; a read after a
   write reflects the mutation.

2. **Errors are isolated** — an invalid tool call (unknown tool, bad
   arguments) returns an error result without crashing. The error
   message is descriptive.

3. **State is deterministic** — two environments initialized with the
   same data and given the same sequence of tool calls produce
   identical final state.

### Orchestrator

4. **Messages route correctly** — agent text goes to user, user text
   goes to agent, tool calls go to environment and results return to
   the caller. In solo mode, the agent operates without a user.

5. **Simulation terminates** — the simulation ends on agent stop,
   user stop, max steps, max errors, agent error, or user error.
   Solo mode agent sending text (not stop) exhausts `max_steps` under
   the current runtime contract.

6. **Trajectory is captured** — the simulation output contains the
   full ordered message history with turn indices, costs, timestamps,
   and termination reason.

### Evaluation

7. **Check engine produces correct verdicts** — expected outcomes
   (tool_called, tool_not_called, tool_called_with, tool_before_tool,
   state_field, message_not_contains) are evaluated deterministically
   against a trace. Failed verdicts include evidence pointers.

8. **Reward composition works** — abnormal termination gets 0.0,
   no criteria gets 1.0, otherwise reward is the product of all
   evaluator rewards.

### Policy Evaluation Pipeline

9. **Trace recording captures tool context** — tool calls are
   recorded with pre/post state, and query methods answer questions
   about the trace.

10. **Canonical decision is extracted** — exactly one policy decision
    (ALLOW/DENY/ESCALATE) is resolved from the trace. Tool channel
    takes precedence over JSON. Invalid/missing/multiple decisions
    are caught.

11. **Event flags are computed** — V_r, UR_r, OR_r, EA_r, AT_r are
    computed deterministically from trace + decision + expected
    outcomes. Aggregation operators (Ever@k, Always@k) combine
    flags across k runs.

12. **Audit mode lets violations through; hard-gate blocks them** —
    in audit-only mode, forbidden tools execute normally. In
    hard-gate mode, forbidden tools are blocked and return a policy
    error. Both modes record trace events.

### Runner

13. **Multi-trial execution works** — k trials per task run and
    produce k simulation results with evaluation rewards.

14. **Seeds are deterministic** — same base seed produces same trial
    seeds, same trajectory for deterministic agents.

15. **Resume skips completed work** — given a checkpoint file, only
    incomplete runs execute.

---

## What This Spec Does NOT Cover

These are future layers that go on top of this core:

- Compliance matrix (10 surfaces x 7 pressures x 5 metrics)
- Adversarial user profiles
- Audit reports
- NL assertions evaluator (LLM-as-judge)
- Ablation controller

All of these layer on top of the core engine. The evaluator pipeline
is designed to be extended with new evaluator types.
