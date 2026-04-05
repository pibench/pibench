"""ENV_ASSERTION evaluator — run callable assertions against the environment.

Matches tau2-bench behavior: multiplicative scoring. One failed
assertion zeroes out the entire evaluator (1.0 * 0.0 = 0.0).
"""

import logging

logger = logging.getLogger(__name__)


def evaluate_env_assertions(assertions: list[dict], domain: dict) -> float:
    """Run assertion functions against the environment.

    Each assertion has a 'function' key with a callable.
    Returns 1.0 if all callable assertions pass, 0.0 if any fail.
    Only assertions with a callable function are evaluated.
    """
    if not assertions:
        return 1.0

    callable_assertions = [a for a in assertions if a.get("function") and callable(a["function"])]
    if not callable_assertions:
        return 1.0

    reward = 1.0
    for assertion in callable_assertions:
        fn = assertion["function"]
        try:
            result = fn(domain)
            if not result:
                logger.info("ENV_ASSERTION: assertion failed: %s", fn.__name__ if hasattr(fn, '__name__') else str(fn))
                reward *= 0.0
        except Exception as exc:
            logger.warning("ENV_ASSERTION: assertion raised exception: %s", exc)
            reward *= 0.0

    return reward
