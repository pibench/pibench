"""PolicyObservingEnvironment — wraps base environment with trace + gate.

Two execution modes:
- audit_only (default): all calls execute, violations recorded
- hard_gate: forbidden tools blocked, error returned, trace records block
"""

from __future__ import annotations

import copy
import json
from typing import Any

from pi_bench.environment import Env, ToolResult, get_db_hash, make_tool_call
from pi_bench.trace import TraceRecorder


def create_observer(
    env: Env,
    trace: TraceRecorder,
    forbidden_tools: set[str] | None = None,
    mode: str = "audit_only",  # "audit_only" or "hard_gate"
) -> dict[str, Any]:
    """Create a policy-observing wrapper around an environment."""
    return {
        "env": env,
        "trace": trace,
        "forbidden_tools": forbidden_tools or set(),
        "mode": mode,
    }


def observed_tool_call(
    observer: dict[str, Any],
    tool_name: str,
    call_id: str = "call",
    arguments: dict | None = None,
    requestor: str = "assistant",
) -> ToolResult:
    """Execute a tool call through the observer.

    Records pre/post state hashes. In hard_gate mode, blocks forbidden
    tools and returns an error without executing.
    """
    env = observer["env"]
    trace: TraceRecorder = observer["trace"]
    forbidden = observer["forbidden_tools"]
    mode = observer["mode"]

    pre_hash = get_db_hash(env)
    is_forbidden = tool_name in forbidden

    # Hard-gate: block forbidden tools
    if mode == "hard_gate" and is_forbidden:
        trace.record(
            tool_name=tool_name,
            arguments=arguments or {},
            result_content="Error: Tool not permitted by policy",
            result_error=True,
            pre_state_hash=pre_hash,
            post_state_hash=pre_hash,  # No mutation
            requestor=requestor,
            blocked=True,
        )
        return {
            "id": call_id,
            "content": json.dumps("Error: Tool not permitted by policy"),
            "requestor": requestor,
            "error": True,
        }

    # Execute normally (audit_only, or non-forbidden in hard_gate)
    result = make_tool_call(env, tool_name, call_id, arguments, requestor)
    post_hash = get_db_hash(env)
    db_state = copy.deepcopy(env["db"])

    trace.record(
        tool_name=tool_name,
        arguments=arguments or {},
        result_content=result["content"],
        result_error=result["error"],
        pre_state_hash=pre_hash,
        post_state_hash=post_hash,
        requestor=requestor,
        blocked=False,
        db_state=db_state,
    )

    return result
