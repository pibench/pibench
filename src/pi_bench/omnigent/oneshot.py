"""One-shot completions through OmniGent (used by the LLM judge).

Each call uses a fresh, tool-less session so no context carries over between
calls. This lets Claude models run through the same subscription-backed
harness as the benchmark agents when no provider API key is configured.
"""

from __future__ import annotations

from pi_bench.omnigent.server import OmniGentServer, get_shared_server
from pi_bench.omnigent.session import OmniGentSession, build_agent_spec, unique_name

# Same harness as the agents (see pi_bench.omnigent.DEFAULT_HARNESS).
_HARNESS = "claude-sdk"


def complete_once(
    model: str,
    system_prompt: str,
    user_text: str,
    *,
    server: OmniGentServer | None = None,
    timeout: float = 120.0,
) -> str:
    """Send one message to a fresh tool-less session and return the reply text."""
    spec = build_agent_spec(
        name=unique_name("pibench-oneshot"),
        prompt=system_prompt,
        model=model,
        harness=_HARNESS,
        allowed_tools=[],
        workspace=None,
    )
    session = OmniGentSession(server or get_shared_server(), spec, timeout=timeout)
    try:
        result = session.send_message(user_text)
        if result.status != "completed":
            raise RuntimeError(f"OmniGent completion {result.status}: {result.error}")
        return result.text
    finally:
        session.close()
