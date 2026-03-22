from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_RULES_DIR = Path(__file__).resolve().parent.parent.parent / "rules"


@dataclass(frozen=True)
class RuleData:
    name: str
    priority: int
    content: str


def _parse_rule_file(path: Path) -> RuleData:
    """Parse a rule markdown file with frontmatter."""
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        return RuleData(name=path.stem, priority=50, content=text.strip())

    _, frontmatter, body = text.split("---", 2)

    meta: dict[str, str] = {}
    for line in frontmatter.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return RuleData(
        name=meta.get("name", path.stem),
        priority=int(meta.get("priority", "50")),
        content=body.strip(),
    )


def load_all_rules() -> str:
    """Load all rule .md files, sorted by priority, and return concatenated text."""
    if not _RULES_DIR.exists():
        return ""

    rules = [_parse_rule_file(p) for p in _RULES_DIR.glob("*.md")]
    rules.sort(key=lambda r: r.priority)
    return "\n\n".join(r.content for r in rules)
