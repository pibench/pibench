"""A2APurpleAgent — implements AgentProtocol by routing to a purple agent via HTTP.

This adapter lets pi-bench's orchestrator evaluate a remote purple agent
over the A2A protocol. The orchestrator sees it as any other AgentProtocol
implementation (like LiteLLMAgent), but generate() sends requests to a
purple agent's HTTP endpoint instead of calling an LLM directly.

Supports two modes:

1. **Bootstrapped** (preferred): policy + tools are sent once via
   ``init_state()`` when the purple agent advertises
   ``urn:pi-bench:policy-bootstrap:v1``.  Subsequent turns send only
   conversation history + ``context_id``.

2. **Stateless** (fallback): full conversation history + tool schemas are
   sent on every turn, as before.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx

from pi_bench.a2a.bootstrap import (
    BenchmarkBootstrap,
    build_bootstrap_request,
    check_bootstrap_support,
    parse_bootstrap_response,
)
from pi_bench.types import build_tool_call, make_assistant_msg

logger = logging.getLogger(__name__)


class A2APurpleAgent:
    """Agent that routes to a remote purple agent via A2A JSON-RPC."""

    model_name: str

    def __init__(self, purple_url: str, timeout: float = 120.0) -> None:
        self.purple_url = purple_url.rstrip("/")
        self.model_name = f"a2a:{purple_url}"
        self._client = httpx.Client(timeout=timeout)
        self._seed: int | None = None
        self._task_id: str | None = None
        self._bootstrapped: bool = False
        self._context_id: str | None = None

    # ── AgentProtocol interface ───────────────────────────

    def init_state(
        self,
        system_messages: list[dict],
        tools: list[dict],
        message_history: list[dict] | None = None,
    ) -> dict:
        """Store system messages and tool schemas in state.

        If the purple agent supports the bootstrap extension, sends policy +
        tools once and stores the returned ``context_id``.  Subsequent
        ``generate()`` calls will omit system messages and tools.
        """
        openai_tools = [_to_openai_tool(t) for t in tools] if tools else []
        openai_messages: list[dict] = []
        for sm in system_messages:
            openai_messages.append({"role": "system", "content": sm["content"]})
        if message_history:
            for msg in message_history:
                openai_messages.extend(_to_openai_messages(msg))

        self._task_id = str(uuid.uuid4())

        # Attempt bootstrap handshake
        self._bootstrapped = False
        self._context_id = None
        try:
            if check_bootstrap_support(self.purple_url, self._client):
                policy_text = "\n\n".join(
                    sm["content"] for sm in system_messages if sm.get("content")
                )
                task_desc = (
                    system_messages[1]["content"]
                    if len(system_messages) > 1 and system_messages[1].get("content")
                    else ""
                )
                bundle = BenchmarkBootstrap(
                    policy_text=policy_text,
                    task_description=task_desc,
                    tools=openai_tools,
                    run_id=self._task_id,
                )
                bootstrap_req = build_bootstrap_request(bundle, task_id=self._task_id)
                resp = self._client.post(
                    self.purple_url,
                    json=bootstrap_req,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                context_id = parse_bootstrap_response(resp.json())
                if context_id:
                    self._bootstrapped = True
                    self._context_id = context_id
                    logger.info("Bootstrap succeeded — context_id=%s", context_id)
                else:
                    logger.warning("Bootstrap response missing context_id, falling back")
        except Exception as exc:
            logger.warning("Bootstrap handshake failed, falling back to stateless: %s", exc)

        return {
            "messages": openai_messages,
            "tools": openai_tools,
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        """Send conversation to the purple agent, parse response.

        When bootstrapped, system messages and tools are omitted from the
        payload — the purple agent prepends them from its session cache.
        """
        messages = list(state["messages"])
        messages.extend(_to_openai_messages(message))

        if self._bootstrapped and self._context_id:
            a2a_request = _build_a2a_request_bootstrapped(
                messages=messages,
                context_id=self._context_id,
                task_id=self._task_id,
            )
        else:
            a2a_request = _build_a2a_request(
                messages=messages,
                tools=state["tools"],
                task_id=self._task_id,
            )

        response = self._client.post(
            self.purple_url,
            json=a2a_request,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        a2a_response = response.json()

        result = _parse_a2a_response(a2a_response)

        assistant_msg = _result_to_openai_msg(result)
        messages.append(assistant_msg)
        new_state = {**state, "messages": messages}

        return result, new_state

    def is_stop(self, message: dict) -> bool:
        return False

    def set_seed(self, seed: int) -> None:
        self._seed = seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        self._client.close()


# ── Conversion: pi_bench → OpenAI format ─────────────────


def _to_openai_msg(msg: dict) -> dict:
    """Convert a single pi_bench message to OpenAI format."""
    role = msg.get("role", "user")

    if role == "system":
        return {"role": "system", "content": msg.get("content", "")}

    if role == "tool":
        return {
            "role": "tool",
            "tool_call_id": msg["id"],
            "content": msg.get("content", ""),
        }

    if role in ("assistant", "user"):
        out: dict[str, Any] = {"role": role}
        if "content" in msg and msg["content"] is not None:
            out["content"] = msg["content"]
        if "tool_calls" in msg and msg["tool_calls"]:
            out["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": (
                            json.dumps(tc["arguments"])
                            if isinstance(tc["arguments"], dict)
                            else tc["arguments"]
                        ),
                    },
                }
                for tc in msg["tool_calls"]
            ]
        return out

    return {"role": role, "content": msg.get("content", "")}


def _to_openai_messages(msg: dict) -> list[dict]:
    """Convert a pi_bench message to a list of OpenAI messages."""
    if msg.get("role") == "multi_tool":
        result = []
        for sub in msg.get("tool_messages", []):
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": sub["id"],
                    "content": sub.get("content", ""),
                }
            )
        return result
    return [_to_openai_msg(msg)]


def _to_openai_tool(schema: dict) -> dict:
    """Wrap a pi_bench tool schema in OpenAI function-calling format."""
    func: dict[str, Any] = {
        "name": schema["name"],
        "parameters": schema.get("parameters", {}),
    }
    if "description" in schema:
        func["description"] = schema["description"]
    return {"type": "function", "function": func}


# ── A2A request/response ─────────────────────────────────


def _build_a2a_request(
    messages: list[dict],
    tools: list[dict],
    task_id: str | None = None,
) -> dict:
    """Build an A2A JSON-RPC message/send request."""
    context = {
        "messages": messages,
        "tools": tools,
    }

    a2a_message = {
        "role": "user",
        "parts": [{"kind": "data", "data": context}],
    }

    params: dict[str, Any] = {"message": a2a_message}
    if task_id:
        params["configuration"] = {"taskId": task_id}

    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": params,
    }


def _build_a2a_request_bootstrapped(
    messages: list[dict],
    context_id: str,
    task_id: str | None = None,
) -> dict:
    """Build a lightweight A2A request for a bootstrapped session.

    Strips system messages from the history (purple will prepend from cache)
    and includes the ``context_id`` instead of tool schemas.
    """
    non_system = [m for m in messages if m.get("role") != "system"]

    context: dict[str, Any] = {
        "messages": non_system,
        "context_id": context_id,
    }

    a2a_message: dict[str, Any] = {
        "role": "user",
        "parts": [{"kind": "data", "data": context}],
    }

    params: dict[str, Any] = {"message": a2a_message}
    if task_id:
        params["configuration"] = {"taskId": task_id}

    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": params,
    }


def _parse_a2a_response(response: dict) -> dict:
    """Parse an A2A JSON-RPC response into a pi-bench assistant message."""
    result = response.get("result", {})

    # Task-based response (artifacts)
    if "artifacts" in result:
        for artifact in result["artifacts"]:
            for part in artifact.get("parts", []):
                return _part_to_pi_msg(part)

    # Status-based response
    status = result.get("status", {})
    message = status.get("message", {})
    if message:
        parts = message.get("parts", [])
        if parts:
            return _part_to_pi_msg(parts[0])

    # Direct message
    if "message" in result:
        parts = result["message"].get("parts", [])
        if parts:
            return _part_to_pi_msg(parts[0])

    return make_assistant_msg()


def _part_to_pi_msg(part: dict) -> dict:
    """Convert an A2A message part to a pi-bench assistant message."""
    kind = part.get("kind", "text")

    if kind == "data":
        data = part.get("data", {})
        if "tool_calls" in data:
            pi_tool_calls = []
            for tc in data["tool_calls"]:
                func = tc.get("function", tc)
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                pi_tool_calls.append(
                    build_tool_call(
                        name=func.get("name", tc.get("name", "unknown")),
                        arguments=args,
                        call_id=tc.get("id", str(uuid.uuid4())),
                    )
                )
            return make_assistant_msg(tool_calls=pi_tool_calls)

        if "content" in data:
            return make_assistant_msg(content=data["content"])

        return make_assistant_msg(content=json.dumps(data))

    text = part.get("text", "")
    if not text:
        return make_assistant_msg()
    return make_assistant_msg(content=text)


def _result_to_openai_msg(result: dict) -> dict:
    """Convert a pi-bench result message to OpenAI format for state tracking."""
    out: dict[str, Any] = {"role": "assistant"}
    if "content" in result and result["content"] is not None:
        out["content"] = result["content"]
    if "tool_calls" in result and result["tool_calls"]:
        out["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": (
                        json.dumps(tc["arguments"])
                        if isinstance(tc["arguments"], dict)
                        else tc["arguments"]
                    ),
                },
            }
            for tc in result["tool_calls"]
        ]
    return out
