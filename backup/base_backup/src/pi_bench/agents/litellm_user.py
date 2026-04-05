"""LiteLLMUser — LLM-backed user simulator using litellm.

Implements UserProtocol. Given a scenario with persona and pressure context,
generates realistic customer messages via an LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import litellm

from pi_bench.types import is_stop_signal


class LiteLLMUser:
    """User simulator backed by an LLM, implementing UserProtocol."""

    model_name: str

    def __init__(self, model_name: str = "gpt-4o-mini", max_turns: int = 8) -> None:
        self.model_name = model_name
        self._seed: int | None = None
        self._max_turns = max_turns

    def init_state(
        self,
        scenario: dict,
        message_history: list[dict] | None = None,
    ) -> dict:
        system_prompt = _build_user_system_prompt(scenario, self._max_turns)
        openai_messages = [{"role": "system", "content": system_prompt}]

        if message_history:
            for msg in message_history:
                openai_messages.extend(_to_openai_messages(msg))

        return {
            "messages": openai_messages,
            "turn_count": 0,
            "max_turns": self._max_turns,
            "initial_message": scenario.get("initial_user_message", ""),
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        messages = list(state["messages"])
        turn_count = state["turn_count"]

        # First turn: deliver the initial message directly (no LLM call needed)
        if turn_count == 0 and state.get("initial_message"):
            user_msg = {"role": "user", "content": state["initial_message"]}
            messages.append({"role": "assistant", "content": message.get("content", "")})
            messages.append(user_msg)
            new_state = {**state, "messages": messages, "turn_count": 1}
            return user_msg, new_state

        # Subsequent turns: call the LLM
        # Map the incoming assistant message into the user-sim's context
        # (the assistant's message appears as "assistant" from the user-sim's POV
        #  since the user-sim sees the agent as the other party)
        messages.extend(_to_openai_messages(message))

        if turn_count >= state["max_turns"]:
            stop_msg = {"role": "user", "content": "###STOP###"}
            messages.append(stop_msg)
            new_state = {**state, "messages": messages, "turn_count": turn_count + 1}
            return stop_msg, new_state

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        if self._seed is not None:
            kwargs["seed"] = self._seed

        response = litellm.completion(**kwargs)
        choice = response.choices[0]
        content = getattr(choice.message, "content", None) or "###STOP###"

        user_msg = {"role": "user", "content": content}
        messages.append({"role": "user", "content": content})
        new_state = {**state, "messages": messages, "turn_count": turn_count + 1}
        return user_msg, new_state

    def is_stop(self, message: dict) -> bool:
        return is_stop_signal(message)

    def set_seed(self, seed: int) -> None:
        self._seed = seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        pass


_GUIDELINES_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "user_simulator" / "simulation_guidelines.md"
)


def _load_guidelines() -> str:
    return _GUIDELINES_PATH.read_text()


def _build_user_system_prompt(scenario: dict, max_turns: int) -> str:
    """Build the system prompt for the user simulator from the scenario."""
    guidelines = _load_guidelines()
    persona = scenario.get("persona", "customer")
    initial_msg = scenario.get("initial_user_message", "")
    pressure_script = scenario.get("pressure_script", [])

    lines: list[str] = []
    lines.append(f"You are a {persona}.")
    if initial_msg:
        lines.append(f'Your opening request: "{initial_msg}"')
    if pressure_script:
        p_lines = "\n".join(f'  - "{p}"' for p in pressure_script)
        lines.append(f"Pressure escalation themes (use these, adapt naturally):\n{p_lines}")

    scenario_block = "\n".join(lines)
    return f"{guidelines}\n\n<scenario>\n{scenario_block}\n</scenario>\n\nAfter {max_turns} exchanges, wrap up and output ###STOP###."


def _to_openai_messages(msg: dict) -> list[dict]:
    """Convert a pi_bench message to OpenAI format for the user simulator.

    The user simulator sees the conversation from the customer's perspective:
    - assistant messages from the agent appear as "assistant"
    - tool/multi_tool messages are skipped (customer doesn't see tool calls)
    """
    role = msg.get("role", "")

    if role == "assistant":
        content = msg.get("content")
        if content:
            return [{"role": "assistant", "content": content}]
        return []  # tool-call-only messages — customer doesn't see these

    if role == "user":
        content = msg.get("content", "")
        return [{"role": "user", "content": content}] if content else []

    if role == "system":
        return [{"role": "system", "content": msg.get("content", "")}]

    # tool, multi_tool — customer doesn't see these
    return []
