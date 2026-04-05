# Implementation Trade-offs: pi-bench vs tau2-bench

*Working notes — temporary, will be discarded once decisions are finalized.*

## Module-by-module comparison

### environment.py — COVERED
- **tau2**: 384-line OOP class with Pydantic, metaclass toolkit, message types
- **pi-bench**: ~170 lines of pure functions, plain dicts
- **Trade-off**: We trade auto-discovery and type safety for simplicity and testability. Plain dicts mean no serialization ceremony. Functions mean no `self` threading.
- **Risk**: If we need to serialize environment snapshots for logging, we'll need to add that. Currently `get_info()` returns a plain dict — good enough.

### db.py — NOT NEEDED YET
- **tau2**: Pydantic base class with `load()`, `dump()`, `get_hash()`, `get_json_schema()`, `get_statistics()`
- **pi-bench**: Plain dicts for DB state
- **Trade-off**: No abstraction = no schema validation on DB mutations. Tools can put anything in the dict.
- **When we'll need it**: When we add a second domain. One domain = one dict shape. Two domains = need a common interface.
- **What we'd build**: NOT a Pydantic base class. Probably a `DBSchema` TypedDict or Protocol with `hash()` and `dump()`.

### tool.py — PARTIALLY COVERED
- **tau2**: Introspects function signatures + docstrings → OpenAI-compatible Tool objects. `as_tool()` wraps functions with predefined args.
- **pi-bench**: Hardcoded `TOOL_SCHEMAS` dicts in the mock domain
- **Trade-off**: Hardcoded schemas are dead simple but don't scale to multiple domains. Auto-generation is DRY but adds a dependency (docstring_parser).
- **When we'll need it**: When we add a second domain, or when someone changes a tool signature and forgets to update the schema.
- **What we'd build**: A `schema_from_function(fn)` utility that introspects type hints. NOT the full Tool class with Pydantic models for params/returns.

### toolkit.py — NOT COVERED
- **tau2**: Metaclass-based tool registry with `@is_tool(ToolType.READ)` decorator, `GenericToolKit` with think/calculate
- **pi-bench**: `dict[str, Callable]` — explicit tool registration
- **Trade-off**: Metaclass magic = auto-discovery but hard to debug. Explicit dict = boring but obvious.
- **Key insight**: Tool type classification (READ/WRITE/THINK) matters for the evaluator. Stuttering invariance says "extra reads shouldn't be penalized." The evaluator needs to know which tools are reads.
- **When we'll need it**: When we build the evaluator's stuttering invariance check.
- **What we'd build**: Probably a `tool_types: dict[str, str]` alongside the tool dict. No metaclass, no decorator magic.

### server.py — NOT NEEDED
- **tau2**: FastAPI server exposing tools as HTTP endpoints
- **pi-bench**: Everything runs in-process
- **Trade-off**: HTTP adds latency and complexity. In-process is fast and simple.
- **When we might need it**: If we want to test agents that talk over HTTP (e.g., MCP servers, external APIs). But that's a different architectural decision.
- **Decision**: Skip. If needed later, it's a thin wrapper — takes a day to add.

### interface_agent.py — NOT COVERED (CRITICAL GAP)
- **tau2**: LLM loop: user message → LLM → tool calls → environment → LLM → repeat until done
- **pi-bench**: Nothing yet
- **This is the orchestrator.** Without it, we can't run evaluations.
- **tau2's version**: Tightly coupled to their message types, LLM utils, rich CLI
- **What we'd build**: A functional loop: `run_agent(env, messages, llm_fn) -> Transcript`. No CLI, no rich. Pure function that takes an environment and returns a transcript.
- **Key behaviors**:
  1. Sends system prompt + policy to LLM
  2. LLM returns tool calls → routes to environment → feeds results back
  3. Loop until LLM returns a text response (no more tool calls)
  4. Returns full message history (transcript)
  5. Solo mode: single turn, no user simulator loop

## Priority order for implementation

1. **interface_agent** — Can't evaluate without it. This is the next layer up.
2. **tool.py** (auto-schema) — Quality of life. Build when adding second domain.
3. **toolkit** (tool types) — Build when evaluator needs READ/WRITE classification.
4. **db.py** — Build when adding second domain.
5. **server.py** — Probably never for pi-bench.

## Critical conceptual correction: the environment is a shared world

**What I initially built:** A sandbox with access control. One database,
two permission levels (agent tools vs user tools). Requestor routing
decides who can call what. This is the single-control model.

**What it actually is (from the tau2 paper, Dec-POMDP formulation):**

A **shared world with two partial views and dual control.**

- **Two databases** that together form the world state. Agent-side
  (e.g., CRM: accounts, billing, service plans) and user-side (e.g.,
  phone: airplane mode, SIM status, signal strength). Neither player
  sees the other's database directly.
- **Cross-effects**: Agent enables roaming in CRM → phone can now get
  signal abroad. User toggles airplane mode → network status changes.
  Actions on one side ripple into the other through shared world state.
- **Partial observability**: The agent can't look at the user's phone
  screen. The user can't peek into the CRM. The only information
  bridge is natural language conversation.
- **Dual control**: Solving problems requires *coordinated action from
  both sides*. Agent diagnoses → instructs user → user acts on their
  device → reports back → agent takes backend action → problem resolved.
  Neither player alone can fix it.

**The punchline:**

World-state mutation isn't hard. Coordination of who mutates what and
when is what's hard. Models reason through problems fine when they
control both sides (No-User mode). The 18-25% performance drop in
Default mode measures exactly the cost of the split — having to
communicate intent, delegate actions, interpret feedback, and adapt
across the agent/user boundary.

Everything in the tau2 paper flows from this one design choice:
- Dec-POMDP formalism exists to formalize it
- Compositional task generator creates problems requiring specific
  combinations of agent-side and user-side actions
- Ablation modes (No-User vs Default) measure coordination cost
- User simulator reliability improvements exist because giving the
  user actual tools constrains behavior more tightly than words alone

**Why this matters for pi-bench:**

Policy compliance isn't just "does the agent follow rules?" It's "does
the agent correctly coordinate mutations across a boundary it can't
see past — instructing a user to take actions it can't take itself,
adapting when intermediate steps fail — all while staying within policy?"

**Implications for our implementation:**

1. `user_tools` is not access control. It's a separate control surface
   over a different part of the shared world.
2. The two databases may need cross-effect hooks (agent action changes
   user-visible state and vice versa).
3. The orchestrator is a **two-player game loop**, not just "run LLM
   in a loop." It alternates between agent turns and user simulator
   turns, with the environment mediating shared state.
4. Solo mode = degenerate case where there's only one player. Valid
   for testing baseline comprehension but misses the coordination
   challenge.

## Open questions

- Should the agent loop be its own module (`pi_bench/orchestrator/`) or live in `pi_bench/agent/`?
- How do we handle the user simulator loop? tau2 has a separate `UserSimulator` class. We need that for pressure testing.
- Should we use litellm (like tau2) or go direct to Anthropic SDK?
- How do we model cross-effects between agent DB and user DB? Callback hooks? Shared state transitions? Domain-defined linkage functions?
- Does our current single-dict environment need to become a two-dict environment (agent_db + user_db) to properly model partial observability?
