"""Checkpoint — save/load simulation results for incremental persistence."""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def save_incremental(
    simulations: list[dict], path: Path, lock: threading.Lock
) -> None:
    """Write current results to JSON file. Thread-safe via lock."""
    with lock:
        data = {"simulations": _make_serializable(simulations)}
        path.write_text(json.dumps(data, default=str, sort_keys=True))


def load_checkpoint(path: Path | str) -> dict | None:
    """Load existing results for resume. Returns None if file doesn't exist."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        logger.warning("Corrupted checkpoint file: %s — starting fresh", p)
        return None
    except OSError as exc:
        logger.warning("Cannot read checkpoint %s: %s — starting fresh", p, exc)
        return None


def make_info(
    domain: dict,
    agent: Any,
    user: Any,
    num_trials: int,
    seed: int | None,
    max_steps: int,
    max_errors: int,
    max_concurrency: int,
    solo: bool,
    observer_mode: str = "audit_only",
) -> dict:
    """Build metadata dict."""
    return {
        "domain": domain.get("name", "unknown"),
        "agent_model": getattr(agent, "model_name", "unknown"),
        "user_model": getattr(user, "model_name", "unknown") if user else "none",
        "num_trials": num_trials,
        "seed": seed,
        "max_steps": max_steps,
        "max_errors": max_errors,
        "max_concurrency": max_concurrency,
        "solo": solo,
        "observer_mode": observer_mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _make_serializable(simulations: list[dict]) -> list[dict]:
    """Make simulation dicts JSON-serializable by converting problem values."""
    result = []
    for sim in simulations:
        s = {}
        for k, v in sim.items():
            if k == "messages":
                s[k] = _clean_messages(v)
            else:
                s[k] = v
        result.append(s)
    return result


def _clean_messages(messages: list[dict]) -> list[dict]:
    """Remove non-serializable items from messages."""
    clean = []
    for msg in messages:
        m = {}
        for k, v in msg.items():
            try:
                json.dumps(v, default=str)
                m[k] = v
            except (TypeError, ValueError):
                m[k] = str(v)
        clean.append(m)
    return clean
