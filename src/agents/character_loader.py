from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DIR = Path(__file__).resolve().parent.parent.parent / "agents"


@dataclass(frozen=True)
class CharacterData:
    name: str
    emoji: str
    color: str
    hi_message: str
    personality: str
    bye_message: str = "has left the chat."
    thinking: tuple[str, ...] = ()


def _parse_character_file(path: Path) -> CharacterData:
    """Parse a character markdown file with YAML-like frontmatter."""
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Character file {path.name} missing frontmatter")

    _, frontmatter, body = text.split("---", 2)

    meta: dict[str, str] = {}
    for line in frontmatter.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        meta[key.strip()] = value

    required = ("name", "emoji", "color", "hi_message")
    for field in required:
        if field not in meta:
            raise ValueError(f"Character file {path.name} missing required field: {field}")

    thinking = tuple(
        t.strip() for t in meta.get("thinking", "").split("|") if t.strip()
    )

    return CharacterData(
        name=meta["name"],
        emoji=meta["emoji"],
        color=meta["color"],
        hi_message=meta["hi_message"],
        personality=body.strip(),
        bye_message=meta.get("bye_message", "has left the chat."),
        thinking=thinking,
    )


def _collect_files(dirs: list[Path] | None = None) -> list[Path]:
    """Collect .md files from given dirs, deduplicating by filename (first wins)."""
    search_dirs = dirs if dirs else [_DEFAULT_DIR]
    seen: dict[str, Path] = {}
    for d in search_dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.md")):
                if p.name not in seen:
                    seen[p.name] = p
    return sorted(seen.values(), key=lambda p: p.name)


def load_all_characters(dirs: list[Path] | None = None) -> list[CharacterData]:
    """Discover and load all .md character files from the given directories."""
    return [_parse_character_file(p) for p in _collect_files(dirs)]


def load_character_by_filename(filename: str, dirs: list[Path] | None = None) -> CharacterData:
    """Load a specific character by its .md filename (without extension)."""
    for p in _collect_files(dirs):
        if p.stem == filename:
            return _parse_character_file(p)
    available = [p.stem for p in _collect_files(dirs)]
    raise FileNotFoundError(
        f"Character '{filename}' not found. Available: {', '.join(available)}"
    )


def load_random_character(dirs: list[Path] | None = None) -> CharacterData:
    """Pick a random .md file and parse only that one."""
    import random
    paths = _collect_files(dirs)
    if not paths:
        raise FileNotFoundError("No character .md files found")
    return _parse_character_file(random.choice(paths))
