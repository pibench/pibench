"""Evaluator reward-info dimension tests."""

from pi_bench.evaluator import evaluate
from pi_bench.trace import TraceRecorder


def test_evaluate_returns_dimension_breakdown():
    trace = TraceRecorder()
    trace.record(
        tool_name="lookup_order",
        arguments={"order_id": "ORD1"},
        result_content="ok",
        result_error=False,
        pre_state_hash="a",
        post_state_hash="a",
    )
    trace.record(
        tool_name="record_decision",
        arguments={"decision": "DENY"},
        result_content="ok",
        result_error=False,
        pre_state_hash="a",
        post_state_hash="a",
    )

    task = {
        "evaluation_criteria": {
            "reward_basis": ["POLICY", "STATE_FIELD"],
            "policy_checks": [
                {"outcome_id": "D1", "type": "decision_equals", "equals": "DENY"},
                {"outcome_id": "T1", "type": "tool_called", "tool_name": "lookup_order"},
            ],
            "state_field_checks": [
                {
                    "outcome_id": "S1",
                    "type": "state_field",
                    "field_path": "activity.pending_requests[request_id=REQ1].status",
                    "equals": "held",
                }
            ],
        }
    }
    sim = {
        "termination_reason": "agent_stop",
        "messages": [],
        "trace": trace,
        "env": {
            "db": {
                "activity": {
                    "pending_requests": [{"request_id": "REQ1", "status": "pending"}],
                }
            }
        },
    }

    result = evaluate(task, sim, domain={})

    assert result["all_passed"] is False
    assert "dimensions" in result
    assert result["dimensions"]["decision"]["passed"] is True
    assert result["dimensions"]["outcomes"]["passed"] is True
    assert result["dimensions"]["state"]["passed"] is False
