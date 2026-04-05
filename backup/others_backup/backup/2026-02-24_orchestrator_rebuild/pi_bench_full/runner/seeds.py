"""Seed derivation — deterministic SHA-256 trial seeds."""

import hashlib


def derive_trial_seeds(
    base_seed: int, tasks: list[dict], num_trials: int
) -> list[tuple[dict, int, int]]:
    """Generate (task, trial, seed) tuples with SHA-256 derived seeds.

    seed = int(sha256(f"{base_seed}:{task_id}:{trial}").hexdigest()[:8], 16)
    Order-independent: changing task count doesn't shift other seeds.
    """
    result = []
    for task in tasks:
        for trial in range(num_trials):
            h = hashlib.sha256(
                f"{base_seed}:{task['id']}:{trial}".encode()
            ).hexdigest()[:8]
            trial_seed = int(h, 16)
            result.append((task, trial, trial_seed))
    return result


def build_work_queue(
    tasks: list[dict],
    num_trials: int,
    base_seed: int,
    completed: set[tuple],
) -> list[tuple[dict, int, int]]:
    """Generate (task, trial, seed) tuples, excluding completed."""
    all_work = derive_trial_seeds(base_seed, tasks, num_trials)
    return [
        (task, trial, seed)
        for task, trial, seed in all_work
        if (task["id"], trial) not in completed
    ]
