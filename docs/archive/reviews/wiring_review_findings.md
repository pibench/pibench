# Wiring Review Findings — Agent & Demo Code

*Deep verification of the 5 new files created for the agent/demo implementation.*

## Overall Result

All 5 new files are wired correctly. Every import works, every function call matches the right signature, every dict key exists. The A2A protocol format (how the server talks to pi-bench) is properly aligned.

## 2 Small Fixes Needed

### 1. Safety fix in `litellm_agent.py` (line 206)

When the LLM returns tool calls (like "look up customer X"), the agent stores them in memory for the next turn. Right now it stores the raw response. There's a tiny chance the format could be wrong (dict instead of JSON string), which would break turn 2+. The fix is one line — just make sure it's always a string before storing it. The A2A version (`purple_adapter.py:375-379`) already does this correctly.

### 2. Lint warning in `litellm_agent.py` (line 83)

The `stop()` method takes `message` and `state` parameters but doesn't use them (it's a no-op). The linter complains about unused variables. Fix: rename them to `_message` and `_state` to signal "intentionally unused."

## Known Issue in Existing Code (Not Our Problem)

The A2A path doesn't pass the random seed from pi-bench to the purple server in the HTTP request. This is in the original `purple_adapter.py`, not something we wrote. The workaround is using `--seed` when starting the server via CLI.
