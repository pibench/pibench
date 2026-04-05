"""Shared fixtures for purple reference tests."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from pi_bench.a2a.bootstrap import BenchmarkBootstrap

# Importing from sibling — add purple_reference to path at collection time
import sys
from pathlib import Path

_purple_root = Path(__file__).resolve().parent.parent
if str(_purple_root.parent) not in sys.path:
    sys.path.insert(0, str(_purple_root.parent))

from purple_reference.server import DEFAULT_MODEL, create_app


# ── Sample data ──────────────────────────────────────────


SAMPLE_POLICY = (
    "You are a compliance officer. Always verify customer identity "
    "before processing any financial transaction."
)

SAMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_identity",
            "description": "Verify customer identity",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_transaction",
            "description": "Process a financial transaction",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "account": {"type": "string"},
                },
                "required": ["amount", "account"],
            },
        },
    },
]


# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture
def sample_policy() -> str:
    return SAMPLE_POLICY


@pytest.fixture
def sample_tools() -> list[dict]:
    return SAMPLE_TOOLS


@pytest.fixture
def bootstrap_bundle(sample_policy: str, sample_tools: list[dict]) -> BenchmarkBootstrap:
    return BenchmarkBootstrap(
        policy_text=sample_policy,
        task_description="Handle a wire transfer request",
        tools=sample_tools,
        run_id="test-run-001",
        domain="finra",
    )


@pytest.fixture
def purple_app() -> Starlette:
    """Starlette test app with the purple reference server."""
    return create_app(host="testserver", port=9100, model=DEFAULT_MODEL)


@pytest.fixture
def purple_client(purple_app) -> TestClient:
    """httpx-backed test client for the purple server (no real HTTP)."""
    return TestClient(purple_app)
