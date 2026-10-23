"""One OmniGent harness session, driven turn by turn over the Sessions HTTP API.

Benchmark tools are sent as *client tools* with every user message. When the
model calls one, OmniGent pauses the turn and emits a ``function_call`` item
with ``status: "action_required"``; the session returns it to the caller,
which executes it (pi-bench's environment + trace) and resumes the turn with
``send_tool_results``.
"""

from __future__ import annotations

import io
import json
import logging
import os
import platform
import queue
import tarfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from pi_bench.omnigent.server import INTERNAL_ORIGIN, OmniGentServer

logger = logging.getLogger(__name__)

# How long to keep collecting after the first action_required item, so that
# parallel tool calls from one model step are returned together.
_TOOL_BATCH_GRACE_S = 0.75
_END_EVENTS = {"response.completed", "response.failed", "response.incomplete"}

# Framework tools OmniGent always registers. Benchmark tool names must not
# collide with these (spec builtins win over client tools on a name clash).
RESERVED_TOOL_PREFIXES = ("sys_", "browser_", "mcp__")
RESERVED_TOOL_NAMES = {
    "Skill", "ToolSearch", "load_skill", "list_comments", "update_comment", "list_files",
}


@dataclass
class PendingToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class TurnResult:
    """What the model produced before pausing (tool calls) or finishing (text)."""

    text: str = ""
    tool_calls: list[PendingToolCall] = field(default_factory=list)
    status: str = "completed"  # completed | tool_calls | failed | incomplete
    error: str | None = None


def check_tool_names(names: list[str]) -> None:
    clashes = [n for n in names if n in RESERVED_TOOL_NAMES or n.startswith(RESERVED_TOOL_PREFIXES)]
    if clashes:
        raise ValueError(f"Benchmark tool names collide with OmniGent framework tools: {clashes}")


def cel_allowlist_expression(allowed: list[str]) -> str:
    """CEL policy: deny every tool call whose name is not in *allowed*."""
    names = sorted(set(allowed) | {f"mcp__omnigent__{a}" for a in allowed})
    return (
        f'event.type == "tool_call" && !(event.data.name in {json.dumps(names)})'
        ' ? {"result": "DENY", "reason": "This tool is not available in this task."}'
        ' : {"result": "ALLOW"}'
    )


def build_agent_spec(
    *,
    name: str,
    prompt: str,
    model: str,
    harness: str,
    allowed_tools: list[str],
    workspace: Path | None,
) -> dict[str, Any]:
    """Agent spec (spec_version 1). ``workspace`` set ⇒ read-only sandboxed file access there."""
    spec: dict[str, Any] = {
        "spec_version": 1,
        "name": name,
        "prompt": prompt,
        "executor": {"type": "omnigent", "model": model, "config": {"harness": harness}},
        "skills": "none",
        "async": False,
        "guardrails": {"policies": {"tool_allowlist": {"type": "function", "function": {
            "path": "omnigent.policies.builtins.cel.cel_policy",
            "arguments": {"expression": cel_allowlist_expression(allowed_tools),
                          "reason": "This tool is not available in this task."},
        }}}},
    }
    if workspace is not None:
        spec["os_env"] = {
            "type": "caller_process",
            "cwd": str(workspace),
            "sandbox": {"type": _sandbox_type(), "write_paths": [], "allow_network": False},
        }
    return spec


def _sandbox_type() -> str:
    """OS sandbox for the read-only workspace (override: PI_BENCH_OMNIGENT_SANDBOX)."""
    override = os.environ.get("PI_BENCH_OMNIGENT_SANDBOX")
    if override:
        return override
    return "darwin_seatbelt" if platform.system() == "Darwin" else "linux_bwrap"


def to_client_tool(schema: dict[str, Any]) -> dict[str, Any]:
    """pi-bench / OpenAI tool schema → OpenAI chat-completions function tool."""
    if schema.get("type") == "function" and "function" in schema:
        return schema
    func = {"name": schema["name"], "parameters": schema.get("parameters") or {"type": "object", "properties": {}}}
    if schema.get("description"):
        func["description"] = schema["description"]
    return {"type": "function", "function": func}


