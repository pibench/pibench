"""Orchestrator initialization — set up state for a fresh simulation."""

import json
from typing import Any

from pi_bench.environment import get_tool_schemas, get_policy
from pi_bench.orchestrator.helpers import unwrap_env, snapshot_db


def init(
    agent: Any,
    user: Any,
    env: dict,
    task: dict,
    seed: int | None = None,
    solo: bool = False,
) -> dict:
    """Set up orchestrator state for a fresh simulation.

    Three initialization paths:
        solo=True:  Agent works from a ticket, no user simulator.
        history:    Resume from a previous message history.
        default:    Fresh start with greeting → user.

    Args:
        agent: Agent protocol — generates assistant messages.
        user: User protocol — simulates customer messages.
        env: Environment dict (or observer-wrapped env).
        task: Task dict with id, description, evaluation_criteria.
        seed: Random seed for reproducible agent/user behavior.
        solo: If True, skip user simulator entirely.

    Returns:
        State dict with fields:
            trajectory:         list[dict] — ordered message history
            from_role:          str — role of last message sender
            to_role:            str — next routing target
            current_message:    dict — most recent message
            agent_state:        dict — agent's internal state
            user_state:         dict — user simulator's internal state
            step_count:         int — routing steps taken
            error_count:        int — tool call errors seen
            done:               bool — simulation finished
            termination_reason: str | None — why it ended
            tools:              list[dict] — current tool schemas
            solo:               bool — solo mode flag
            seed:               int | None — seed used
            agent_system_prompt: str — full system prompt sent to agent
            user_system_prompt:  str | None — user scenario as JSON
            db_snapshots:       list[dict] — DB state snapshots
    """
    if seed is not None:
        agent.set_seed(seed)
        if not solo and user is not None:
            user.set_seed(seed)

    raw_env = unwrap_env(env)
    tools = get_tool_schemas(raw_env)
    system_messages = build_system_messages(raw_env, task)
    history = task.get("initial_state", {}).get("message_history")

    if solo:
        # Solo mode: agent generates first message, no greeting
        agent_state = agent.init_state(system_messages, tools, message_history=history)
        trigger = {"role": "system", "content": task.get("ticket", task["description"])}
        state = {
            "trajectory": [trigger] if not history else list(history),
            "from_role": "system",
            "to_role": "agent",
            "current_message": trigger,
            "agent_state": agent_state,
            "user_state": {},
            "step_count": 0,
            "error_count": 0,
            "done": False,
            "termination_reason": None,
            "tools": tools,
            "solo": True,
            "seed": seed,
        }
    elif history:
        # Resume from message history
        agent_history = filter_history_for_role(history, "agent")
        user_history = filter_history_for_role(history, "user")
        agent_state = agent.init_state(system_messages, tools, message_history=agent_history)
        user_state = user.init_state(
            task.get("user_scenario", {}), message_history=user_history
        )
        last = history[-1]
        to_role = next_role_from_message(last)
        state = {
            "trajectory": list(history),
            "from_role": last["role"],
            "to_role": to_role,
            "current_message": last,
            "agent_state": agent_state,
            "user_state": user_state,
            "step_count": 0,
            "error_count": 0,
            "done": False,
            "termination_reason": None,
            "tools": tools,
            "solo": False,
            "seed": seed,
        }
    else:
        # Fresh start: greeting → user
        greeting = {"role": "assistant", "content": "Hi! How can I help you today?"}
        agent_state = agent.init_state(system_messages, tools, message_history=[greeting])
        user_state = user.init_state(task.get("user_scenario", {}))
        state = {
            "trajectory": [greeting],
            "from_role": "assistant",
            "to_role": "user",
            "current_message": greeting,
            "agent_state": agent_state,
            "user_state": user_state,
            "step_count": 0,
            "error_count": 0,
            "done": False,
            "termination_reason": None,
            "tools": tools,
            "solo": False,
            "seed": seed,
        }

    # Capture system prompts
    agent_prompt = "\n\n".join(m["content"] for m in system_messages)
    state["agent_system_prompt"] = agent_prompt

    user_scenario = task.get("user_scenario", {})
    state["user_system_prompt"] = json.dumps(user_scenario) if user_scenario else None

    # Initial DB snapshot
    state["db_snapshots"] = [snapshot_db(env, "init", len(state["trajectory"]))]

    return state


def build_system_messages(env: dict, task: dict) -> list[dict]:
    """Build system messages from environment policy and task description."""
    policy = get_policy(env)
    return [
        {"role": "system", "content": policy},
        {"role": "system", "content": task["description"]},
    ]


def filter_history_for_role(history: list[dict], role: str) -> list[dict]:
    """Filter message history per-role for resume.

    Agent sees: system, assistant messages, tool results for assistant.
    User sees: system, user messages, tool results for user, assistant text.
    """
    filtered = []
    for msg in history:
        msg_role = msg.get("role")
        if msg_role == "system":
            filtered.append(msg)
        elif role == "agent":
            if msg_role == "assistant":
                filtered.append(msg)
            elif msg_role == "tool" and msg.get("requestor") == "assistant":
                filtered.append(msg)
            elif msg_role == "multi_tool":
                subs = [m for m in msg.get("tool_messages", []) if m.get("requestor") == "assistant"]
                if subs:
                    filtered.append(msg)
        elif role == "user":
            if msg_role == "user":
                filtered.append(msg)
            elif msg_role == "assistant" and "content" in msg:
                filtered.append(msg)
            elif msg_role == "tool" and msg.get("requestor") == "user":
                filtered.append(msg)
            elif msg_role == "multi_tool":
                subs = [m for m in msg.get("tool_messages", []) if m.get("requestor") == "user"]
                if subs:
                    filtered.append(msg)
    return filtered


def next_role_from_message(msg: dict) -> str:
    """Determine the next routing target from the last message."""
    role = msg.get("role")
    if role == "assistant":
        if msg.get("tool_calls"):
            return "environment"
        return "user"
    elif role == "user":
        if msg.get("tool_calls"):
            return "environment"
        return "agent"
    elif role in ("tool", "multi_tool"):
        requestor = msg.get("requestor", "assistant")
        if requestor == "assistant":
            return "agent"
        return "user"
    return "agent"
