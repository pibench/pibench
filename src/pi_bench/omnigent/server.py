"""Lifecycle of a private local OmniGent server + runner.

The benchmark never uses the user's normal OmniGent server. It starts its own
server (SQLite under a run directory) and one runner bound to it with a random
tunnel token; one runner serves every session.
"""

from __future__ import annotations

import atexit
import hashlib
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Header every internal request to the OmniGent server must carry
# (omnigent.runner.identity.OMNIGENT_INTERNAL_WS_ORIGIN).
INTERNAL_ORIGIN = "omnigent://internal"

_READY_TIMEOUT_S = 90.0

# Environment variables that must not leak into the harness processes:
# this machine may itself be running inside Claude Code, whose variables
# (e.g. ANTHROPIC_BASE_URL, CLAUDECODE) would redirect or alter the Claude CLI.
_SCRUB_PREFIXES = ("CLAUDE", "ANTHROPIC_")
_SCRUB_EXACT = {"OMNIGENT_RUNNER_WORKSPACE"}


def token_bound_runner_id(token: str) -> str:
    """Runner id authorized by a tunnel binding token (mirrors omnigent.runner.identity)."""
    stripped = token.strip()
    if not stripped:
        raise RuntimeError("tunnel binding token must not be empty")
    digest = hashlib.sha256(f"omnigent-runner:{stripped}".encode()).hexdigest()
    return f"runner_token_{digest[:32]}"


def resolve_omnigent_python() -> str:
    """Find the Python interpreter of the installed OmniGent tool.

    Order: ``PI_BENCH_OMNIGENT_PYTHON``; the shebang of the ``omnigent`` CLI;
    the default ``uv tool`` location.
    """
    explicit = os.environ.get("PI_BENCH_OMNIGENT_PYTHON")
    if explicit:
        return explicit
    cli = shutil.which("omnigent")
    if cli:
        try:
            first = Path(os.path.realpath(cli)).read_text(errors="ignore").splitlines()[0]
            if first.startswith("#!"):
                interpreter = first[2:].strip().split()[0]
                if Path(interpreter).exists():
                    return interpreter
        except (OSError, IndexError):
            pass
    default = Path.home() / ".local/share/uv/tools/omnigent/bin/python"
    if default.exists():
        return str(default)
    raise RuntimeError(
        "OmniGent is not installed (no `omnigent` CLI found). Install it or set "
        "PI_BENCH_OMNIGENT_PYTHON to the interpreter of an OmniGent environment."
    )


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _harness_env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(_SCRUB_PREFIXES) and k not in _SCRUB_EXACT
    }
    env["DO_NOT_TRACK"] = "1"
    env["OMNIGENT_DISABLE_TELEMETRY"] = "1"
    return env


