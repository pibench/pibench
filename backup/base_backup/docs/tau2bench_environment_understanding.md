# tau2-bench Environment Implementation — Deep Dive

Source: `reference/tau2-bench/src/tau2/environment/`

## File Inventory

The environment package contains **6 Python files** across 2 directories:

```
environment/
├── __init__.py              (empty)
├── db.py                    (42 lines)
├── tool.py                  (223 lines)
├── toolkit.py               (177 lines)
├── environment.py           (416 lines)
├── server.py                (228 lines)
└── utils/
    └── interface_agent.py   (264 lines)
```

Total: **1,350 lines** of implementation.

---

## 1. `db.py` — Database Base Class (42 lines)

The simplest file. Defines `DB`, a Pydantic `BaseModelNoExtra` that every domain subclasses.

### Class: `DB(BaseModelNoExtra)`

| Method | Line | Signature | Purpose |
|---|---|---|---|
| `load` | 14 | `classmethod(path: str) -> DB` | Load from JSON/YAML/TOML via `load_file` utility |
| `dump` | 19 | `(path: str, exclude_defaults: bool) -> None` | Serialize to file via `dump_file` |
| `get_json_schema` | 24 | `() -> dict` | Returns Pydantic JSON schema of the DB model |
| `get_hash` | 28 | `() -> str` | Deterministic hash via `get_pydantic_hash(self)` |
| `get_statistics` | 32 | `() -> dict` | Override hook, returns `{}` by default |

### Free function: `get_db_json_schema(db: Optional[DB]) -> dict`

Line 37. Null-safe wrapper around `db.get_json_schema()`.

### Key design decisions

- `BaseModelNoExtra` rejects unknown fields (strict validation)
- Hash is computed from the Pydantic model, not raw JSON — field ordering doesn't matter
- `load` uses `model_validate(data)`, so the JSON must match the domain's DB schema exactly

---

## 2. `tool.py` — Tool Abstraction (223 lines)

