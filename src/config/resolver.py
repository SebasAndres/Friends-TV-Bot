"""Two-tier configuration resolver for Qubito.

Resolves paths from three layers (highest priority first):
1. Project-local: .qubito/ in the given project directory
2. Global: ~/.qubito/
3. Legacy fallback: project root (agents/, skills/, rules/, mcp_servers.json)
"""

from __future__ import annotations

from pathlib import Path

_GLOBAL_DIR = Path.home() / ".qubito"
_LOCAL_DIR_NAME = ".qubito"

_RESOURCE_DIRS = ("agents", "skills", "rules", "mcp")


class QConfig:
    """Resolved configuration paths for a Qubito session."""

    def __init__(self, project_dir: Path | None = None) -> None:
        self._global_dir = _GLOBAL_DIR
        self._project_dir = project_dir
        self._local_dir = (project_dir / _LOCAL_DIR_NAME) if project_dir else None

    # ------------------------------------------------------------------
    # Public path accessors
    # ------------------------------------------------------------------

    @property
    def global_dir(self) -> Path:
        return self._global_dir

    @property
    def local_dir(self) -> Path | None:
        return self._local_dir

    @property
    def agents_dirs(self) -> list[Path]:
        return self._collect_dirs("agents")

    @property
    def skills_dirs(self) -> list[Path]:
        return self._collect_dirs("skills")

    @property
    def rules_dirs(self) -> list[Path]:
        return self._collect_dirs("rules")

    @property
    def mcp_dirs(self) -> list[Path]:
        return self._collect_dirs("mcp")

    @property
    def memory_dir(self) -> Path:
        """Memory always lives under global ~/.qubito/memory/."""
        return self._global_dir / "memory"

    # ------------------------------------------------------------------
    # Merged resource loading
    # ------------------------------------------------------------------

    def merged_files(self, resource: str, pattern: str = "*.md") -> list[Path]:
        """Return files for a resource type, project-local overriding global by filename.

        Files are collected from all directories for the resource type.
        When the same filename exists in multiple layers, the highest-priority
        layer (project-local > global > legacy) wins.
        """
        seen: dict[str, Path] = {}
        # Iterate lowest-priority first so higher layers overwrite
        for d in reversed(self._collect_dirs(resource)):
            if d.is_dir():
                for p in sorted(d.glob(pattern)):
                    seen[p.name] = p
        return sorted(seen.values(), key=lambda p: p.name)

    def mcp_config_paths(self) -> list[Path]:
        """Return all existing MCP config JSON files, highest priority first."""
        candidates: list[Path] = []
        # Project-local
        if self._local_dir:
            p = self._local_dir / "mcp" / "servers.json"
            if p.exists():
                candidates.append(p)
        # Global
        p = self._global_dir / "mcp" / "servers.json"
        if p.exists():
            candidates.append(p)
        # Legacy fallback
        if self._project_dir:
            p = self._project_dir / "mcp_servers.json"
            if p.exists():
                candidates.append(p)
        return candidates

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _collect_dirs(self, resource: str) -> list[Path]:
        """Return directories for a resource type, highest priority first."""
        dirs: list[Path] = []
        # Project-local .qubito/<resource>/
        if self._local_dir:
            d = self._local_dir / resource
            if d.is_dir():
                dirs.append(d)
        # Global ~/.qubito/<resource>/
        d = self._global_dir / resource
        if d.is_dir():
            dirs.append(d)
        # Legacy fallback: project root <resource>/
        if self._project_dir:
            d = self._project_dir / resource
            if d.is_dir():
                dirs.append(d)
        return dirs
