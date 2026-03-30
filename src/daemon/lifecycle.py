"""Daemon process lifecycle: start, stop, status via PID file."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

from src.constants import DAEMON_HOST, DAEMON_PORT

PID_FILE = Path.home() / ".qubito" / "daemon.pid"
LOG_FILE = Path.home() / ".qubito" / "daemon.log"


def _resolve_python() -> Path:
    """Return the project virtualenv Python, falling back to sys.executable."""
    venv_python = Path.cwd() / ".venv" / "bin" / "python"
    if venv_python.is_file():
        return venv_python
    return Path(sys.executable)


def _base_url() -> str:
    return f"http://{DAEMON_HOST}:{DAEMON_PORT}"


def is_running() -> tuple[bool, int | None]:
    """Check if the daemon process is alive via PID file.

    Returns
    -------
    tuple of (bool, int or None)
        Whether the process is alive, and its PID if so.
    """
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True, pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return False, None


def start_daemon(
    host: str | None = None,
    port: int | None = None,
    foreground: bool = False,
) -> None:
    """Start the daemon process.

    Parameters
    ----------
    host : str or None
        Bind address. Defaults to DAEMON_HOST.
    port : int or None
        Bind port. Defaults to DAEMON_PORT.
    foreground : bool
        If True, run in the current process instead of forking.
    """
    running, pid = is_running()
    if running:
        print(f"Daemon already running (PID {pid})")
        return

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    if foreground:
        PID_FILE.write_text(str(os.getpid()))
        try:
            from src.daemon.server import run_server
            run_server(host=host, port=port)
        finally:
            PID_FILE.unlink(missing_ok=True)
        return

    log_handle = LOG_FILE.open("a")
    python = _resolve_python()
    proc = subprocess.Popen(
        [str(python), "-m", "src.daemon.server"],
        start_new_session=True,
        stdout=log_handle,
        stderr=log_handle,
        cwd=Path.cwd(),
    )
    PID_FILE.write_text(str(proc.pid))
    _wait_for_ready(timeout=15)
    print(f"Daemon started (PID {proc.pid}) on {_base_url()}")


def stop_daemon() -> None:
    """Stop the daemon process gracefully."""
    running, pid = is_running()
    if not running:
        print("Daemon is not running")
        return

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        try:
            os.kill(pid, 0)
            time.sleep(0.5)
        except ProcessLookupError:
            break
    else:
        os.kill(pid, signal.SIGKILL)

    PID_FILE.unlink(missing_ok=True)
    print("Daemon stopped")


def daemon_status() -> dict | None:
    """Get daemon status from the API, or None if not reachable.

    Returns
    -------
    dict or None
        Status payload with ``pid`` injected, or None if daemon is down.
    """
    running, pid = is_running()
    if not running:
        return None
    try:
        resp = httpx.get(f"{_base_url()}/status", timeout=3)
        data = resp.json()
        data["pid"] = pid
        return data
    except httpx.ConnectError:
        return {"pid": pid, "status": "starting"}


_SERVICE_TEMPLATE = """\
[Unit]
Description=Qubito AI Agent Daemon
After=network.target

[Service]
Type=simple
ExecStart={python} -m src.daemon.server
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""

_SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
_SERVICE_NAME = "qubito.service"


def install_service() -> None:
    """Install a systemd --user service for the Qubito daemon."""
    _SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    unit = _SERVICE_TEMPLATE.format(
        python=_resolve_python(),
        working_dir=Path.cwd(),
    )
    service_path = _SERVICE_DIR / _SERVICE_NAME
    service_path.write_text(unit)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "qubito"], check=True)
    print(f"Service installed at {service_path}")
    print("Start with: systemctl --user start qubito")


def uninstall_service() -> None:
    """Remove the systemd --user service."""
    subprocess.run(["systemctl", "--user", "disable", "--now", "qubito"], check=False)
    service_path = _SERVICE_DIR / _SERVICE_NAME
    if service_path.exists():
        service_path.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        print("Service uninstalled")
    else:
        print("Service not found")


def _wait_for_ready(timeout: int = 15) -> None:
    """Poll /status until the server responds or timeout.

    Parameters
    ----------
    timeout : int
        Maximum seconds to wait before giving up.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{_base_url()}/status", timeout=2)
            if resp.status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(0.5)
