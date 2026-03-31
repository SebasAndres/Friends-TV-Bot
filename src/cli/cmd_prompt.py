"""Headless single-prompt mode: send one message, print the response, exit."""

from __future__ import annotations

import sys

from src.daemon.client import DaemonClient


def run_prompt(text: str, character: str | None = None) -> None:
    """Send a single prompt to the daemon, print the response, and exit."""
    client = DaemonClient()

    if not client.is_daemon_running():
        print("Error: daemon is not running. Start it with: qubito daemon start", file=sys.stderr)
        sys.exit(1)

    session = client.create_session(character=character, headless=True)
    try:
        data = client.send_message_full(session.id, text)
        print(data.get("response", ""))
    finally:
        client.delete_session(session.id)
        client.close()
