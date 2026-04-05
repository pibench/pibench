"""FastAPI application — run single pi-bench scenarios via HTTP."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from pi_bench.agents import LiteLLMAgent
from pi_bench.domains.mock import INITIAL_DB, TOOL_SCHEMAS, AGENT_TOOLS
from pi_bench.environment import create_environment
from pi_bench.evaluator import evaluate
from pi_bench.observer import create_observer
from pi_bench.orchestrator import run as orchestrator_run
from pi_bench.trace import TraceRecorder

app = FastAPI(title="pi-bench", version="0.1.0")


class RunRequest(BaseModel):
    task: dict[str, Any]
    model_name: str = "gpt-4o-mini"
    max_steps: int = Field(default=50, ge=1, le=500)
    seed: int | None = None
    solo: bool = True
    forbidden_tools: list[str] = Field(default_factory=list)
    observer_mode: str = "audit_only"


class RunResponse(BaseModel):
    simulation_id: str
    termination_reason: str
    step_count: int
    duration: float
    reward: float
    messages: list[dict[str, Any]]
    reward_info: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run_scenario(req: RunRequest) -> RunResponse:
    agent = LiteLLMAgent(model_name=req.model_name)

    env = create_environment(
        domain_name="mock",
        policy=req.task.get("policy", "Follow all instructions."),
        tools=AGENT_TOOLS,
        db=deepcopy(INITIAL_DB),
        tool_schemas=TOOL_SCHEMAS,
    )

    trace = TraceRecorder()
    forbidden = set(req.forbidden_tools) if req.forbidden_tools else None
    observer = create_observer(
        env, trace, forbidden_tools=forbidden, mode=req.observer_mode
    )

    task = {**req.task}
    if "id" not in task:
        task["id"] = str(uuid.uuid4())

    simulation = orchestrator_run(
        agent=agent,
        user=None,
        env=env,
        task=task,
        max_steps=req.max_steps,
        seed=req.seed,
        solo=req.solo,
        observer=observer,
    )

    simulation["trace"] = trace
    reward_info = evaluate(task, simulation, env)

    return RunResponse(
        simulation_id=simulation["id"],
        termination_reason=simulation.get("termination_reason", "unknown"),
        step_count=simulation.get("step_count", 0),
        duration=simulation.get("duration", 0.0),
        reward=reward_info["reward"],
        messages=simulation.get("messages", []),
        reward_info=reward_info,
    )
