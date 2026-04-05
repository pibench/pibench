"""Integration tests — green adapter ↔ purple reference server.

Uses Starlette TestClient (no real HTTP) with mocked LLM calls.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from pi_bench.a2a.bootstrap import (
    POLICY_BOOTSTRAP_EXTENSION,
    BenchmarkBootstrap,
    build_bootstrap_request,
    check_bootstrap_support,
    parse_bootstrap_response,
)


def _mock_llm_response(content="I'll verify the customer first.", tool_calls=None):
    """Build a mock litellm response with explicit attribute values."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls  # explicitly None avoids truthy MagicMock
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _get_llm_call_kwarg(mock_llm, key: str):
    """Extract a keyword argument from the mock LLM's most recent call."""
    call_kwargs = mock_llm.call_args
    return call_kwargs.kwargs.get(key) or call_kwargs[1].get(key)


class TestBootstrapHandshake:
    """Green adapter discovers agent card, bootstraps, gets context_id."""

    def test_bootstrap_handshake(self, purple_client):
        # 1. Discover agent card
        resp = purple_client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        card = resp.json()
        assert POLICY_BOOTSTRAP_EXTENSION in card["extensions"]

        # 2. Send bootstrap request
        bundle = BenchmarkBootstrap(
            policy_text="Always verify identity before transactions.",
            task_description="Wire transfer review",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "verify_identity",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            run_id="test-run-hsk",
            domain="finra",
        )
        bootstrap_req = build_bootstrap_request(bundle, task_id="task-hsk")
        resp = purple_client.post("/", json=bootstrap_req)
        assert resp.status_code == 200

        # 3. Parse context_id
        context_id = parse_bootstrap_response(resp.json())
        assert context_id is not None
        assert isinstance(context_id, str)
        # Verify it's a valid UUID
        uuid.UUID(context_id)


class TestBootstrappedTurn:
    """Bootstrapped request with context_id — purple prepends cached policy."""

    @patch("purple_reference.server.litellm.acompletion")
    def test_bootstrapped_turn(self, mock_llm, purple_client):
        mock_llm.return_value = _mock_llm_response("Identity verified. Proceeding.")

        # Bootstrap first
        bundle = BenchmarkBootstrap(
            policy_text="You must verify identity.",
            task_description="",
            tools=[],
            run_id="run-bt",
        )
        bootstrap_req = build_bootstrap_request(bundle)
        resp = purple_client.post("/", json=bootstrap_req)
        context_id = parse_bootstrap_response(resp.json())
        assert context_id is not None

        # Send a bootstrapped turn
        turn_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "messages": [
                                    {"role": "user", "content": "Process wire transfer $50k"}
                                ],
                                "context_id": context_id,
                            },
                        }
                    ],
                }
            },
        }
        resp = purple_client.post("/", json=turn_req)
        assert resp.status_code == 200

        # Verify LLM was called with system messages prepended
        messages = _get_llm_call_kwarg(mock_llm, "messages")
        assert messages[0]["role"] == "system"
        assert "verify identity" in messages[0]["content"]
        # User message follows
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any("wire transfer" in m["content"] for m in user_msgs)

        # Verify response structure
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"
        parts = result["status"]["message"]["parts"]
        assert any(p.get("text") or p.get("data") for p in parts)


class TestFallbackWhenNoAgentCard:
    """Green falls back to stateless when purple has no agent card."""

    def test_fallback_when_no_agent_card(self):
        # Create a purple server WITHOUT the agent card endpoint
        async def handle_post(request):
            body = await request.json()
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id", "1"),
                "result": {
                    "status": {
                        "state": "completed",
                        "message": {
                            "role": "agent",
                            "parts": [{"kind": "text", "text": "OK"}],
                        },
                    }
                },
            })

        app = Starlette(routes=[Route("/", handle_post, methods=["POST"])])
        client = TestClient(app)

        # check_bootstrap_support should return False (404 on agent card)
        import httpx

        # Use the test client's transport for the httpx client
        with httpx.Client(transport=client._transport, base_url="http://testserver") as hx:
            supported = check_bootstrap_support("http://testserver", hx)
        assert supported is False


class TestStatelessFullPayload:
    """Non-bootstrapped request sends full messages + tools."""

    @patch("purple_reference.server.litellm.acompletion")
    def test_stateless_full_payload(self, mock_llm, purple_client):
        mock_llm.return_value = _mock_llm_response("Done.")

        # Send a stateless request (no bootstrap, no context_id)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "lookup_account",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "messages": [
                                    {"role": "system", "content": "Be helpful"},
                                    {"role": "user", "content": "Look up account 123"},
                                ],
                                "tools": tools,
                            },
                        }
                    ],
                }
            },
        }
        resp = purple_client.post("/", json=req)
        assert resp.status_code == 200

        # LLM should have been called with both messages and tools
        messages = _get_llm_call_kwarg(mock_llm, "messages")
        called_tools = _get_llm_call_kwarg(mock_llm, "tools")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert called_tools == tools
