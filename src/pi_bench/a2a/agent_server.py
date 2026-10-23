"""Serve any pi-bench AgentProtocol implementation as an A2A purple agent.

Speaks the same contract as examples/a2a_demo/purple_server.py, so the green
assessment (A2APurpleAgent) needs no changes:

- the agent card advertises ``urn:pi-bench:policy-bootstrap:v1``;
- a bootstrap message (benchmark context + OpenAI-format tools) creates one
  agent session and returns its ``context_id``;
- each turn carries the full OpenAI-format history; only messages not seen
  before (the new user message or the tool results) go to ``generate()``;
- replies are a DataPart ``{"content", "tool_calls"}``.

Usage::

    python -m pi_bench.a2a.agent_server --agent omnigent --model claude-sonnet-4-5 --port 8766
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import importlib
import json
import logging
import threading
import uuid
from typing import Any

import uvicorn
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentExtension, AgentSkill, DataPart, Part
from a2a.utils import new_agent_parts_message, new_agent_text_message
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from pi_bench.a2a.bootstrap import POLICY_BOOTSTRAP_EXTENSION
from pi_bench.env import load_env

logger = logging.getLogger(__name__)

AGENT_ALIASES = {
    "omnigent": "pi_bench.agents.omnigent_agent:OmniGentAgent",
    "litellm": "pi_bench.agents.litellm_agent:LiteLLMAgent",
}


def load_agent(spec: str, model: str | None, **kwargs: Any) -> Any:
    """Instantiate an agent from an alias or ``module:ClassName``."""
    target = AGENT_ALIASES.get(spec, spec)
    if ":" not in target:
        raise ValueError(f"agent must be an alias {sorted(AGENT_ALIASES)} or module:ClassName, got {spec!r}")
    module_path, class_name = target.rsplit(":", 1)
    cls = getattr(importlib.import_module(module_path), class_name)
    return cls(model_name=model, **kwargs) if model else cls(**kwargs)


class _Context:
    def __init__(self, state: dict) -> None:
        self.state = state
        self.consumed = 0
        self.lock = threading.Lock()


_BRIDGES: list["AgentBridge"] = []


class AgentBridge:
    """Maps A2A bootstrap/turn payloads onto one AgentProtocol instance."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self._contexts: dict[str, _Context] = {}
        self._lock = threading.Lock()
        _BRIDGES.append(self)
        atexit.register(self.close_all)

    def bootstrap(self, data: dict) -> dict:
        state = self.agent.init_state(
            benchmark_context=_as_list(data.get("benchmark_context")),
            tools=_as_list(data.get("tools")),
            message_history=None,
        )
        context_id = str(uuid.uuid4())
        with self._lock:
            self._contexts[context_id] = _Context(state)
        logger.info("Bootstrap: context_id=%s", context_id)
        return {"bootstrapped": True, "context_id": context_id}

    def turn(self, data: dict) -> dict:
        context_id = str(data.get("context_id") or "")
        with self._lock:
            ctx = self._contexts.get(context_id)
        if ctx is None:
            return {"content": f"Unknown or missing bootstrap context_id: {context_id!r}. "
                               "This agent server requires the pi-bench policy-bootstrap extension."}
        messages = _as_list(data.get("messages"))
        with ctx.lock:
            new = messages[ctx.consumed:]
            ctx.consumed = len(messages)
            message = _next_input(new)
            if message is None:
                return {"content": "###STOP###"}
            reply, ctx.state = self.agent.generate(message, ctx.state)
            # The reply comes back to us inside the next request's history.
            ctx.consumed += 1
        return _reply_to_data(reply)

    def close_all(self) -> None:
        with self._lock:
            contexts, self._contexts = list(self._contexts.values()), {}
        for ctx in contexts:
            try:
                self.agent.stop(None, ctx.state)
            except Exception as exc:  # best effort at shutdown
                logger.warning("agent.stop failed: %s", exc)


def _next_input(new_messages: list[dict]) -> dict | None:
    """Turn the not-yet-seen OpenAI messages into one pi-bench input message."""
    tool_msgs = [
        {"role": "tool", "id": m.get("tool_call_id", ""), "content": m.get("content", "")}
        for m in new_messages if m.get("role") == "tool"
    ]
    if tool_msgs:
        return tool_msgs[0] if len(tool_msgs) == 1 else {"role": "multi_tool", "tool_messages": tool_msgs}
    users = [m for m in new_messages if m.get("role") == "user"]
    if users:
        return {"role": "user", "content": users[-1].get("content", "")}
    return None


