"""Scaffold .qubito/ directory structures."""

from __future__ import annotations

from pathlib import Path

_SUBDIRS = ("agents", "memory", "skills", "rules", "mcp")


def scaffold_global() -> Path:
    """Create ~/.qubito/ with all subdirectories. Returns the path."""
    base = Path.home() / ".qubito"
    _create_structure(base)
    return base


def scaffold_project(project_dir: Path | None = None) -> Path:
    """Create .qubito/ in the given directory (default: cwd). Returns the path."""
    base = (project_dir or Path.cwd()) / ".qubito"
    _create_structure(base)
    return base


def _create_structure(base: Path) -> None:
    """Create the base directory and all expected subdirectories."""
    for sub in _SUBDIRS:
        (base / sub).mkdir(parents=True, exist_ok=True)
