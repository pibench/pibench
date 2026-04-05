"""Transition table — the orchestrator state machine as pure data.

The orchestrator is a state machine with three roles (agent, user,
environment) and five events (tool_calls, text, text_solo, stop, error).
The transition table maps (role, event) → next role. None means terminal.

State Machine Diagram:

    ┌──────────┐  text   ┌──────────┐
    │  agent   │────────→│   user   │
    │          │←────────│          │
    └────┬─────┘  text   └────┬─────┘
         │                    │
         │ tool_calls         │ tool_calls
         ↓                    ↓
    ┌──────────────────────────────┐
    │        environment           │
    │  (routes back to caller)     │
    └──────────────────────────────┘

    Solo mode: agent text → agent (self-loop)
    Stop/error from agent or user → terminal
"""

from typing import Literal, Union

from pi_bench.protocols import AgentProtocol, UserProtocol
from pi_bench.types import is_stop_signal

# --- Type aliases for readability ---

Role = Literal["agent", "user", "environment"]
"""A participant in the simulation."""

Event = Literal["tool_calls", "text", "text_solo", "stop", "error", "from_agent", "from_user"]
"""An event produced by a handler that drives the next transition."""

TransitionKey = tuple[Role, Event]
"""(current_role, event) — input to the transition table."""

NextRole = Role | None
"""The next role to route to, or None for terminal."""

TerminationReason = str
"""Why the simulation ended (e.g., 'agent_stop', 'user_error')."""

Message = dict
"""A message dict with at minimum 'role' and optionally 'content', 'tool_calls'."""


# --- Transition table ---

TRANSITIONS: dict[TransitionKey, NextRole] = {
    ("agent",       "tool_calls"):  "environment",
    ("agent",       "text"):        "user",
    ("agent",       "text_solo"):   "agent",
    ("agent",       "stop"):        None,
    ("agent",       "error"):       None,
    ("user",        "tool_calls"):  "environment",
    ("user",        "text"):        "agent",
    ("user",        "stop"):        None,
    ("user",        "error"):       None,
    ("environment", "from_agent"):  "agent",
    ("environment", "from_user"):   "user",
}

TERMINATION_REASONS: dict[TransitionKey, TerminationReason] = {
    ("agent", "stop"):  "agent_stop",
    ("agent", "error"): "agent_error",
    ("user",  "stop"):  "user_stop",
    ("user",  "error"): "user_error",
}


# --- Event classification (pure functions) ---


def classify_event(
    msg: Message | None,
    role: Role,
    protocol: Union[AgentProtocol, UserProtocol],
    solo: bool,
) -> Event:
    """Classify a generated message into a state-machine event.

    Pure function. No side effects. The transition table uses
    the returned event to determine the next role.

    Classification order (first match wins):
        None message    → "error"
        stop signal     → "stop"
        has tool_calls  → "tool_calls"
        agent + solo    → "text_solo"
        otherwise       → "text"
    """
    if msg is None:
        return "error"
    if protocol.is_stop(msg) or is_stop_signal(msg):
        return "stop"
    if msg.get("tool_calls"):
        return "tool_calls"
    if role == "agent" and solo:
        return "text_solo"
    return "text"


def classify_env_event(from_role: str) -> Event:
    """Classify environment completion — routes back to whoever called.

    "assistant" → "from_agent", anything else → "from_user".
    """
    return "from_agent" if from_role == "assistant" else "from_user"
