"""Scenario generator — produces pi-bench scenarios from procedure DAGs and behavioral envelopes."""

from pi_bench.generator.dag import ProcedureDAG, ToolNode, Gate
from pi_bench.generator.core import generate_scenarios

__all__ = ["ProcedureDAG", "ToolNode", "Gate", "generate_scenarios"]