def _reply_to_data(reply: dict) -> dict:
    data: dict[str, Any] = {}
    if reply.get("tool_calls"):
        data["tool_calls"] = [
            {"id": tc["id"], "type": "function",
             "function": {"name": tc["name"], "arguments": json.dumps(tc.get("arguments") or {})}}
            for tc in reply["tool_calls"]
        ]
    if reply.get("content"):
        data["content"] = reply["content"]
    return data or {"content": "###STOP###"}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _extract_data(context: Any) -> dict:
    message = context.message
    for part in (message.parts or []) if message else []:
        root = getattr(part, "root", part)
        data = getattr(root, "data", None)
        if isinstance(data, dict):
            return data
        text = getattr(root, "text", "")
        if text:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return {}


class BridgeExecutor(AgentExecutor):
    def __init__(self, bridge: AgentBridge) -> None:
        self.bridge = bridge

    async def execute(self, context: Any, event_queue: Any) -> None:
        data = _extract_data(context)
        if not data:
            await event_queue.enqueue_event(new_agent_text_message(
                "No message data provided", context_id=context.context_id, task_id=context.task_id))
            return
        try:
            if data.get("bootstrap"):
                payload = await asyncio.to_thread(self.bridge.bootstrap, data)
            else:
                payload = await asyncio.to_thread(self.bridge.turn, data)
        except Exception as exc:
            logger.exception("agent turn failed")
            payload = {"content": f"Agent error: {exc}"}
        await event_queue.enqueue_event(new_agent_parts_message(
            [Part(root=DataPart(data=payload))], context_id=context.context_id, task_id=context.task_id))

    async def cancel(self, context: Any, event_queue: Any) -> None:
        await event_queue.enqueue_event(new_agent_text_message("Cancellation is not supported"))


def create_app(agent: Any, host: str, port: int, card_url: str | None = None) -> Starlette:
    card = AgentCard(
        name="pi-bench-agent-server",
        description=f"pi-bench purple agent ({type(agent).__name__}, model={getattr(agent, 'model_name', '?')}).",
        url=card_url or f"http://{host}:{port}/",
        version="0.1.0",
        default_input_modes=["application/json", "text"],
        default_output_modes=["application/json", "text"],
        capabilities=AgentCapabilities(streaming=False, extensions=[AgentExtension(
            uri=POLICY_BOOTSTRAP_EXTENSION, description="Caches benchmark context and tools per scenario.",
            required=False)]),
        skills=[AgentSkill(id="pi_bench_policy_agent", name="PI-Bench Policy Agent",
                           description="Handles PI-Bench policy-compliance scenarios over A2A.",
                           tags=["policy", "pi-bench", "purple-agent"])],
    )
    a2a_app = A2AStarletteApplication(
        agent_card=card,
        http_handler=DefaultRequestHandler(agent_executor=BridgeExecutor(AgentBridge(agent)),
                                           task_store=InMemoryTaskStore()),
    )
    app = a2a_app.build(agent_card_url="/.well-known/agent.json", rpc_url="/")
    app.routes.append(Route("/.well-known/agent-card.json", a2a_app._handle_get_agent_card, methods=["GET"]))
    app.routes.append(Route("/a2a/message/send", a2a_app._handle_requests, methods=["POST"]))

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app.routes.append(Route("/health", health))
    return app


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Serve a pi-bench agent over A2A")
    parser.add_argument("--agent", default="omnigent", help="omnigent | litellm | module:ClassName")
    parser.add_argument("--model", default=None, help="Model name (default: the agent's own default)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--card-url", default="")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    agent = load_agent(args.agent, args.model)
    logger.info("Serving %s (model=%s) on %s:%d", type(agent).__name__, getattr(agent, "model_name", "?"),
                args.host, args.port)
    try:
        uvicorn.run(create_app(agent, args.host, args.port, card_url=args.card_url or None),
                    host=args.host, port=args.port, log_level="info")
    finally:
        for bridge in _BRIDGES:  # save transcripts while OmniGent is still up
            bridge.close_all()
        _stop_shared_omnigent()


def _stop_shared_omnigent() -> None:
    """Stop the process-wide OmniGent server if this process started one."""
    try:
        from pi_bench.omnigent import server as omnigent_server
    except ImportError:
        return
    if omnigent_server._shared is not None:
        omnigent_server._shared.stop()


if __name__ == "__main__":
    main()
