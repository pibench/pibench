"""Read run save files whether they are plain (`.json`, as a run writes them)
or gzip-compressed (`.json.gz`, as they are committed: the raw files are
50-85 MB each, too large for the git host)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path


def read_results(path: Path) -> dict:
    """The save file at `path`, or its `.gz` copy; {} if neither exists."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    gz = path.with_name(path.name + ".gz")
    if gz.exists():
        with gzip.open(gz, "rt") as f:
            return json.load(f)
    return {}


def results_files(folder: Path, pattern: str = "wave*_*.json") -> list[Path]:
    """Save files matching `pattern`, each once (plain name even when only the .gz exists)."""
    folder = Path(folder)
    found = {p for p in folder.glob(pattern)}
    found |= {p.with_name(p.name[:-3]) for p in folder.glob(pattern + ".gz")}
    return sorted(found)
