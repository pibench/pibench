"""Procedure DAG — the formal truth of what a policy procedure requires.

A DAG encodes:
- Which tools must be called (nodes)
- What order they must be called in (edges)
- Which groups of tools are required together (AND gates)
- Which tools are alternatives (OR gates)
- Which tools are forbidden (forbidden set)
- What constraints must hold for each tool to be reachable

From one DAG, the generator produces many scenarios by permuting which
constraints are satisfied and which behavioral envelope is applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolNode:
    """A tool call in the procedure DAG."""

    tool_name: str
    arguments: dict[str, str] = field(default_factory=dict)
    description: str = ""
    # Constraint that must hold for this node to be reachable
    constraint: str | None = None
    # If True, this tool call is required. If False, it's optional.
    required: bool = True


@dataclass
class Gate:
    """A logical gate connecting nodes in the DAG."""

    gate_type: str  # "and", "or"
    children: list[int] = field(default_factory=list)  # indices into nodes


@dataclass
class ProcedureDAG:
    """A directed action graph encoding a policy procedure.

    This is the ground truth from which scenarios and evaluation checks
    are derived. The DAG is NOT used to score agents — it's used to:
    1. Generate scenarios (constraint permutation)
    2. Derive evaluation checks (automatic)
    3. Validate scenario consistency (reference trajectory)
    """

    name: str
    domain: str
    description: str

    # The procedure as a list of tool nodes
    nodes: list[ToolNode] = field(default_factory=list)

    # Directed edges: (from_idx, to_idx) meaning from must happen before to
    edges: list[tuple[int, int]] = field(default_factory=list)

    # Forbidden tools — must never be called
    forbidden: list[str] = field(default_factory=list)

    # The terminal node (the final action, e.g., record_decision)
    terminal_node: int = 0

    # Expected decision when all constraints are satisfied
    decision_when_satisfied: str = "ALLOW"

    # Expected decision when key constraints are NOT satisfied
    decision_when_unsatisfied: str = "DENY"

    # Default leaderboard column when all constraints are satisfied
    leaderboard_primary: str = "Procedural Compliance"

    # Constraints that can be permuted for generation
    constraints: list[Constraint] = field(default_factory=list)


@dataclass
class Constraint:
    """A permutable constraint in the procedure.

    When satisfied, the procedure can proceed through the associated nodes.
    When unsatisfied, the agent should detect this and change course
    (deny, escalate, or take an alternative path).
    """

    name: str
    description: str

    # DB field path that controls this constraint
    db_field: str
    # Value when constraint is satisfied
    satisfied_value: Any
    # Value when constraint is NOT satisfied
    unsatisfied_value: Any

    # Which nodes become unreachable when this constraint is unsatisfied
    blocks_nodes: list[int] = field(default_factory=list)

    # What the expected label becomes when this constraint is unsatisfied
    unsatisfied_label: str = "DENY"

    # What tools the agent should call instead when constraint is unsatisfied
    alternative_tools: list[str] = field(default_factory=list)
