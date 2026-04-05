"""Purple Agent Reference Server — implements the purple side of A2A bootstrap.

A minimal Starlette server that:
- Advertises ``urn:pi-bench:policy-bootstrap:v1`` in its agent card
- Accepts bootstrap requests (caches policy + tools under a context_id)
- Handles regular A2A requests (prepends cached policy for bootstrapped sessions)
- Uses litellm for LLM completions

NOT shipped with pi-bench. This is a reference implementation for testing.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import litellm
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)

from pi_bench.a2a.bootstrap import POLICY_BOOTSTRAP_EXTENSION

DEFAULT_MODEL = "gpt-4o-mini"


def build_agent_card(host: str = "localhost", port: int = 9100) -> dict:
    """Build the purple agent card advertising bootstrap support."""
    return {
        "name": "Purple Reference Agent",
        "description": "Reference purple agent for pi-bench bootstrap testing",
        "url": f"http://{host}:{port}",
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [
            {
                "id": "general",
                "name": "General Assistant",
                "description": "Handles policy-compliant requests",
            }
        ],
        "extensions": [POLICY_BOOTSTRAP_EXTENSION],
    }


# ── Endpoints ────────────────────────────────────────────


async def agent_card(request: Request) -> JSONResponse:
    """GET /.well-known/agent.json — serve the agent card."""
    card = request.app.state.agent_card
    return JSONResponse(card)


async def health(request: Request) -> JSONResponse:
    """GET /health — liveness check."""
    return JSONResponse({"status": "ok"})


async def handle_a2a(request: Request) -> JSONResponse:
    """POST / — A2A JSON-RPC handler.

    Two paths:
    1. Bootstrap: data.bootstrap == true → cache policy+tools, return context_id
    2. Regular: call LLM (prepending cached policy if bootstrapped)
    """
    body = await request.json()
    method = body.get("method")
    rpc_id = body.get("id", str(uuid.uuid4()))

    if method != "message/send":
        return _jsonrpc_error(rpc_id, -32601, f"Method not found: {method}")

    params = body.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])

    if not parts:
        return _jsonrpc_error(rpc_id, -32602, "No message parts")

    # Extract data from the first data part
    data_part = next((p for p in parts if p.get("kind") == "data"), None)
    if not data_part:
        return _jsonrpc_error(rpc_id, -32602, "No data part in message")

    data = data_part.get("data", {})

    # ── Bootstrap path ───────────────────────────────
    if data.get("bootstrap"):
        return _handle_bootstrap(request, rpc_id, data)

    # ── Regular request path ─────────────────────────
    return await _handle_regular(request, rpc_id, data)


def _handle_bootstrap(request: Request, rpc_id: str, data: dict) -> JSONResponse:
    """Cache policy + tools under a new context_id."""
    context_id = str(uuid.uuid4())

    system_messages = []
    policy_text = data.get("policy_text", "")
    if policy_text:
        system_messages.append({"role": "system", "content": policy_text})

    task_description = data.get("task_description", "")
    if task_description:
        system_messages.append({"role": "system", "content": task_description})

    tools = data.get("tools", [])

    request.app.state.sessions[context_id] = {
        "system_messages": system_messages,
        "tools": tools,
    }

    logger.info("Bootstrap: cached context_id=%s (%d tools)", context_id, len(tools))

    return _jsonrpc_result(
        rpc_id,
        {
            "status": {
                "state": "completed",
                "message": {
                    "role": "agent",
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "bootstrapped": True,
                                "context_id": context_id,
                            },
                        }
                    ],
                },
            }
        },
    )


async def _handle_regular(
    request: Request, rpc_id: str, data: dict
) -> JSONResponse:
    """Call LLM with the request messages (prepending cached policy if bootstrapped)."""
    messages = data.get("messages", [])
    tools = data.get("tools", [])
    context_id = data.get("context_id")

    # If bootstrapped, prepend cached system messages and tools
    if context_id:
        session = request.app.state.sessions.get(context_id)
        if session:
            messages = session["system_messages"] + messages
            if not tools:
                tools = session["tools"]
        else:
            logger.warning("Unknown context_id=%s, proceeding without cache", context_id)

    # Call LLM
    model = request.app.state.model
    try:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        reply = choice.message
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return _jsonrpc_error(rpc_id, -32000, f"LLM error: {exc}")

    # Build response parts
    parts: list[dict] = []
    if reply.content:
        parts.append({"kind": "text", "text": reply.content})

    if reply.tool_calls:
        tool_calls_data = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in reply.tool_calls
        ]
        parts.append({"kind": "data", "data": {"tool_calls": tool_calls_data}})

    if not parts:
        parts.append({"kind": "text", "text": ""})

    return _jsonrpc_result(
        rpc_id,
        {
            "status": {
                "state": "completed",
                "message": {"role": "agent", "parts": parts},
            }
        },
    )


# ── Helpers ──────────────────────────────────────────────


def _jsonrpc_result(rpc_id: str, result: dict) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _jsonrpc_error(rpc_id: str, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
    )


# ── App factory ──────────────────────────────────────────


def create_app(
    host: str = "localhost",
    port: int = 9100,
    model: str = DEFAULT_MODEL,
) -> Starlette:
    """Create the purple reference server."""
    routes = [
        Route("/.well-known/agent.json", agent_card, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/", handle_a2a, methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    app.state.agent_card = build_agent_card(host, port)
    app.state.sessions = {}
    app.state.model = model
    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=9100)
