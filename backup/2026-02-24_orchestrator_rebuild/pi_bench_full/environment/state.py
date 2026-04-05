"""State management — DB hashing, comparison, and mutation."""

import hashlib
import json
from typing import Any

Env = dict[str, Any]


def get_db_hash(env: Env) -> str:
    """Deterministic SHA-256 hash of the environment's database state."""
    serialized = json.dumps(env["db"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def set_state(env: Env, db: dict) -> None:
    """Replace the environment's database with a new state."""
    env["db"] = db


def check_db(env: Env, reference: dict) -> bool:
    """Check if the environment's DB matches a reference by hash."""
    current = json.dumps(env["db"], sort_keys=True, separators=(",", ":"))
    expected = json.dumps(reference, sort_keys=True, separators=(",", ":"))
    return (
        hashlib.sha256(current.encode("utf-8")).hexdigest()
        == hashlib.sha256(expected.encode("utf-8")).hexdigest()
    )


def is_solo_mode(env: Env) -> bool:
    """Check if the environment is in solo mode."""
    return env["solo_mode"]


def set_solo_mode(env: Env, solo: bool) -> None:
    """Toggle solo mode. When on, user tool calls are rejected."""
    env["solo_mode"] = solo
