"""Orchestrator state — typed dataclass, no string keys.

SimState is the single source of truth for a running simulation.
Every field is typed. Every access is `state.field_name` — a typo
is an AttributeError caught by static analysis, not a silent None.

Three states: agent, user, environment.
Agent and user generate messages. Environment executes tool calls.
Environment always routes back to whoever called it — no event
needed, just `state.to_role = state.env_caller`.

Four events (agent/user only): text, tool_calls, stop, error.
Environment has no events — its routing is unconditional.
"""

from dataclasses import dataclass, field
from typing import Literal


# --- Types ---

Role = Literal["agent", "user", "environment"]
"""Three states: agent generates, user generates, environment executes."""

GeneratorRole = Literal["agent", "user"]
"""Roles that generate messages (not environment)."""

Event = Literal["text", "tool_calls", "stop", "error"]
"""What a generator (agent/user) produced — drives the next transition.

text:         Text message → route to other party.
tool_calls:   Tool calls → route to environment.
stop:         Stop signal → terminal.
error:        Error (invalid message, solo violation, exception) → terminal.
"""

Message = dict
"""A message dict with at minimum 'role' and optionally 'content', 'tool_calls'."""


# --- State ---

@dataclass
class SimState:
    """Complete simulation state. Passed through every step.

    Routing:
        to_role:            Next state — who acts next.
        current_message:    Most recent message dict.
        trajectory:         Ordered list of all messages.
        env_caller:         Who requested tool execution (set when to_role is
                            environment, used to route back after execution).

    Protocol state:
        agent_state:        Agent's internal state (opaque dict from protocol).
        user_state:         User simulator's internal state.

    Config:
        tools:              Current tool schemas available to agent/user.
        solo:               Solo mode — agent only, no user simulator.
        seed:               Random seed for reproducibility.

    Limits:
        step_count:         Number of steps taken so far.
        error_count:        Number of tool call errors encountered.

    Termination:
        done:               Whether the simulation has ended.
        termination_reason: Why it ended (None while running).
    """

    # Routing
    to_role: Role
    current_message: Message
    trajectory: list[Message] = field(default_factory=list)
    env_caller: GeneratorRole | None = None

    # Protocol state
    agent_state: dict = field(default_factory=dict)
    user_state: dict = field(default_factory=dict)

    # Config
    tools: list[dict] = field(default_factory=list)
    solo: bool = False
    seed: int | None = None

    # Limits
    step_count: int = 0
    error_count: int = 0
    solo_text_count: int = 0  # consecutive text-only messages in solo mode

    # Termination
    done: bool = False
    termination_reason: str | None = None
