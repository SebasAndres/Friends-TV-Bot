"""Handler for the ``qubito telegram`` subcommand."""

from __future__ import annotations

from src.telegram.bot import run_bot


def run_telegram() -> None:
    """Start the Telegram bot."""
    run_bot()
