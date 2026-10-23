"""User simulator running on OmniGent (implements UserProtocol).

A chat-only OmniGent session: no workspace and every tool call denied by
policy. The system prompt is the same one LiteLLMUser builds from the
scenario's ``user_simulation`` block (persona, known_facts, goal, rules,
opening, and pressure in stress runs), so both backends behave alike.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from pi_bench.omnigent import DEFAULT_HARNESS, DEFAULT_USER_MODEL
from pi_bench.omnigent.server import OmniGentServer, get_shared_server
from pi_bench.omnigent.session import OmniGentSession, build_agent_spec, unique_name
from pi_bench.types import STOP_SIGNALS, is_stop_signal
from pi_bench.users.user import (
    _DEFAULT_MAX_PUSHBACKS,
    _build_user_system_prompt,
    _scenario_max_turns,
    default_max_turns,
    validate_condition,
)

# How the tested agent's visible text is presented to the simulated user.
_AGENT_PREFIX = "Service representative says:\n"


class OmniGentUser:
    """UserProtocol implementation backed by a tool-less OmniGent session."""

    model_name: str

    def __init__(
        self,
        model_name: str | None = None,
        harness: str = DEFAULT_HARNESS,
        condition: str | None = None,
        max_turns: int | None = None,
        max_pushbacks: int = _DEFAULT_MAX_PUSHBACKS,
        server: OmniGentServer | None = None,
        turn_timeout: float = 300.0,
        transcript_dir: str | Path | None = None,
        **_ignored: Any,
    ) -> None:
        self.model_name = model_name or DEFAULT_USER_MODEL
        self.harness = harness
        self._condition = validate_condition(condition)
        self._max_turns = default_max_turns(max_turns, self._condition)
        self._max_pushbacks = int(max_pushbacks)
        self._server = server
        self.turn_timeout = float(turn_timeout)
        self._transcript_dir = Path(transcript_dir) if transcript_dir else None
        self._seed: int | None = None
        self._sessions: dict[str, OmniGentSession] = {}
        self._lock = threading.Lock()

    # ── UserProtocol ──

    def init_state(self, scenario: dict, message_history: list[dict] | None = None) -> dict:
        server = self._server or get_shared_server()
        max_turns = _scenario_max_turns(scenario, self._max_turns)
        prompt = _build_user_system_prompt(
            scenario, max_turns, condition=self._condition, max_pushbacks=self._max_pushbacks
        )
        spec = build_agent_spec(
            name=unique_name("pibench-user"),
            prompt=prompt,
            model=self.model_name,
            harness=self.harness,
            allowed_tools=[],  # the user has no tools
            workspace=None,
        )
        session = OmniGentSession(server, spec, timeout=self.turn_timeout)
        with self._lock:
            self._sessions[session.session_id] = session
        turn_count = sum(1 for m in message_history or [] if m.get("role") == "user")
        return {
            "session_id": session.session_id,
            "turn_count": turn_count,
            "max_turns": max_turns,
            "initial_message": scenario.get("initial_user_message", ""),
            "condition": self._condition,
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        turn = state["turn_count"]
        if turn == 0 and state.get("initial_message"):
            # The opening is sent verbatim (no model call); the prompt already
            # tells the simulator it opened with this request.
            return {"role": "user", "content": state["initial_message"]}, {**state, "turn_count": 1}
        if turn >= state["max_turns"]:
            return {"role": "user", "content": "###STOP###"}, {**state, "turn_count": turn + 1}

        agent_text = message.get("content") or ""
        session = self._session(state)
        result = session.send_message(f"{_AGENT_PREFIX}{agent_text}" if agent_text else _AGENT_PREFIX + "(no reply)")
        if result.status != "completed":
            raise RuntimeError(f"OmniGent user turn {result.status}: {result.error}")
        return {"role": "user", "content": _normalize_reply(result.text)}, {**state, "turn_count": turn + 1}

    def is_stop(self, message: dict) -> bool:
        return is_stop_signal(message)

    def set_seed(self, seed: int) -> None:
        self._seed = seed  # provenance only; the Claude harness takes no sampling seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        if not state or "session_id" not in state:
            return
        with self._lock:
            session = self._sessions.pop(state["session_id"], None)
        if session is None:
            return
        if self._transcript_dir is not None:
            self._transcript_dir.mkdir(parents=True, exist_ok=True)
            session.save_transcript(self._transcript_dir / f"user_{session.session_id}.json")
        session.close()

    def _session(self, state: dict) -> OmniGentSession:
        with self._lock:
            session = self._sessions.get(state.get("session_id", ""))
        if session is None:
            raise RuntimeError("OmniGent user session not found; init_state must run first")
        return session


def _normalize_reply(text: str) -> str:
    """Empty → stop; a reply that contains a control token is that token."""
    stripped = (text or "").strip()
    if not stripped:
        return "###STOP###"
    for token in STOP_SIGNALS:
        if token in stripped:
            return token
    return stripped