Adapted from [BerriAI/appl](https://github.com/BerriAI/appl/blob/main/appl/core/tool.py). Wraps Python functions into LLM-callable tool objects with OpenAI-compatible schemas.

### Class: `BaseTool(BaseModel, ABC)`

Line 17. Abstract base with three methods:

| Method | Line | Purpose |
|---|---|---|
| `openai_schema` | 24 | Abstract property — returns OpenAI function-calling schema |
| `_call` | 30 | Abstract — actual execution |
| `__call__` | 33 | Delegates to `_call` |

### Class: `Tool(BaseTool)`

Line 38. The concrete implementation. Built from a Python function via introspection.

#### Constructor: `__init__(self, func: Callable, use_short_desc: bool, **predefined)`

Line 61. Does the following:
1. Extracts `name` from `func.__name__`
2. Extracts `sig` from `inspect.signature(func)`
3. Extracts `doc` from `func.__doc__`
4. Calls `parse_data(sig, doc, predefined)` to build params/returns/raises/examples
5. Stores `_func`, `_predefined`, `_use_short_desc` as private attrs

#### `parse_data(sig, docstring, predefined) -> dict` (classmethod)

Line 82. The parsing engine:

1. **Parses docstring** using `docstring_parser.parse()` — extracts short_desc, long_desc, param descriptions, return descriptions, raises, examples
2. **Builds params model**: iterates `sig.parameters`, merges type annotations from signature with descriptions from docstring, creates a dynamic Pydantic model via `create_model("parameters", **params)`
3. **Removes predefined params**: any kwarg passed as `predefined` is excluded from the params model (the LLM won't see them)
4. **Builds returns model**: same approach, `create_model("returns", returns=(anno, default))`
5. **Builds raises/examples**: extracted directly from docstring

#### `openai_schema` property

Line 140. Returns:
```python
{
    "type": "function",
    "function": {
        "name": self.name,
        "description": short_desc (or short + long),
        "parameters": self.params.model_json_schema()
    }
}
```

#### `_call(self, *args, **kwargs)`

Line 180. Merges `self._predefined` into kwargs, then calls `self._func(*args, **kwargs)`. This is how predefined arguments (like a DB reference) get injected without appearing in the LLM schema.

### Free function: `as_tool(func: Callable, **kwargs) -> Tool`

Line 185. Convenience wrapper: `return Tool(func=func, **kwargs)`.

---

## 3. `toolkit.py` — ToolKit Metaclass + Base Class (177 lines)

The registration and discovery layer. Uses a **metaclass** to auto-discover methods decorated with `@is_tool`.

### Constants

```python
TOOL_ATTR = "__tool__"        # line 10
TOOL_TYPE_ATTR = "__tool_type__"  # line 11
```

### Enum: `ToolType(str, Enum)`

Line 41. Four types:

| Value | Meaning |
|---|---|
| `READ` | Reads from DB without mutation |
| `WRITE` | Mutates DB state |
| `THINK` | Pure reasoning, no DB interaction |
| `GENERIC` | Everything else (e.g., transfer to human) |

### Decorator: `is_tool(tool_type: ToolType = ToolType.READ)`

Line 50. Sets two attributes on the decorated function:
- `__tool__ = True`
- `__tool_type__ = tool_type`

This is how methods are marked for auto-discovery.

### Metaclass: `ToolKitType(type)`

Line 17. The magic that makes tool discovery work.

**`__init__(cls, name, bases, attrs)`** (line 20):
1. Scans `attrs` for any method with the `__tool__` attribute
2. Collects them into `func_tools` dict
3. Defines a `_func_tools` property on the class that merges this class's tools with parent class tools (via `super()._func_tools`)

This means tool discovery is **inherited** — a subclass automatically includes parent tools.

### Class: `ToolKitBase(metaclass=ToolKitType)`

Line 65. The base class every domain's toolkit extends.

#### Constructor: `__init__(self, db: Optional[T] = None)`

Line 68. Stores `self.db` — the domain's `DB` instance that tools read/write.

#### Key methods:

| Method | Line | Signature | Purpose |
|---|---|---|---|
| `tools` | 72 | `property -> Dict[str, Callable]` | Returns bound methods discovered by metaclass |
| `use_tool` | 76 | `(tool_name, **kwargs) -> str` | Looks up tool by name, calls it. Raises `ValueError` if not found |
| `get_tools` | 82 | `() -> Dict[str, Tool]` | Wraps each method with `as_tool()` to produce `Tool` objects with OpenAI schemas |
| `has_tool` | 94 | `(tool_name) -> bool` | Existence check |
| `tool_type` | 98 | `(tool_name) -> ToolType` | Reads `__tool_type__` attribute from the method |
| `get_statistics` | 102 | `() -> dict` | Counts tools by type |
| `update_db` | 125 | `(update_data: dict) -> None` | Patches `self.db` using `update_pydantic_model_with_dict` |
| `get_db_hash` | 133 | `() -> str` | Returns `get_dict_hash(self.db.model_dump())` |

#### Important detail: `get_tools()` vs `tools`

- `tools` (property, line 72) returns **bound methods** (`getattr(self, name)`)
- `get_tools()` (line 82) wraps them with `as_tool()` to produce **`Tool` objects** with OpenAI schemas

The `as_tool()` call receives `getattr(self, name)` (a bound method), so `self` is already bound and does NOT appear in the generated parameter schema. This is critical — the LLM sees `create_task(user_id, title)`, not `create_task(self, user_id, title)`.

### Class: `ToolSignature(BaseModel)`

Line 138. A serializable representation of a tool's signature:
- `name: str`
- `doc: str`
- `params: Optional[dict]` (JSON schema)
- `returns: Optional[dict]` (JSON schema)

### Free functions:

| Function | Line | Purpose |
|---|---|---|
| `get_tool_signatures(tools: ToolKitBase)` | 153 | Returns `dict[str, ToolSignature]` for all tools |
| `get_tool_types(tools: ToolKitBase)` | 170 | Returns `dict[str, ToolType]` for all tools |

### Class: `GenericToolKit(ToolKitBase)`

Line 179. Defines two reusable tools any domain can inherit:

| Tool | Line | Type | Purpose |
|---|---|---|---|
| `think(thought: str)` | 186 | THINK | Scratchpad for LLM reasoning, returns `""` |
| `calculate(expression: str)` | 199 | GENERIC | Safe math eval with character whitelist |

`calculate` uses `eval()` with `{"__builtins__": None}` — only digits, operators, parens, dots, spaces allowed.

---

## 4. `environment.py` — The Environment Class (416 lines)

The central orchestration point. Holds two toolkits (agent + user), dispatches tool calls, manages DB state, runs assertions.

### Class: `EnvironmentInfo(BaseModel)`

Line 22. Serializable metadata:
- `domain_name: str`
- `policy: str`
- `tool_defs: Optional[dict[str, ToolSignature]]`

### Class: `Environment`

Line 34. The main class.

#### Constructor: `__init__(self, domain_name, policy, tools, user_tools, solo_mode)`

Line 39. Parameters:
- `domain_name: str` — e.g., "mock", "airline"
- `policy: str` — free-form text the agent reads
- `tools: Optional[ToolKitBase]` — agent's toolkit
- `user_tools: Optional[ToolKitBase]` — user simulator's toolkit
- `solo_mode: bool` — if True, agent gets both tool sets, no user simulator

Calls `validate_solo_mode()` if solo mode (checks no tool name overlap), then `sync_tools()`.

#### Tool Access Methods (lines 65-127)

| Method | Line | Purpose |
|---|---|---|
| `get_domain_name()` | 65 | Returns domain name |
| `get_policy()` | 71 | Returns policy text |
| `get_tools()` | 77 | Returns `list[Tool]` from agent toolkit |
| `get_user_tools()` | 85 | Returns `list[Tool]` from user toolkit |
| `get_tools_description(env_type)` | 93 | Numbered text description of tools |
| `use_tool(tool_name, **kwargs)` | 112 | Direct call to agent toolkit |
| `use_user_tool(tool_name, **kwargs)` | 120 | Direct call to user toolkit |

#### `make_tool_call(tool_name, requestor, **kwargs)` — Line 128

The routing layer:
- `requestor="user"` → calls `use_user_tool()` (blocked in solo mode)
- `requestor="assistant"` → calls `use_tool()`, but in solo mode also checks user tools first
- This is how solo-mode agents access both tool sets

**Does NOT call `sync_tools()`** — that's the caller's responsibility.

#### `sync_tools()` — Line 157

Override hook. Default is `pass`. Subclasses use this to keep agent/user toolkits in sync after mutations (e.g., airline domain where booking changes affect both sides).

#### Assertion & Function Call Methods (lines 164-212)

| Method | Line | Purpose |
|---|---|---|
| `run_env_function_call(env_function_call)` | 164 | Runs any function on agent or user toolkit by name. Calls `sync_tools()` after |
| `run_env_assertion(assertion, raise_assertion_error)` | 183 | Calls `run_env_function_call`, checks return == `assert_value`. Returns bool |
| `run_env_function_calls(env_function_calls)` | 203 | Batch version. Assertions get assertion-checked, others just execute |

The assertion flow:
1. `run_env_assertion` calls `run_env_function_call(assertion)` (line 193)
2. Verifies result is `bool` (line 194-196)
3. Compares `res == assertion.assert_value` (line 198)
4. If `raise_assertion_error=True` and mismatch, raises `AssertionError` with `assertion.message`

#### DB Comparison Methods (lines 233-261)

| Method | Line | Purpose |
|---|---|---|
| `check_db(reference: DB)` | 233 | Compares agent DB hash with reference |
| `check_user_db(reference: DB)` | 239 | Compares user DB hash with reference |
| `get_db_hash()` | 245 | Returns agent toolkit's `get_db_hash()` or `None` |
| `get_user_db_hash()` | 254 | Returns user toolkit's `get_db_hash()` or `None` |

#### `set_state(initialization_data, initialization_actions, message_history)` — Line 263

The state reconstruction method. Used by the evaluator to replay trajectories.

**Three-phase process:**

**Phase 1: Apply initialization data** (lines 310-314)
```python
if initialization_data.agent_data is not None:
    self.tools.update_db(initialization_data.agent_data)
if initialization_data.user_data is not None:
    self.user_tools.update_db(initialization_data.user_data)
```

**Phase 2: Run initialization actions** (lines 316-318)
```python
for action in initialization_actions:
    self.run_env_function_call(action)
```

**Phase 3: Replay message history** (lines 320-335)
1. Extracts `(ToolCall, ToolMessage)` pairs from `message_history` using inner function `get_actions_from_messages` (line 277)
2. For each pair: calls `self.get_response(tool_call)`, then **validates** the response matches the expected response
3. If mismatch → raises `ValueError` with full details
4. Finally calls `sync_tools()`

The inner function `get_actions_from_messages` (line 277) is a parser that walks the message list, pairs each `ToolCall` within an `AssistantMessage`/`UserMessage` with its following `ToolMessage`, and validates ID matching.

#### `to_json_str(resp: Any) -> str` (classmethod) — Line 337

Serialization utility. Handles:
- `BaseModel` → `model_dump()` then `json.dumps`
- `str` → passthrough
- `None` → passthrough
- `int/float/bool` → `str()`
- `list/tuple/dict` → recursive processing
- `datetime/date` → `isoformat()`
- Fallback: `json.dumps(..., default=str)`

#### Solo Mode Methods (lines 368-388)

| Method | Line | Purpose |
|---|---|---|
| `set_solo_mode(solo_mode)` | 368 | Toggle solo mode + validate |
| `validate_solo_mode()` | 376 | Ensures no tool name overlap between agent and user toolkits |

#### `get_response(message: ToolCall) -> ToolMessage` — Line 390

**The most important method.** This is what the Orchestrator calls for every tool call.

```python
def get_response(self, message: ToolCall) -> ToolMessage:
    error = False
    try:
        resp = self.make_tool_call(
            message.name, requestor=message.requestor, **message.arguments
        )
        self.sync_tools()
    except Exception as e:
        resp = f"Error: {e}"
        error = True
    resp = self.to_json_str(resp)
    return ToolMessage(
        id=message.id,
        content=resp,
        requestor=message.requestor,
        role="tool",
        error=error,
    )
```

Flow:
1. Try `make_tool_call` with tool name + arguments from the `ToolCall`
2. On success: call `sync_tools()`, serialize response to JSON string
3. On any exception: capture error message, set `error=True`
4. Return `ToolMessage` with the call's ID preserved, content as JSON string, and error flag

**Key guarantees:**
- Never crashes — all exceptions are caught and returned as error messages
- Result ID always matches call ID
- Content is always a JSON string (via `to_json_str`)
- `sync_tools()` is called after successful calls (not after errors)

---

## 5. `server.py` — FastAPI Environment Server (228 lines)

Wraps an `Environment` as an HTTP API. Used by `tau2 start` for remote agent evaluation.

### Class: `EnvironmentServer`

Line 12.

#### Constructor: `__init__(self, environment: Environment)`

Line 17. Creates a `FastAPI` app with:
- Title from domain name
- Description from policy (formatted with markdown)
- OpenAPI tags for "Tools" and "User Tools"
- Calls `_setup_routes()` to create endpoints

#### `_setup_routes()` — Line 105

1. Gets `ToolSignature` for all agent tools
2. Calls `_setup_tool_routes(signatures, "tools")` → creates `/tools/{name}` POST endpoints
3. If user tools exist, does the same under `/user_tools/{name}`

#### `_setup_tool_routes(tool_signatures, route_prefix)` — Line 116

For each tool:
1. **Builds a dynamic Pydantic request model** from the tool's JSON schema params (line 120-143)
   - Maps JSON schema types to Python types: `string→str`, `number→float`, `integer→int`, `boolean→bool`
2. **Creates a POST endpoint** at `/{route_prefix}/{name}` (line 148)
3. **Handler** (line 158): calls `environment.use_tool()` or `use_user_tool()`, returns result or raises `HTTPException(400)`

#### `_format_description(policy)` — Line 44

Parses policy text for XML-style sections (`<main_policy>`, `<tech_support_policy>`), formats as markdown for ReDoc.

#### `_format_tool_description(doc, returns, is_user_tool)` — Line 175

Extracts docstring content, adds response format and error sections for API docs.

#### `run(host, port)` — Line 217

Starts uvicorn server. Default: `127.0.0.1:8004`.

---

## 6. `utils/interface_agent.py` — Interactive DB Query Agent (264 lines)

An LLM-powered REPL for querying the environment's database interactively. Used by developers, not by the benchmark itself.

### Class: `InterfaceAgent`

Line 33.

#### Constructor: `__init__(self, environment, llm, llm_args)`

Line 34. Takes an `Environment`, an LLM model name, and optional LLM args. Default LLM comes from `config.py`.

#### System prompt (line 21)

```
You are a query interface agent that helps the developer interact with a database.
You have access to tools that can be used to query the database.
```

#### `respond(message, message_history) -> (AssistantMessage, list[Message])`

Line 52. The core loop:
1. Creates `SystemMessage` + appends `UserMessage` to history
2. Calls `generate(model, tools, messages)` — LLM call
3. While the response is a tool call:
   - For each tool call: `environment.get_response(tool_call)` → append to history
   - Call `generate()` again with updated history
4. Returns final `AssistantMessage` + updated history

This is a **ReAct-style loop** — the agent keeps making tool calls until it produces a text response.

### `main()` function — Line 102

Interactive CLI using `rich`:
- Domain selection (default: airline)
- Commands: `:q` quit, `:d` change domain, `:n` new session
- Renders responses as markdown
- Error handling for keyboard interrupts and tool failures

### `get_interface_agent(get_environment)` — Line 97

Factory function: `return InterfaceAgent(get_environment())`.

---

## Dependency Graph

```
db.py                    (no internal deps)
  ↑
tool.py                  (no internal deps)
  ↑
toolkit.py               (imports db.py, tool.py)
  ↑
environment.py           (imports db.py, tool.py, toolkit.py)
  ↑
server.py                (imports environment.py, toolkit.py)
  ↑
utils/interface_agent.py (imports environment.py)
```

The dependency flow is strictly bottom-up. No circular imports.

## External Dependencies

| File | External imports |
|---|---|
| `db.py` | `tau2.utils` (load_file, dump_file, get_pydantic_hash) |
| `tool.py` | `docstring_parser`, `pydantic` (create_model, field_serializer) |
| `toolkit.py` | `tau2.utils` (get_dict_hash, update_pydantic_model_with_dict) |
| `environment.py` | `tau2.data_model.message`, `tau2.data_model.tasks` |
| `server.py` | `fastapi`, `pydantic` (create_model) |
| `interface_agent.py` | `rich`, `tau2.utils.llm_utils`, `tau2.registry` |

---

## How It All Connects to the Orchestrator

The Orchestrator interacts with Environment through exactly **two methods**:

1. **`set_state(initialization_data, initialization_actions, message_history)`** — called during `Orchestrator.initialize()` to set up preconditions
2. **`get_response(tool_call: ToolCall) -> ToolMessage`** — called during `Orchestrator.step()` for every tool call the agent or user makes

The evaluator additionally uses:
- `get_db_hash()` — for DB state comparison
- `run_env_assertion(assertion)` — for post-simulation checks
- `set_state()` — to reconstruct both predicted and gold environments

---

## How This Maps to Our BDD Feature

Our `environment.feature` scenarios test the core guarantees of `get_response()`:

| Scenario | Tests |
|---|---|
| Read tool returns data as JSON | `get_response` serializes via `to_json_str`, content is valid JSON |
| Write tool mutates database state | `make_tool_call` → WRITE tool → `get_db_hash()` differs |
| Unknown tool returns error without crashing | `use_tool` raises `ValueError`, caught by `get_response` |
| Invalid arguments return error without crashing | Tool raises exception, caught by `get_response` |
| Result ID matches the call ID | `ToolMessage.id = message.id` (line 410) |
| Two fresh environments have the same hash | `DB.get_hash()` is deterministic |
| Tool results are always JSON strings | `to_json_str` guarantees string output |
