#!/usr/bin/env python3
"""Generate the staged helpdesk admin-password-reset batch."""

from __future__ import annotations

from pathlib import Path

from pi_bench.generator.catalog import generate_helpdesk_admin_password_reset_batch
from pi_bench.generator.core import write_scenarios


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    output_dir = workspace_root / "scenarios" / "generated" / "helpdesk"
    scenarios = generate_helpdesk_admin_password_reset_batch()
    paths = write_scenarios(scenarios, output_dir)
    print(f"Wrote {len(paths)} scenario(s) to {output_dir}")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
