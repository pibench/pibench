"""ENV_ASSERTION evaluator — run callable assertions against the environment."""


def evaluate_env_assertions(assertions: list[dict], domain: dict) -> float:
    """Run assertion functions against the environment.

    Each assertion has a 'function' key with a callable.
    Returns fraction of assertions that pass.
    """
    if not assertions:
        return 1.0

    passed = 0
    for assertion in assertions:
        fn = assertion.get("function")
        if fn and callable(fn):
            try:
                result = fn(domain)
                if result:
                    passed += 1
            except Exception:
                pass

    return passed / len(assertions)
