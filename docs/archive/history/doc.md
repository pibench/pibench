# Project Folder Rearrangement — What Was Done

## Problem

The project had three copies of the codebase in different locations:

- **`original/`** — the latest code with the most recent changes (the "good" version)
- **`src/pi_bench/`** — older version of the code (stale)
- **`new_original/`** — someone else's copy of the project

This caused confusion about which code was authoritative. The goal was to make `original/` the single active codebase under `src/pi_bench/`, and back up everything else.

## What Was Done

### Step 1: Created backup directories

```
backup/others_backup/    <- for new_original/ contents
backup/base_backup/      <- for old root-level items
```

### Step 2: Moved `new_original/` contents into `backup/others_backup/`

All contents of `new_original/` were moved into `backup/others_backup/`:

`.gitignore`, `backup/`, `docs/`, `domains/`, `purple_reference/`, `pyproject.toml`, `scenario_archive/`, `scenarios/`, `scratchpad/`, `scripts/`, `src/`, `tau2bench_adapter/`, `temp/`, `tests/`

The empty `new_original/` directory was then deleted.

### Step 3: Moved old root-level items into `backup/base_backup/`

These items were moved from the project root into `backup/base_backup/`:

`src/` (containing the old `pi_bench/`), `data/`, `docs/`, `domains/`, `scenarios/`, `scenario_archive/`, `scripts/`, `scratchpad/`, `tests/`, `temp/`, `tau2bench_adapter/`, `purple_reference/`, `pyproject.toml`, `README.md`

Items that stayed at root: `.git/`, `.claude/`, `.pytest_cache/`, `original/`, `backup/`

### Step 4: Moved `original/` contents into `src/pi_bench/`

Created a fresh `src/pi_bench/` directory and moved all of `original/`'s contents into it:

`__init__.py`, `a2a/`, `data/`, `decision/`, `domains/`, `environment/`, `evaluator/`, `event_flags/`, `metrics.py`, `observer/`, `orchestrator/`, `protocols.py`, `runner/`, `scenario_loader.py`, `trace/`, `types.py`, `users/`

Also created `src/__init__.py` to make `src` a proper Python package.

The empty `original/` directory was then deleted.

### Step 5: Fixed imports in moved code

Updated import references in the moved files:

- `src/pi_bench/users/user.py` — changed `from original.types import is_stop_signal` to `from pi_bench.types import is_stop_signal`
- `src/pi_bench/users/scripted_user.py` — same change

## Final Project Structure

```
new_pi-bench/
├── .git/
├── .claude/
├── backup/
│   ├── others_backup/          <- contents from new_original/
│   ├── base_backup/            <- old root items (old src/, docs/, domains/, etc.)
│   ├── 2026-02-24_orchestrator_rebuild/
│   ├── 2026-02-24_routing_refactor/
│   ├── 20260303_scen009_removed/
│   ├── bdd_archive_2026-02-24/
│   └── retired_check_engine/
├── src/
│   ├── __init__.py
│   └── pi_bench/               <- active codebase (moved from original/)
│       ├── __init__.py
│       ├── a2a/
│       ├── data/
│       ├── decision/
│       ├── domains/
│       ├── environment/
│       ├── evaluator/
│       ├── event_flags/
│       ├── metrics.py
│       ├── observer/
│       ├── orchestrator/
│       ├── protocols.py
│       ├── runner/
│       ├── scenario_loader.py
│       ├── trace/
│       ├── types.py
│       └── users/
└── doc.md                      <- this file
```

## Key Differences: Old vs New `src/pi_bench/`

| Only in old (now in backup/base_backup/src/pi_bench/) | Only in new (current src/pi_bench/) |
|-------------------------------------------------------|-------------------------------------|
| `agents/`                                             | `data/`                             |
| `run_scenarios.py`                                    |                                     |
| `server/`                                             |                                     |
| `validate.py`                                         |                                     |

The new codebase from `original/` is leaner — it removed `agents/`, `server/`, `run_scenarios.py`, and `validate.py`, and added a `data/` folder.

## Verification

- `backup/others_backup/` contains all former `new_original/` contents
- `backup/base_backup/` contains all former root items
- `src/pi_bench/` contains all former `original/` contents
- `original/` and `new_original/` directories no longer exist
- All `from original.` imports updated to `from pi_bench.`
- `python -c "from pi_bench.types import is_stop_signal"` works with `PYTHONPATH=src`