class OmniGentSession:
    """A live OmniGent session for one agent in one scenario run."""

    def __init__(self, server: OmniGentServer, spec: dict[str, Any], timeout: float = 300.0) -> None:
        self.server = server
        self.timeout = timeout
        self._client = server.client(timeout=60.0)
        self._events: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self._seen_calls: set[str] = set()
        self._closed = threading.Event()
        self.session_id = self._create(spec)
        self._stream_thread = threading.Thread(target=self._stream, daemon=True)
        self._stream_thread.start()
        self._wait_stream_open()

    # ── setup ──

    def _create(self, spec: dict[str, Any]) -> str:
        buf = io.BytesIO()
        payload = yaml.safe_dump(spec, sort_keys=False).encode()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo("config.yaml")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        resp = self._client.post(
            "/v1/sessions",
            data={"metadata": json.dumps({})},
            files={"bundle": ("agent.tar.gz", buf.getvalue(), "application/gzip")},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"OmniGent session create failed: {resp.status_code} {resp.text[:400]}")
        body = resp.json()
        session_id = body.get("session_id") or body.get("id")
        bind = self._client.patch(f"/v1/sessions/{session_id}", json={"runner_id": self.server.runner_id})
        bind.raise_for_status()
        return str(session_id)

    def _stream(self) -> None:
        try:
            with httpx.Client(base_url=self.server.base_url, timeout=None,
                              headers={"Origin": INTERNAL_ORIGIN}) as sc:
                with sc.stream("GET", f"/v1/sessions/{self.session_id}/stream") as resp:
                    self._events.put({"type": "_stream.open"})
                    for line in resp.iter_lines():
                        if self._closed.is_set():
                            return
                        if line.startswith("data:"):
                            try:
                                self._events.put(json.loads(line[5:].strip()))
                            except json.JSONDecodeError:
                                continue
        except Exception as exc:  # surfaced to the caller on its next wait
            if not self._closed.is_set():
                self._events.put({"type": "_stream.error", "error": repr(exc)})

    def _wait_stream_open(self) -> None:
        try:
            ev = self._events.get(timeout=15)
        except queue.Empty as exc:
            raise RuntimeError("OmniGent event stream did not open") from exc
        if ev.get("type") == "_stream.error":
            raise RuntimeError(f"OmniGent event stream failed: {ev.get('error')}")
        time.sleep(0.2)

    # ── turns ──

    def send_message(self, text: str, tools: list[dict[str, Any]] | None = None) -> TurnResult:
        body: dict[str, Any] = {
            "type": "message",
            "data": {"role": "user", "content": [{"type": "input_text", "text": text}]},
        }
        if tools:
            body["tools"] = tools
        self._post_event(body)
        return self._wait()

    def send_tool_results(self, results: list[tuple[str, str]]) -> TurnResult:
        for call_id, output in results:
            self._post_event({"type": "function_call_output", "data": {"call_id": call_id, "output": output}})
        return self._wait()

    def _post_event(self, body: dict[str, Any]) -> None:
        resp = self._client.post(f"/v1/sessions/{self.session_id}/events", json=body)
        if resp.status_code >= 400:
            raise RuntimeError(f"OmniGent event post failed: {resp.status_code} {resp.text[:400]}")

    def _wait(self) -> TurnResult:
        text: list[str] = []
        calls: list[PendingToolCall] = []
        deadline = time.monotonic() + self.timeout
        grace_until: float | None = None
        while True:
            now = time.monotonic()
            if grace_until is not None and now >= grace_until:
                return TurnResult(text="".join(text).strip(), tool_calls=calls, status="tool_calls")
            if now >= deadline:
                raise TimeoutError(f"OmniGent turn exceeded {self.timeout}s (session {self.session_id})")
            wait = min(1.0, (grace_until or deadline) - now)
            try:
                ev = self._events.get(timeout=max(wait, 0.05))
            except queue.Empty:
                continue
            etype = ev.get("type", "")
            if etype == "_stream.error":
                raise RuntimeError(f"OmniGent event stream failed: {ev.get('error')}")
            if etype == "response.output_text.delta":
                text.append(ev.get("delta", ""))
            elif etype == "response.output_item.done":
                item = ev.get("item") or {}
                if (item.get("type") == "function_call" and item.get("status") == "action_required"
                        and item.get("call_id") not in self._seen_calls):
                    self._seen_calls.add(item["call_id"])
                    raw = item.get("arguments") or "{}"
                    try:
                        args = json.loads(raw) if isinstance(raw, str) else dict(raw)
                    except json.JSONDecodeError:
                        args = {"_raw_arguments": raw}
                    calls.append(PendingToolCall(call_id=item["call_id"], name=item.get("name", ""), arguments=args))
                    grace_until = time.monotonic() + _TOOL_BATCH_GRACE_S
            elif etype in _END_EVENTS:
                status = etype.split(".", 1)[1]
                error = None
                if status != "completed":
                    error = json.dumps((ev.get("response") or {}).get("error"))[:500]
                if calls:  # a step that ended right after emitting tool calls
                    return TurnResult(text="".join(text).strip(), tool_calls=calls, status="tool_calls")
                return TurnResult(text="".join(text).strip(), status=status, error=error)

    # ── teardown ──

    def snapshot(self) -> dict[str, Any]:
        resp = self._client.get(f"/v1/sessions/{self.session_id}")
        resp.raise_for_status()
        return resp.json()

    def save_transcript(self, path: Path) -> None:
        try:
            path.write_text(json.dumps(self.snapshot(), indent=1, default=str))
        except Exception as exc:  # transcripts are best-effort audit artifacts
            logger.warning("Could not save OmniGent transcript for %s: %s", self.session_id, exc)

    def close(self) -> None:
        self._closed.set()
        self._client.close()


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"
