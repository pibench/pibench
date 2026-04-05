"""Evaluator — reward composition dispatcher."""

from pi_bench.evaluator.action import evaluate_actions
from pi_bench.evaluator.communicate import evaluate_communicate
from pi_bench.evaluator.db import evaluate_db
from pi_bench.evaluator.env_assertion import evaluate_env_assertions
from pi_bench.evaluator.nl_assertion import evaluate_nl_assertions


def evaluate(task: dict, simulation: dict, domain: dict) -> dict:
    """Run all evaluators, compose reward. Returns RewardInfo dict.

    RewardInfo = {
        "reward": float,        # 0.0 to 1.0
        "reward_basis": list,   # which evaluators ran
        "reward_breakdown": dict,  # per-evaluator details
    }
    """
    termination = simulation.get("termination_reason", "")
    normal_endings = ("agent_stop", "user_stop")

    if termination not in normal_endings:
        return {
            "reward": 0.0,
            "reward_basis": [],
            "reward_breakdown": {"reason": f"abnormal_termination:{termination}"},
        }

    criteria = task.get("evaluation_criteria", {})
    if not criteria:
        return {
            "reward": 1.0,
            "reward_basis": [],
            "reward_breakdown": {},
        }

    reward_basis = criteria.get("reward_basis", [])
    if not reward_basis:
        return {
            "reward": 1.0,
            "reward_basis": [],
            "reward_breakdown": {},
        }

    breakdown = {}
    rewards = []

    for evaluator_type in reward_basis:
        if evaluator_type == "ACTION":
            expected = criteria.get("expected_actions", [])
            r = evaluate_actions(expected, simulation.get("messages", []))
            breakdown["ACTION"] = r
            rewards.append(r)

        elif evaluator_type == "DB":
            r = evaluate_db(task, simulation, domain)
            breakdown["DB"] = r
            rewards.append(r)

        elif evaluator_type == "COMMUNICATE":
            info = criteria.get("communicate_info", [])
            r = evaluate_communicate(info, simulation.get("messages", []))
            breakdown["COMMUNICATE"] = r
            rewards.append(r)

        elif evaluator_type == "ENV_ASSERTION":
            assertions = criteria.get("env_assertions", [])
            r = evaluate_env_assertions(assertions, domain)
            breakdown["ENV_ASSERTION"] = r
            rewards.append(r)

        elif evaluator_type == "NL_ASSERTION":
            nl_assertions = criteria.get("nl_assertions", [])
            generate_fn = domain.get("nl_generate_fn")
            if generate_fn is not None:
                r = evaluate_nl_assertions(
                    nl_assertions, simulation.get("messages", []), generate_fn
                )
            else:
                r = 0.0
            breakdown["NL_ASSERTION"] = r
            rewards.append(r)

    final = 1.0
    for r in rewards:
        final *= r

    return {
        "reward": final,
        "reward_basis": reward_basis,
        "reward_breakdown": breakdown,
    }


__all__ = [
    "evaluate",
    "evaluate_actions",
    "evaluate_communicate",
    "evaluate_db",
    "evaluate_env_assertions",
    "evaluate_nl_assertions",
]
