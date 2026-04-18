"""BenchmarkBootstrap — send benchmark context + tools once per scenario.

When the purple agent declares support for ``urn:pi-bench:policy-bootstrap:v1``
in its ``/.well-known/agent.json``, the green adapter sends structured
benchmark context and tool schemas exactly once at session init. All subsequent
turns on the same ``context_id`` run under the cached context and tools.

If the purple agent does *not* advertise the extension (or the bootstrap
handshake fails), the adapter falls back to the existing stateless behaviour.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

POLICY_BOOTSTRAP_EXTENSION = "urn:pi-bench:policy-bootstrap:v1"
AGENT_CARD_PATHS = (
    "/.well-known/agent.json",
    "/.well-known/agent-card.json",
)


@dataclass
class BenchmarkBootstrap:
    """Bundle of data sent once at scenario init."""

    benchmark_context: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = ""


def check_bootstrap_support(
    purple_url: str,
    client: httpx.Client,
) -> bool:
    """Return *True* if the purple agent declares the bootstrap extension.

    Fetches common A2A agent-card URLs and looks for
    ``POLICY_BOOTSTRAP_EXTENSION`` in ``extensions``.
    """
    for url in agent_card_urls(purple_url):
        try:
            resp = client.get(url, timeout=10.0)
            resp.raise_for_status()
            card = resp.json()
            if POLICY_BOOTSTRAP_EXTENSION in _agent_card_extension_uris(card):
                return True
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.debug("Bootstrap capability check failed for %s: %s", url, exc)
    return False


def agent_card_urls(purple_url: str) -> list[str]:
    """Return candidate agent-card URLs for a purple-agent base or endpoint URL."""
    parsed = urlparse(purple_url)
    if parsed.scheme and parsed.netloc:
        base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    else:
        base = purple_url.rstrip("/")
    return [f"{base}{path}" for path in AGENT_CARD_PATHS]


def _agent_card_extension_uris(card: dict[str, Any]) -> set[str]:
    """Return extension URIs from legacy and A2A 0.3 agent-card shapes."""
    uris: set[str] = set()

    legacy_extensions = card.get("extensions", [])
    if isinstance(legacy_extensions, list):
        for item in legacy_extensions:
            if isinstance(item, str):
                uris.add(item)
            elif isinstance(item, dict) and item.get("uri"):
                uris.add(str(item["uri"]))

    capabilities = card.get("capabilities", {})
    if isinstance(capabilities, dict):
        capability_extensions = capabilities.get("extensions", [])
        if isinstance(capability_extensions, list):
            for item in capability_extensions:
                if isinstance(item, str):
                    uris.add(item)
                elif isinstance(item, dict) and item.get("uri"):
                    uris.add(str(item["uri"]))

    return uris


def build_bootstrap_request(
    bundle: BenchmarkBootstrap,
    task_id: str | None = None,
) -> dict:
    """Build the A2A JSON-RPC ``message/send`` request that bootstraps a session."""
    data: dict[str, Any] = {
        "bootstrap": True,
        "benchmark_context": bundle.benchmark_context,
        "tools": bundle.tools,
        "run_id": bundle.run_id,
        "domain": bundle.domain,
    }

    a2a_message: dict[str, Any] = {
        "role": "user",
        "kind": "message",
        "messageId": str(uuid.uuid4()),
        "parts": [
            {
                "kind": "data",
                "data": data,
                "metadata": {"extension": POLICY_BOOTSTRAP_EXTENSION},
            }
        ],
    }

    params: dict[str, Any] = {"message": a2a_message}
    if task_id:
        params["configuration"] = {"taskId": task_id}

    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": params,
    }


def parse_bootstrap_response(response: dict) -> str | None:
    """Extract ``context_id`` from a bootstrap response.

    Returns the context ID on success, or *None* if the response does not
    contain the expected bootstrap acknowledgement.
    """
    result = response.get("result", {})

    # Direct A2A message response
    context_id = _context_id_from_parts(result.get("parts", []))
    if context_id:
        return context_id

    # Status-based response
    status = result.get("status", {})
    message = status.get("message", {})
    if message:
        context_id = _context_id_from_parts(message.get("parts", []))
        if context_id:
            return context_id

    # Artifact-based response
    for artifact in result.get("artifacts", []) or []:
        context_id = _context_id_from_parts(artifact.get("parts", []))
        if context_id:
            return context_id

    return None


def _context_id_from_parts(parts: Any) -> str | None:
    if not isinstance(parts, list):
        return None
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("kind") == "data":
            data = part.get("data", {})
        elif "data" in part:
            data = part.get("data", {})
        else:
            continue
        if isinstance(data, dict) and data.get("bootstrapped"):
            context_id = data.get("context_id") or data.get("contextId")
            if context_id:
                return str(context_id)
    return None
