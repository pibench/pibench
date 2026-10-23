"""OmniGent backend for pi-bench agents.

pi-bench talks to a private, local OmniGent server over HTTP (it never imports
the ``omnigent`` package, which lives in its own Python environment). The
server runs harness sessions (Claude via the ``claude-sdk`` harness by default)
for both sides of a benchmark conversation:

- the agent under test (``pi_bench.agents.omnigent_agent.OmniGentAgent``):
  reads ``policy.md`` from a sandboxed per-run workspace and acts only through
  the benchmark tools, whose calls are handed back to pi-bench for execution;
- the user simulator (``pi_bench.users.omnigent_user.OmniGentUser``): chat
  only, every tool denied.
"""

from pi_bench.omnigent.server import OmniGentServer, get_shared_server
from pi_bench.omnigent.session import OmniGentSession, PendingToolCall, TurnResult

DEFAULT_AGENT_MODEL = "claude-sonnet-4-5"
DEFAULT_USER_MODEL = "claude-sonnet-5-5"
DEFAULT_HARNESS = "claude-sdk"

__all__ = [
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_HARNESS",
    "DEFAULT_USER_MODEL",
    "OmniGentServer",
    "OmniGentSession",
    "PendingToolCall",
    "TurnResult",
    "get_shared_server",
]
