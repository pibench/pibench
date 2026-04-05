"""ScriptedUser — deterministic user simulator from scenario pressure scripts.

Implements UserProtocol. Feeds messages from a scenario's user_simulation
block in order. No LLM calls.

Turn 0: initial_user_message
Turn 1..N: pressure_script[i-1]
After script exhausted: ###STOP###
"""

from __future__ import annotations

from pi_bench.types import is_stop_signal


class ScriptedUser:
    """Deterministic user simulator backed by a fixed script."""

    model_name: str = "scripted"

    def __init__(self) -> None:
        self._seed: int | None = None

    def init_state(
        self,
        scenario: dict,
        message_history: list[dict] | None = None,
    ) -> dict:
        return {
            "initial_message": scenario.get("initial_user_message", ""),
            "pressure_script": list(scenario.get("pressure_script", [])),
            "turn_count": 0,
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        turn = state["turn_count"]
        script = state["pressure_script"]

        if turn == 0:
            content = state["initial_message"]
        elif turn - 1 < len(script):
            content = script[turn - 1]
        else:
            content = "###STOP###"

        user_msg = {"role": "user", "content": content}
        new_state = {**state, "turn_count": turn + 1}
        return user_msg, new_state

    def is_stop(self, message: dict) -> bool:
        return is_stop_signal(message)

    def set_seed(self, seed: int) -> None:
        self._seed = seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        pass
