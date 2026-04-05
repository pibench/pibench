#!/usr/bin/env python3
"""FastAPI purple agent server — wraps litellm for A2A-based pi-bench evaluation.

Receives pi-bench messages already in OpenAI format via A2A JSON-RPC,
calls litellm.completion() directly, returns results in A2A format.

Supports the pi-bench bootstrap extension (urn:pi-bench:policy-bootstrap:v1):
system messages and tools are sent once and cached per context_id.

Usage:
    python examples/a2a_demo/purple_server.py --model gpt-4o-mini --port 8766
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from typing import Any

import litellm
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

POLICY_BOOTSTRAP_EXTENSION = "urn:pi-bench:policy-bootstrap:v1"

app = FastAPI(title="pi-bench purple agent")

# Module-level state
_model: str = "gpt-4o-mini"
_seed: int | None = None
_sessions: dict[str, dict] = {}  # context_id → {system_messages, tools}


@app.get("/.well-known/agent.json")
async def agent_card() -> JSONResponse:
    """Return agent card declaring bootstrap extension support."""
    return JSONResponse({
        "name": "pi-bench-purple-agent",
        "description": "LiteLLM-based purple agent for pi-bench evaluation",
        "url": "",
        "extensions": [POLICY_BOOTSTRAP_EXTENSION],
        "capabilities": {
            "message": True,
        },
    })


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "model": _model})


@app.post("/")
async def message_send(request: Request) -> JSONResponse:
    """Handle A2A JSON-RPC message/send requests."""
    body = await request.json()

    method = body.get("method", "")
    if method != "message/send":
        return _jsonrpc_error(body.get("id"), -32601, f"Unknown method: {method}")

    params = body.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])

    if not parts:
        return _jsonrpc_error(body.get("id"), -32602, "No message parts")

    data = parts[0].get("data", {})

    # Bootstrap request
    if data.get("bootstrap"):
        return _handle_bootstrap(body.get("id"), data)

    # Regular turn
    return _handle_turn(body.get("id"), data)


def _handle_bootstrap(request_id: str | None, data: dict) -> JSONResponse:
    """Cache policy and tools for a new session, return context_id."""
    context_id = str(uuid.uuid4())

    # Build system messages from policy text
    system_messages = []
    if data.get("policy_text"):
        system_messages.append({"role": "system", "content": data["policy_text"]})
    if data.get("task_description"):
        system_messages.append({"role": "system", "content": data["task_description"]})

    _sessions[context_id] = {
        "system_messages": system_messages,
        "tools": data.get("tools", []),
    }

    logger.info("Bootstrap: cached context_id=%s (%d system msgs, %d tools)",
                context_id, len(system_messages), len(data.get("tools", [])))

    return _jsonrpc_success(request_id, {
        "kind": "data",
        "data": {"bootstrapped": True, "context_id": context_id},
    })


def _handle_turn(request_id: str | None, data: dict) -> JSONResponse:
    """Process a regular conversation turn."""
    context_id = data.get("context_id")
    messages = data.get("messages", [])
    tools = data.get("tools", [])

    # If bootstrapped, prepend cached system messages and tools
    if context_id and context_id in _sessions:
        session = _sessions[context_id]
        messages = session["system_messages"] + messages
        tools = session["tools"]

    # Build litellm kwargs
    kwargs: dict[str, Any] = {
        "model": _model,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    if _seed is not None:
        kwargs["seed"] = _seed

    try:
        response = litellm.completion(**kwargs)
    except Exception as exc:
        logger.exception("litellm.completion failed")
        return _jsonrpc_error(request_id, -32000, str(exc))

    choice = response.choices[0]
    result_part = _format_response(choice.message)

    return _jsonrpc_success(request_id, result_part)


def _format_response(choice_message: Any) -> dict:
    """Format an OpenAI response as an A2A data part.

    Must match the format expected by _parse_a2a_response in purple_adapter.py.
    """
    tool_calls_raw = getattr(choice_message, "tool_calls", None)
    content = getattr(choice_message, "content", None)

    if tool_calls_raw:
        tc_list = []
        for tc in tool_calls_raw:
            tc_list.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })
        return {"kind": "data", "data": {"tool_calls": tc_list}}

    if content:
        return {"kind": "data", "data": {"content": content}}

    return {"kind": "data", "data": {"content": "###STOP###"}}


def _jsonrpc_success(request_id: str | None, part: dict) -> JSONResponse:
    """Wrap a result part in a JSON-RPC success response."""
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id or str(uuid.uuid4()),
        "result": {
            "status": {
                "message": {
                    "role": "agent",
                    "parts": [part],
                },
            },
        },
    })


def _jsonrpc_error(request_id: str | None, code: int, message: str) -> JSONResponse:
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id or str(uuid.uuid4()),
        "error": {"code": code, "message": message},
    })


def main() -> None:
    global _model, _seed

    parser = argparse.ArgumentParser(description="pi-bench purple agent server")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="LiteLLM model name")
    parser.add_argument("--port", type=int, default=8766, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for LLM calls")
    args = parser.parse_args()

    _model = args.model
    _seed = args.seed

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("Starting purple agent server: model=%s host=%s port=%d", _model, args.host, args.port)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
