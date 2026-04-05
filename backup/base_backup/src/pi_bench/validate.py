"""Validate pi-bench scenario files.

Usage:
    python -m pi_bench.validate [scenarios_dir]
    python -m pi_bench.validate workspace/scenarios/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pi_bench.evaluator.scenario_validator import validate_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pi-bench scenario files")
    parser.add_argument(
        "scenarios_dir",
        nargs="?",
        type=Path,
        help="Directory containing scenario JSON files (default: auto-discover)",
    )
    args = parser.parse_args()

    # Determine scenarios directory (same pattern as run_scenarios.py)
    scenarios_dir = args.scenarios_dir
    if scenarios_dir is None:
        cwd = Path.cwd()
        if (cwd / "workspace" / "scenarios").is_dir():
            scenarios_dir = cwd / "workspace" / "scenarios"
        elif cwd.name == "workspace" and (cwd / "scenarios").is_dir():
            scenarios_dir = cwd / "scenarios"
        elif (cwd / "scenarios").is_dir():
            scenarios_dir = cwd / "scenarios"
        else:
            print("No scenarios directory found. Pass path as argument.", file=sys.stderr)
            sys.exit(1)

    if not scenarios_dir.is_dir():
        print(f"Not a directory: {scenarios_dir}", file=sys.stderr)
        sys.exit(1)

    # Count all JSON files for the summary
    all_files = sorted(scenarios_dir.rglob("*.json"))
    total_files = len(all_files)

    if total_files == 0:
        print(f"No JSON files found in {scenarios_dir}")
        sys.exit(0)

    # Validate
    errors_by_file = validate_all(scenarios_dir)

    # Print errors
    for filename, errors in sorted(errors_by_file.items()):
        print(f"\n{filename}:")
        for err in errors:
            print(f"  - {err}")

    # Summary
    n_errors = len(errors_by_file)
    n_valid = total_files - n_errors
    print(f"\n{total_files} files checked, {n_valid} valid, {n_errors} with errors")

    sys.exit(1 if n_errors > 0 else 0)


if __name__ == "__main__":
    main()