class OmniGentServer:
    """A private OmniGent server + runner pair. Use as a context manager or start()/stop()."""

    def __init__(self, run_dir: str | Path | None = None, python: str | None = None) -> None:
        self.python = python or resolve_omnigent_python()
        self._owns_dir = run_dir is None
        self.run_dir = Path(run_dir) if run_dir else Path(tempfile.mkdtemp(prefix="pibench-omnigent-"))
        self.base_url = ""
        self.runner_id = ""
        self._server: subprocess.Popen[bytes] | None = None
        self._runner: subprocess.Popen[bytes] | None = None
        self._watchdog: subprocess.Popen[bytes] | None = None

    # ── lifecycle ──

    def start(self) -> "OmniGentServer":
        if self.running:
            return self
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "artifacts").mkdir(exist_ok=True)
        port = _free_port()
        self.base_url = f"http://127.0.0.1:{port}"
        token = uuid.uuid4().hex
        self.runner_id = token_bound_runner_id(token)
        env = _harness_env()
        self._server = subprocess.Popen(
            [self.python, "-m", "omnigent.cli", "server", "--port", str(port),
             "--database-uri", f"sqlite:///{self.run_dir / 'omnigent.db'}",
             "--artifact-location", str(self.run_dir / "artifacts")],
            env={**env, "OMNIGENT_RUNNER_TUNNEL_TOKEN": token},
            cwd=str(self.run_dir),
            stdout=(self.run_dir / "server.log").open("wb"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._runner = subprocess.Popen(
            [self.python, "-m", "omnigent.runner._entry"],
            env={**env, "OMNIGENT_RUNNER_ID": self.runner_id,
                 "OMNIGENT_RUNNER_TUNNEL_BINDING_TOKEN": token,
                 "OMNIGENT_RUNNER_PARENT_PID": str(os.getpid()),
                 "RUNNER_SERVER_URL": self.base_url},
            cwd=str(self.run_dir),
            stdout=(self.run_dir / "runner.log").open("wb"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._watchdog = _spawn_watchdog(self._server, self._runner)
        self._wait_ready()
        logger.info("OmniGent server ready at %s (logs in %s)", self.base_url, self.run_dir)
        return self

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + _READY_TIMEOUT_S
        while time.monotonic() < deadline:
            for proc, name in ((self._server, "server"), (self._runner, "runner")):
                if proc is not None and proc.poll() is not None:
                    raise RuntimeError(f"OmniGent {name} exited early; see {self.run_dir}/{name}.log")
            try:
                health = httpx.get(f"{self.base_url}/health", timeout=2)
                status = httpx.get(f"{self.base_url}/v1/runners/{self.runner_id}/status", timeout=2)
                if health.status_code == 200 and status.status_code == 200 and status.json().get("online"):
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.3)
        self.stop()
        raise RuntimeError(f"OmniGent server/runner not ready in {_READY_TIMEOUT_S}s; see {self.run_dir}")

    def stop(self) -> None:
        """Stop runner and server, including any child processes they spawned.

        Each runs in its own process group: on macOS the framework Python
        launcher re-spawns the interpreter as a child, so signalling only the
        launcher PID would orphan the real server.
        """
        for proc in (self._runner, self._server):
            if proc is None:
                continue
            _signal_group(proc, signal.SIGTERM)
            try:
                proc.wait(timeout=3)  # private server: no need for a long graceful drain
            except subprocess.TimeoutExpired:
                pass
            _signal_group(proc, signal.SIGKILL)
        if self._watchdog is not None and self._watchdog.poll() is None:
            self._watchdog.kill()
        self._server = self._runner = self._watchdog = None

    @property
    def running(self) -> bool:
        return self._server is not None and self._server.poll() is None

    def client(self, timeout: float | None = 300.0) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=timeout, headers={"Origin": INTERNAL_ORIGIN})

    def __enter__(self) -> "OmniGentServer":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()


# Kills the server/runner process groups if the pi-bench process dies without
# calling stop() (e.g. SIGKILL), so no OmniGent server is ever orphaned.
_WATCHDOG = """
import os, signal, sys, time
parent, groups = int(sys.argv[1]), [int(g) for g in sys.argv[2:]]
def alive(pid):
    try:
        os.kill(pid, 0); return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
while alive(parent) and any(alive(g) for g in groups):
    time.sleep(1)
for g in groups:
    try: os.killpg(g, signal.SIGKILL)
    except (ProcessLookupError, PermissionError): pass
"""


def _spawn_watchdog(*procs: subprocess.Popen[bytes] | None) -> subprocess.Popen[bytes]:
    groups = [str(p.pid) for p in procs if p is not None]
    return subprocess.Popen(
        [sys.executable, "-c", _WATCHDOG, str(os.getpid()), *groups],
        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _signal_group(proc: subprocess.Popen[bytes], sig: int) -> None:
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


_shared: OmniGentServer | None = None
_shared_lock = threading.Lock()


def get_shared_server() -> OmniGentServer:
    """Process-wide server, started on first use and stopped at exit.

    ``PI_BENCH_OMNIGENT_RUN_DIR`` sets where its database and logs live.
    """
    global _shared
    with _shared_lock:
        if _shared is None or not _shared.running:
            run_dir = os.environ.get("PI_BENCH_OMNIGENT_RUN_DIR") or None
            _shared = OmniGentServer(run_dir=run_dir).start()
            atexit.register(_shared.stop)
        return _shared
