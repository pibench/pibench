"""LiteLLMAgent — LLM-backed agent using litellm for multi-provider access."""

from __future__ import annotations

import json
from typing import Any

import litellm

from pi_bench.types import build_tool_call, is_stop_signal, make_assistant_msg


_RESERVED_KEYS = {"model", "messages", "seed", "thinking"}


class LiteLLMAgent:
    """Agent that calls LLMs via litellm, implementing AgentProtocol."""

    model_name: str

    def __init__(self, model_name: str = "gpt-4o-mini", thinking: dict | None = None, **llm_args) -> None:
        self.model_name = model_name
        self._seed: int | None = None
        self._thinking = thinking
        self._llm_args = {k: v for k, v in llm_args.items() if k not in _RESERVED_KEYS}

    def init_state(
        self,
        system_messages: list[dict],
        tools: list[dict],
        message_history: list[dict] | None = None,
    ) -> dict:
        openai_tools = [_to_openai_tool(t) for t in tools] if tools else []
        openai_messages = []
        for sm in system_messages:
            openai_messages.append({"role": "system", "content": sm["content"]})
        if message_history:
            for msg in message_history:
                openai_messages.extend(_to_openai_messages(msg))
        return {
            "messages": openai_messages,
            "tools": openai_tools,
            "_policy_index": 0,
            "_turn_count": 0,
        }

    def generate(self, message: dict, state: dict) -> tuple[dict, dict]:
        turn = state.get("_turn_count", 0) + 1
        messages = list(state["messages"])
        messages.extend(_to_openai_messages(message))

        # After first turn, exclude the policy system message from API calls
        policy_idx = state.get("_policy_index")
        if turn > 1 and policy_idx is not None:
            send_messages = [m for i, m in enumerate(messages) if i != policy_idx]
        else:
            send_messages = messages

        kwargs: dict[str, Any] = {
            **self._llm_args,
            "model": self.model_name,
            "messages": send_messages,
        }
        if state["tools"]:
            kwargs["tools"] = state["tools"]
        if self._seed is not None:
            kwargs["seed"] = self._seed
        if self._thinking is not None:
            kwargs["thinking"] = self._thinking
            kwargs["max_tokens"] = 16384

        # Drop unsupported params (e.g., seed for Anthropic) instead of erroring
        kwargs["drop_params"] = True

        response = litellm.completion(**kwargs)
        choice = response.choices[0]
        usage = dict(response.usage) if response.usage else {}
        cost = response._hidden_params.get("response_cost", 0.0) if hasattr(response, "_hidden_params") else 0.0

        result = _from_openai_response(choice.message, cost, usage)
        messages.append(_choice_to_openai_msg(choice.message))
        new_state = {**state, "messages": messages, "_turn_count": turn}
        return result, new_state

    def is_stop(self, message: dict) -> bool:
        return is_stop_signal(message)

    def set_seed(self, seed: int) -> None:
        self._seed = seed

    def stop(self, message: dict | None, state: dict | None) -> None:
        pass


# ── Conversion: pi_bench → OpenAI ────────────────────────


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
                        "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"],
                    },
                }
                for tc in msg["tool_calls"]
            ]
        return out

    return {"role": role, "content": msg.get("content", "")}


def _to_openai_messages(msg: dict) -> list[dict]:
    """Convert a pi_bench message to a list of OpenAI messages.

    Handles multi_tool by flattening into separate tool messages.
    """
    if msg.get("role") == "multi_tool":
        result = []
        for sub in msg.get("tool_messages", []):
            result.append({
                "role": "tool",
                "tool_call_id": sub["id"],
                "content": sub.get("content", ""),
            })
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


# ── Conversion: OpenAI → pi_bench ────────────────────────


def _from_openai_response(
    choice_message: Any,
    cost: float = 0.0,
    usage: dict | None = None,
) -> dict:
    """Convert an OpenAI response message back to pi_bench format."""
    content = getattr(choice_message, "content", None)
    tool_calls_raw = getattr(choice_message, "tool_calls", None)

    if tool_calls_raw:
        pi_tool_calls = []
        for tc in tool_calls_raw:
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            pi_tool_calls.append(
                build_tool_call(
                    name=tc.function.name,
                    arguments=args,
                    call_id=tc.id,
                )
            )
        return make_assistant_msg(
            tool_calls=pi_tool_calls, cost=cost, usage=usage
        )

    if content:
        return make_assistant_msg(content=content, cost=cost, usage=usage)

    # No content, no tool_calls → stop
    return make_assistant_msg(content="###STOP###", cost=cost, usage=usage)


def _choice_to_openai_msg(choice_message: Any) -> dict:
    """Convert the raw OpenAI choice.message to a serializable dict for state."""
    out: dict[str, Any] = {"role": "assistant"}
    content = getattr(choice_message, "content", None)
    if content is not None:
        out["content"] = content
    tool_calls_raw = getattr(choice_message, "tool_calls", None)
    if tool_calls_raw:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": (
                        json.dumps(tc.function.arguments)
                        if isinstance(tc.function.arguments, dict)
                        else tc.function.arguments
                    ),
                },
            }
            for tc in tool_calls_raw
        ]
    return out
