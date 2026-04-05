"""Local agent connection path.

To test your agent locally with pi-bench, implement AgentProtocol
and pass your agent instance to the runner.
"""

from pi_bench.local.protocol import AgentProtocol, UserProtocol

__all__ = ["AgentProtocol", "UserProtocol"]
