"""Agent under test running on OmniGent (implements AgentProtocol).

Per scenario run the agent gets a fresh workspace containing only
``policy.md`` (the benchmark policy). Its OmniGent session:

- can read that workspace through a sandboxed read-only file tool
  (no writes, no network, nothing outside the workspace);
- can call only the benchmark tools for the scenario. Those calls are not
  executed inside OmniGent: they are returned from ``generate()`` as
  ``tool_calls``, so pi-bench's environment executes and traces them exactly
  as for any other agent;
- has every other OmniGent framework tool denied by a CEL allowlist policy.

The OmniGent session transcript is saved next to the workspace when the run
stops, so the agent's policy reads remain auditable.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any

import yaml

from pi_bench.omnigent import DEFAULT_AGENT_MODEL, DEFAULT_HARNESS
from pi_bench.omnigent.server import OmniGentServer, get_shared_server
from pi_bench.omnigent.session import (
    OmniGentSession,
    TurnResult,
    build_agent_spec,
    check_tool_names,
    to_client_tool,
    unique_name,
)
from pi_bench.types import build_tool_call, is_stop_signal, make_assistant_msg

logger = logging.getLogger(__name__)

# Read-only file tool and the Claude CLI's deferred-tool loader stay allowed.
_HARNESS_TOOLS = ["sys_os_read", "ToolSearch"]

AGENT_PROMPT = (
    "You are a service agent handling requests on behalf of an organization.\n\n"
    "The organization's policy is in policy.md in your working directory. Read it before "
    "you act and consult it whenever you need to.\n\n"
    "Look up records and take actions only through the tools you are given. Never say an "
    "action happened unless a tool confirmed it."
)

_SOLO_CONTINUE = (
    "(No one else is in this conversation. Continue the task with your tools. "
    "When you have finished, reply with exactly ###STOP###.)"
)


class OmniGentAgent:
    """AgentProtocol implementation backed by an OmniGent harness session."""

    model_name: str

    def __init__(
        self,
        model_name: str | None = None,
        harness: str = DEFAULT_HARNESS,
        workspace_root: str | Path | None = None,
        server: OmniGentServer | None = None,
        turn_timeout: float = 300.0,
        system_prompt: str = AGENT_PROMPT,
        **_ignored: Any,
    ) -> None:
        self.model_name = model_name or DEFAULT_AGENT_MODEL
        self.harness = harness
        self.turn_timeout = float(turn_timeout)
        self.system_prompt = system_prompt
        self._server = server
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self._seed: int | None = None
        self._sessions: dict[str, OmniGentSession] = {}
        self._lock = threading.Lock()

    # ── AgentProtocol ──

    def init_state(
        self,
        benchmark_context: list[dict],
        tools: list[dict],
        message_history: list[dict] | None = None,
    ) -> dict:
        server = self._server or get_shared_server()
        names = [t.get("function", t).get("name", "") for t in tools or []]
        check_tool_names(names)

        policy = "\n\n".join(
            str(n.get("content", "")).strip() for n in benchmark_context or [] if n.get("kind") == "policy"
        ).strip()
        # Opaque folder name: the agent can see its own path, so it must not
        # carry the scenario name. Bookkeeping files live outside the workspace.
        run_dir = self._workspaces_root(server) / f"run-{uuid.uuid4().hex[:12]}"
        workspace = run_dir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "policy.md").write_text(policy + "\n")
        (run_dir / "run_meta.json").write_text(json.dumps({"domain": _domain(benchmark_context)}))

        spec = build_agent_spec(
            name=unique_name("pibench-agent"),
            prompt=self._compose_prompt(benchmark_context),
            model=self.model_name,
            harness=self.harness,
            allowed_tools=_HARNESS_TOOLS + names,
            workspace=workspace,
        )
        # Audit record of exactly what the agent was given (prompt, tools, sandbox).
        (run_dir / "agent_spec.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
        session = OmniGentSession(server, spec, timeout=self.turn_timeout)
        with self._lock:
            self._sessions[session.session_id] = session
        return {
            "session_id": session.session_id,
            "run_dir": str(run_dir),
            "tools": [to_client_tool(t) for t in tools or []],
            "turns": 0,
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        session = self._session(state)
        role = message.get("role")
        if role == "tool":
            result = session.send_tool_results([(message["id"], _content(message))])
        elif role == "multi_tool":
            result = session.send_tool_results(
                [(m["id"], _content(m)) for m in message.get("tool_messages", [])]
            )
        elif role == "assistant":  # solo mode echoes the agent's own text back
            result = session.send_message(_SOLO_CONTINUE, tools=state["tools"])
        else:
            text = _content(message) or "(empty message)"
            result = session.send_message(text, tools=state["tools"])
        return _to_pi_message(result), {**state, "turns": state.get("turns", 0) + 1}

    def is_stop(self, message: dict) -> bool:
        return is_stop_signal(message)

    def set_seed(self, seed: int) -> None:
        # Recorded for provenance; the Claude harness does not take a sampling seed.
        self._seed = seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        if not state or "session_id" not in state:
            return
        with self._lock:
            session = self._sessions.pop(state["session_id"], None)
        if session is None:
            return
        session.save_transcript(Path(state["run_dir"]) / "agent_transcript.json")
        session.close()

    # ── helpers ──

    def _session(self, state: dict) -> OmniGentSession:
        with self._lock:
            session = self._sessions.get(state.get("session_id", ""))
        if session is None:
            raise RuntimeError("OmniGent session not found; init_state must run first")
        return session

    def _workspaces_root(self, server: OmniGentServer) -> Path:
        root = self._workspace_root or os.environ.get("PI_BENCH_OMNIGENT_WORKSPACES")
        return Path(root) if root else server.run_dir / "agent_runs"

    def _compose_prompt(self, benchmark_context: list[dict]) -> str:
        sections = [self.system_prompt]
        for node in benchmark_context or []:
            kind = str(node.get("kind", "context")).strip() or "context"
            if kind == "policy":
                continue  # delivered as the workspace file, not in the prompt
            content = str(node.get("content", "")).strip()
            if content:
                sections.append(f"## {kind.capitalize()}\n{content}")
        return "\n\n".join(sections)


def _to_pi_message(result: TurnResult) -> dict:
    if result.tool_calls:
        calls = [build_tool_call(name=c.name, arguments=c.arguments, call_id=c.call_id) for c in result.tool_calls]
        return make_assistant_msg(content=result.text or None, tool_calls=calls)
    if result.status != "completed":
        raise RuntimeError(f"OmniGent turn {result.status}: {result.error}")
    return make_assistant_msg(content=result.text or "###STOP###")


def _content(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in content)
    return "" if content is None else str(content)


def _domain(benchmark_context: list[dict]) -> str:
    for node in benchmark_context or []:
        domain = (node.get("metadata") or {}).get("domain")
        if domain:
            return str(domain)
    return ""
