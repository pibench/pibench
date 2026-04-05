#!/usr/bin/env python3
"""A2A demo — start a purple agent server and run pi-bench assessment via A2A.

Usage:
    # Start server + run all scenarios
    python examples/a2a_demo/run_a2a.py --model gpt-4o-mini --port 8766

    # Connect to an already-running server
    python examples/a2a_demo/run_a2a.py --external --port 8766
"""

from __future__ import annotations

import argparse
import atexit
import logging
import subprocess
import sys
import time

import httpx

from pi_bench.a2a.assessment import run_assessment

logger = logging.getLogger(__name__)


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Poll /health until the server is ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{url}/health", timeout=5.0)
            if resp.status_code == 200:
                return True
        except httpx.ConnectError:
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pi-bench assessment via A2A")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="LiteLLM model name")
    parser.add_argument("--port", type=int, default=8766, help="Server port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--scenarios-dir", type=str, default="scenarios", help="Scenarios directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-steps", type=int, default=50, help="Max steps per scenario")
    parser.add_argument("--external", action="store_true", help="Connect to an already-running server")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    purple_url = f"http://{args.host}:{args.port}"
    server_proc = None

    if not args.external:
        # Start the purple server as a subprocess
        server_cmd = [
            sys.executable, "examples/a2a_demo/purple_server.py",
            "--model", args.model,
            "--port", str(args.port),
            "--host", "0.0.0.0",
        ]
        if args.seed is not None:
            server_cmd.extend(["--seed", str(args.seed)])

        logger.info("Starting purple server: %s", " ".join(server_cmd))
        server_proc = subprocess.Popen(server_cmd)

        def cleanup():
            if server_proc and server_proc.poll() is None:
                logger.info("Stopping purple server (pid=%d)", server_proc.pid)
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_proc.kill()

        atexit.register(cleanup)

        # Wait for server to be ready
        logger.info("Waiting for server at %s ...", purple_url)
        if not wait_for_server(purple_url):
            print(f"ERROR: Server did not start within 30s at {purple_url}")
            if server_proc.poll() is not None:
                print(f"Server process exited with code {server_proc.returncode}")
            sys.exit(1)
        logger.info("Server is ready")

    # Run assessment
    config = {
        "scenarios_dir": args.scenarios_dir,
        "max_steps": args.max_steps,
        "seed": args.seed,
    }

    print(f"\nRunning assessment against {purple_url}")
    print(f"  Model: {args.model}")
    print(f"  Scenarios: {args.scenarios_dir}")
    print()

    try:
        results = run_assessment(purple_url, config)
    except Exception as exc:
        print(f"ERROR: Assessment failed: {exc}")
        sys.exit(1)

    # Print results
    for result in results:
        status = result.get("status", "unknown")
        scenario_id = result.get("scenario_id", "?")
        if status == "error":
            print(f"  [{status.upper()}] {scenario_id}: {result.get('error', 'unknown')}")
        else:
            passed = "PASS" if result.get("all_passed") else "FAIL"
            decision = result.get("canonical_decision", "?")
            duration = result.get("duration", 0)
            print(f"  [{passed}] {scenario_id}: decision={decision} ({duration:.1f}s)")

    # Summary
    print()
    passed = sum(1 for r in results if r.get("all_passed"))
    errors = sum(1 for r in results if r.get("status") == "error")
    total = len(results)
    print(f"Total: {total}  Passed: {passed}  Failed: {total - passed - errors}  Errors: {errors}")


if __name__ == "__main__":
    main()
