"""A2A Executor — handles incoming assessment requests from AgentBeats.

Implements the a2a-sdk AgentExecutor interface. Parses the incoming request
to extract the purple agent URL and assessment config, runs the multi-domain
assessment engine, and returns results as a DataPart artifact via TaskUpdater.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from typing_extensions import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, TextPart
from a2a.utils import new_agent_text_message, new_task

from pi_bench.a2a.assessment import run_assessment
from pi_bench.a2a.results import to_agentbeats_results

logger = logging.getLogger(__name__)


class PIBenchExecutor(AgentExecutor):
    """Executes pi-bench assessments for incoming A2A requests.

    Accepts an assessment request containing a purple agent URL,
    runs all scenarios (finra, retail, helpdesk) against it, and
    returns AgentBeats-formatted results as an artifact.
    """

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle an incoming assessment request.

        Expected input (as a data part in the message):
            {
                "participants": {
                    "agent": {"url": "<purple_agent_url>", "id": "<agent_id>"}
                },
                "config": {
                    "domain": "policy_compliance",
                    "scenarios_dir": "scenarios",
                    "max_steps": 50,
                    "seed": 42
                }
            }
        """
        msg = context.message
        if not msg:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    json.dumps({"error": "No message in request"})
                )
            )
            return

        task = context.current_task
        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)

        context_id = task.context_id
        updater = TaskUpdater(event_queue, task.id, context_id)
        await updater.start_work()

        try:
            request_data = _extract_request_data(context)
            purple_info = request_data.get("participants", {}).get("agent", {})
            purple_url = purple_info.get("url", "")
            agent_id = purple_info.get("id", "unknown")

            if not purple_url:
                await updater.failed(
                    new_agent_text_message(
                        "No purple agent URL provided",
                        context_id=context_id,
                        task_id=task.id,
                    )
                )
                return

            config = request_data.get("config", {})
            domain = config.pop("domain", "policy_compliance")

            logger.info(
                "Starting assessment for agent %s at %s (all domains)",
                agent_id, purple_url,
            )

            t0 = time.monotonic()

            scenario_results = await asyncio.to_thread(
                run_assessment,
                purple_url=purple_url,
                config=config,
            )

            elapsed = time.monotonic() - t0

            agentbeats_results = to_agentbeats_results(
                agent_id=agent_id,
                domain=domain,
                scenario_results=scenario_results,
                time_used=elapsed,
            )

            await updater.add_artifact(
                parts=[Part(root=DataPart(data=agentbeats_results))],
                name="PI-Bench Assessment Results",
            )

            logger.info(
                "Assessment completed in %.2fs — %d scenarios",
                elapsed, len(scenario_results),
            )
            await updater.complete()

        except Exception as exc:
            logger.exception("Assessment failed")
            error_msg = f"Assessment failed: {exc}"

            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=error_msg)),
                    Part(root=DataPart(data={"error": str(exc)})),
                ],
                name="PI-Bench Assessment Results (Failed)",
            )

            await updater.failed(
                new_agent_text_message(
                    error_msg,
                    context_id=context_id,
                    task_id=task.id,
                )
            )

    @override
    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Notify caller that cancellation is not supported.

        PI-Bench assessments run synchronously in a thread and cannot be
        interrupted mid-scenario. The caller receives an error message.
        """
        await event_queue.enqueue_event(
            new_agent_text_message(
                json.dumps({"error": "Cancellation not supported"})
            )
        )


def _extract_request_data(context: RequestContext) -> dict[str, Any]:
    """Extract assessment request data from the A2A RequestContext."""
    message = context.message
    if message is None:
        return {}

    for part in message.parts or []:
        if hasattr(part, "root"):
            part = part.root
        if hasattr(part, "data") and part.data is not None:
            return dict(part.data) if isinstance(part.data, dict) else {}
        if hasattr(part, "text") and part.text:
            try:
                return json.loads(part.text)
            except json.JSONDecodeError:
                continue

    return {}
