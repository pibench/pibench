#!/usr/bin/env python3
"""Validate the checked-in scenario corpus for structural and tool validity."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pi_bench.evaluator.generated_scenario_checks import validate_generated_scenario_file
from pi_bench.scenario_loader import discover_scenarios


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=_default_workspace_root(),
        help="Workspace root used to resolve domain assets",
    )
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=None,
        help="Scenario directory to scan (defaults to <workspace>/scenarios)",
    )
    args = parser.parse_args(argv)

    workspace_root = args.workspace_root
    scenarios_dir = args.scenarios_dir or (workspace_root / "scenarios")
    paths = discover_scenarios(scenarios_dir)

    failures: list[tuple[Path, list[str]]] = []
    for path in paths:
        errors = validate_generated_scenario_file(path, workspace_root)
        if errors:
            failures.append((path, errors))

    if failures:
        for path, errors in failures:
            print(f"[FAIL] {path}")
            for error in errors:
                print(f"  - {error}")
        print(f"\n{len(failures)} scenario(s) failed validation.")
        return 1

    print(f"Validated {len(paths)} scenario(s): structural checks and domain tool references passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
