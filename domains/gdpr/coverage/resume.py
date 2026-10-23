"""Resume support for run_wave.sh: list unfinished episodes, merge a part file.

  python3 domains/gdpr/coverage/resume.py todo <save_file> <id,id,...>
      prints the comma-separated ids not yet completed in <save_file>
      (missing, or ended in agent_error); prints nothing when all are done.
  python3 domains/gdpr/coverage/resume.py merge <save_file> <part_file>
      replaces/adds the part file's episodes in the save file (by task id)
      and deletes the part file.

Scores are always recomputed from `simulations` (registry, report, ledger),
so the run-level `metrics` block of a merged file is dropped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMPLETED = ("agent_stop", "user_stop", "max_steps")


def _load(path: Path) -> dict:
    from results_io import read_results
    try:
        return read_results(path)
    except (json.JSONDecodeError, EOFError, OSError):
        return {}


def todo(save: Path, ids: list[str]) -> list[str]:
    done = {s.get("task_id") for s in _load(save).get("simulations", [])
            if s.get("termination_reason") in COMPLETED}
    return [i for i in ids if i not in done]


def merge(save: Path, part: Path) -> None:
    base, new = _load(save), _load(part)
    sims = {s.get("task_id"): s for s in base.get("simulations", [])}
    for s in new.get("simulations", []):
        sims[s.get("task_id")] = s
    out = {"info": {**base.get("info", {}), "merged_from": [str(save.name), str(part.name)]} if base
           else new.get("info", {}), "simulations": sorted(sims.values(), key=lambda s: s.get("task_id") or "")}
    save.write_text(json.dumps(out, indent=2, default=str))
    part.unlink(missing_ok=True)
    print(f"merged {len(new.get('simulations', []))} episodes into {save.name}: {len(out['simulations'])} total")


if __name__ == "__main__":
    cmd, save = sys.argv[1], Path(sys.argv[2])
    if cmd == "todo":
        print(",".join(todo(save, [i for i in sys.argv[3].split(",") if i])))
    elif cmd == "merge":
        merge(save, Path(sys.argv[3]))
