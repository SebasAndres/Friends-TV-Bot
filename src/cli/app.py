"""Qubito CLI entry point with subcommands."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config.resolver import QConfig


def _logging_setup() -> None:
    """Configure application and dependency logging levels."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.CRITICAL)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qubito", description="Qubito — natural-language OS")
    sub = parser.add_subparsers(dest="command")

    # qubito chat (default)
    sub.add_parser("chat", help="Interactive terminal chat")

    # qubito init
    init_p = sub.add_parser("init", help="Scaffold .qubito/ directories")
    init_p.add_argument("--global-only", action="store_true", help="Only create ~/.qubito/")

    # qubito telegram
    sub.add_parser("telegram", help="Run the Telegram bot")

    return parser


def main() -> None:
    """CLI entry point."""
    _logging_setup()

    parser = _build_parser()
    args = parser.parse_args()

    config = QConfig(project_dir=Path.cwd())

    command = args.command or "chat"

    if command == "chat":
        from src.cli.cmd_chat import run_chat
        run_chat(config)
    elif command == "init":
        from src.cli.cmd_init import run_init
        run_init(global_only=args.global_only)
    elif command == "telegram":
        from src.cli.cmd_telegram import run_telegram
        run_telegram()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
