"""Unit tests for pi_bench.a2a.bootstrap — 24 tests across 6 classes.

Tests the green-side bootstrap functions directly. The purple server
fixtures provide the other end for integration tests (see test_a2a_smoke.py).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import httpx

from pi_bench.a2a.bootstrap import (
    POLICY_BOOTSTRAP_EXTENSION,
    BenchmarkBootstrap,
    build_bootstrap_request,
    check_bootstrap_support,
    parse_bootstrap_response,
)


# ── TestBenchmarkBootstrap ───────────────────────────────


class TestBenchmarkBootstrap:
    """Dataclass construction and defaults."""

    def test_defaults(self):
        bundle = BenchmarkBootstrap(
            policy_text="Be compliant",
            task_description="Test task",
        )
        assert bundle.policy_text == "Be compliant"
        assert bundle.task_description == "Test task"
        assert bundle.tools == []
        assert bundle.domain == ""
        # run_id is a valid UUID
        uuid.UUID(bundle.run_id)

    def test_explicit_construction(self, bootstrap_bundle):
        assert bootstrap_bundle.policy_text
        assert bootstrap_bundle.task_description == "Handle a wire transfer request"
        assert len(bootstrap_bundle.tools) == 2
        assert bootstrap_bundle.run_id == "test-run-001"
        assert bootstrap_bundle.domain == "finra"


# ── TestBuildBootstrapRequest ────────────────────────────


class TestBuildBootstrapRequest:
    """JSON structure of the bootstrap request."""

    def test_bootstrap_flag_is_true(self, bootstrap_bundle):
        req = build_bootstrap_request(bootstrap_bundle)
        data = req["params"]["message"]["parts"][0]["data"]
        assert data["bootstrap"] is True

    def test_policy_and_tools_present(self, bootstrap_bundle):
        req = build_bootstrap_request(bootstrap_bundle)
        data = req["params"]["message"]["parts"][0]["data"]
        assert data["policy_text"] == bootstrap_bundle.policy_text
        assert data["tools"] == bootstrap_bundle.tools

    def test_extension_metadata(self, bootstrap_bundle):
        req = build_bootstrap_request(bootstrap_bundle)
        part = req["params"]["message"]["parts"][0]
        assert part["metadata"]["extension"] == POLICY_BOOTSTRAP_EXTENSION

    def test_jsonrpc_envelope(self, bootstrap_bundle):
        req = build_bootstrap_request(bootstrap_bundle)
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "message/send"
        # id is a valid UUID
        uuid.UUID(req["id"])

    def test_task_id_handling(self, bootstrap_bundle):
        # Without task_id
        req_no_task = build_bootstrap_request(bootstrap_bundle)
        assert "configuration" not in req_no_task["params"]

        # With task_id
        req_with_task = build_bootstrap_request(bootstrap_bundle, task_id="task-42")
        assert req_with_task["params"]["configuration"]["taskId"] == "task-42"


# ── TestParseBootstrapResponse ───────────────────────────


class TestParseBootstrapResponse:
    """Extracting context_id from bootstrap responses."""

    def test_valid_bootstrap_response(self):
        response = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "status": {
                    "state": "completed",
                    "message": {
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "data",
                                "data": {
                                    "bootstrapped": True,
                                    "context_id": "ctx-abc-123",
                                },
                            }
                        ],
                    },
                }
            },
        }
        assert parse_bootstrap_response(response) == "ctx-abc-123"

    def test_non_bootstrap_response(self):
        response = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "status": {
                    "state": "completed",
                    "message": {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": "Hello"}],
                    },
                }
            },
        }
        assert parse_bootstrap_response(response) is None

    def test_empty_result(self):
        response = {"jsonrpc": "2.0", "id": "1", "result": {}}
        assert parse_bootstrap_response(response) is None

    def test_bootstrapped_false(self):
        response = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "status": {
                    "message": {
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "data",
                                "data": {
                                    "bootstrapped": False,
                                    "context_id": "ctx-nope",
                                },
                            }
                        ],
                    }
                }
            },
        }
        assert parse_bootstrap_response(response) is None


# ── TestBuildA2ARequestBootstrapped ──────────────────────


class TestBuildA2ARequestBootstrapped:
    """Bootstrapped request structure (from purple_adapter module-level functions)."""

    def _build(self, messages, context_id, task_id=None):
        from pi_bench.a2a.purple_adapter import _build_a2a_request_bootstrapped

        return _build_a2a_request_bootstrapped(messages, context_id, task_id)

    def test_system_messages_stripped(self):
        messages = [
            {"role": "system", "content": "Be safe"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        req = self._build(messages, "ctx-1")
        data = req["params"]["message"]["parts"][0]["data"]
        roles = [m["role"] for m in data["messages"]]
        assert "system" not in roles
        assert "user" in roles

    def test_context_id_included(self):
        req = self._build(
            [{"role": "user", "content": "Hi"}], "ctx-42"
        )
        data = req["params"]["message"]["parts"][0]["data"]
        assert data["context_id"] == "ctx-42"

    def test_no_tools_key(self):
        req = self._build(
            [{"role": "user", "content": "Hi"}], "ctx-1"
        )
        data = req["params"]["message"]["parts"][0]["data"]
        assert "tools" not in data

    def test_valid_jsonrpc(self):
        req = self._build(
            [{"role": "user", "content": "Hi"}], "ctx-1", task_id="t-1"
        )
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "message/send"
        assert req["params"]["configuration"]["taskId"] == "t-1"


# ── TestCheckBootstrapSupport ────────────────────────────


class TestCheckBootstrapSupport:
    """Agent card discovery and extension checking."""

    def _mock_client(self, json_data=None, status_code=200, error=None):
        client = MagicMock(spec=httpx.Client)
        if error:
            client.get.side_effect = error
        else:
            response = MagicMock()
            response.status_code = status_code
            response.json.return_value = json_data or {}
            if status_code >= 400:
                response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "error", request=MagicMock(), response=response
                )
            else:
                response.raise_for_status.return_value = None
            client.get.return_value = response
        return client

    def test_true_when_extension_present(self):
        client = self._mock_client({"extensions": [POLICY_BOOTSTRAP_EXTENSION]})
        assert check_bootstrap_support("http://purple:9100", client) is True

    def test_false_when_missing(self):
        client = self._mock_client({"extensions": ["other:ext"]})
        assert check_bootstrap_support("http://purple:9100", client) is False

    def test_false_when_empty_extensions(self):
        client = self._mock_client({"extensions": []})
        assert check_bootstrap_support("http://purple:9100", client) is False

    def test_false_on_404(self):
        client = self._mock_client(status_code=404)
        assert check_bootstrap_support("http://purple:9100", client) is False

    def test_false_on_network_error(self):
        client = self._mock_client(error=httpx.ConnectError("refused"))
        assert check_bootstrap_support("http://purple:9100", client) is False


# ── TestA2APurpleAgentFallback ───────────────────────────


class TestA2APurpleAgentFallback:
    """A2APurpleAgent bootstrap/fallback behavior."""

    def test_default_not_bootstrapped(self):
        from pi_bench.a2a.purple_adapter import A2APurpleAgent

        agent = A2APurpleAgent("http://purple:9100")
        assert agent._bootstrapped is False
        assert agent._context_id is None

    @patch("pi_bench.a2a.purple_adapter.check_bootstrap_support", return_value=False)
    def test_falls_back_when_unsupported(self, mock_check):
        from pi_bench.a2a.purple_adapter import A2APurpleAgent

        agent = A2APurpleAgent("http://purple:9100")
        state = agent.init_state(
            system_messages=[{"role": "system", "content": "Be safe"}],
            tools=[{"name": "t1", "parameters": {}}],
        )
        assert agent._bootstrapped is False
        assert "messages" in state
        assert "tools" in state

    @patch("pi_bench.a2a.purple_adapter.parse_bootstrap_response", return_value="ctx-999")
    @patch("pi_bench.a2a.purple_adapter.build_bootstrap_request")
    @patch("pi_bench.a2a.purple_adapter.check_bootstrap_support", return_value=True)
    def test_bootstraps_when_supported(self, mock_check, mock_build, mock_parse):
        from pi_bench.a2a.purple_adapter import A2APurpleAgent

        mock_build.return_value = {"jsonrpc": "2.0", "id": "1", "method": "message/send", "params": {}}

        agent = A2APurpleAgent("http://purple:9100")
        # Mock the HTTP post for bootstrap
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {}}
        mock_response.raise_for_status.return_value = None
        agent._client.post = MagicMock(return_value=mock_response)

        state = agent.init_state(
            system_messages=[{"role": "system", "content": "Be safe"}],
            tools=[{"name": "t1", "parameters": {}}],
        )
        assert agent._bootstrapped is True
        assert agent._context_id == "ctx-999"

    @patch("pi_bench.a2a.purple_adapter.check_bootstrap_support", side_effect=Exception("boom"))
    def test_falls_back_on_error(self, mock_check):
        from pi_bench.a2a.purple_adapter import A2APurpleAgent

        agent = A2APurpleAgent("http://purple:9100")
        state = agent.init_state(
            system_messages=[{"role": "system", "content": "Be safe"}],
            tools=[],
        )
        assert agent._bootstrapped is False
