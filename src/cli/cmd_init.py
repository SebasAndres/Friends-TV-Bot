"""Handler for the ``qubito init`` subcommand."""

from __future__ import annotations

from pathlib import Path

from src.config.scaffold import scaffold_global, scaffold_project
from src.display import console


def run_init(global_only: bool = False) -> None:
    """Scaffold .qubito/ directories.

    Always creates ~/.qubito/ (global).
    Also creates .qubito/ in cwd unless *global_only* is True.
    """
    gpath = scaffold_global()
    console.print(f"[green]Global config:[/green] {gpath}")

    if not global_only:
        ppath = scaffold_project(Path.cwd())
        console.print(f"[green]Project config:[/green] {ppath}")
