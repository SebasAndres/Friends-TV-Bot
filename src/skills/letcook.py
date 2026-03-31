"""Letcook: autonomous producer/evaluator loop handler.

Integrates the letcook autonomous loop engine as a qubito skill.
Supports init (scaffold), run (execute loop), and list (show tasks).
"""

from __future__ import annotations

import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.agent import Agent

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "letcook_templates"
_TASKS_DIR = Path.home() / ".qubito" / "letcook"


def handle_letcook(agent: Agent, user_input: str) -> None:
    """Dispatch letcook subcommands: init, run, list."""
    from src.display import console

    action, arg = _parse_input(user_input)

    if action == "init":
        _handle_init(arg, console)
    elif action == "run":
        _handle_run(agent, arg, console)
    elif action == "list":
        _handle_list(console)
    else:
        console.print("[yellow]Usage:[/yellow]")
        console.print("  /letcook init [dir]   — scaffold a new task")
        console.print("  /letcook run [dir]    — run the autonomous loop")
        console.print("  /letcook list         — list existing tasks")


def _parse_input(user_input: str) -> tuple[str, str]:
    """Parse letcook subcommand and argument."""
    parts = user_input.strip().split(None, 2)
    if len(parts) < 2:
        return "help", ""
    sub = parts[1]
    rest = parts[2] if len(parts) > 2 else ""
    if sub in ("init", "run", "list"):
        return sub, rest
    return "help", ""


def _handle_init(target: str, console: object) -> None:
    """Scaffold a new letcook task directory with specs templates."""
    target_dir = _resolve_task_dir(target)
    specs_dir = target_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Initializing letcook task in:[/bold] {target_dir}")

    for name in ("skill.md", "program.md", "restrictions.md"):
        src = _TEMPLATES_DIR / name
        dst = specs_dir / name
        if dst.exists():
            console.print(f"  [yellow]SKIP[/yellow]   {dst.name} (already exists)")
        else:
            shutil.copy2(src, dst)
            console.print(f"  [green]CREATE[/green] {dst.name}")

    (target_dir / "output").mkdir(exist_ok=True)

    console.print()
    console.print("[bold green]Task scaffolded.[/bold green]")
    console.print("[dim]Next steps:[/dim]")
    console.print(f"  1. Edit [bold]{specs_dir}/program.md[/bold]      — define your task")
    console.print(f"  2. Edit [bold]{specs_dir}/restrictions.md[/bold] — set quality gates")
    console.print(f"  3. Run:  [cyan]/letcook run {target_dir.name}[/cyan]")


def _handle_list(console: object) -> None:
    """List existing letcook task directories."""
    if not _TASKS_DIR.is_dir():
        console.print("[yellow]No tasks found. Run /letcook init <name> first.[/yellow]")
        return

    tasks = sorted(
        d for d in _TASKS_DIR.iterdir()
        if d.is_dir() and (d / "specs" / "program.md").exists()
    )
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    console.print("\n[bold]Letcook tasks:[/bold]")
    for task_dir in tasks:
        state = _read_loop_state(task_dir / "loop-state.md")
        status_str = f"[dim]{state}[/dim]" if state else "[dim]not started[/dim]"
        console.print(f"  [green]{task_dir.name}[/green] — {status_str}")
    console.print()


def _handle_run(agent: Agent, target: str, console: object) -> None:
    """Execute the autonomous producer/evaluator loop."""
    target_dir = _resolve_task_dir(target)

    for spec in ("specs/skill.md", "specs/program.md", "specs/restrictions.md"):
        if not (target_dir / spec).exists():
            console.print(
                f"[red]Missing {spec}. Run /letcook init {target} first.[/red]"
            )
            return

    skill_text = (target_dir / "specs" / "skill.md").read_text(encoding="utf-8")
    program_text = (target_dir / "specs" / "program.md").read_text(encoding="utf-8")
    restrictions_text = (target_dir / "specs" / "restrictions.md").read_text(encoding="utf-8")

    fm = _parse_frontmatter(program_text)
    max_iter = int(fm.get("iterations", "5"))
    threshold = int(fm.get("completion_threshold", "90"))
    goal = _parse_goal(program_text)

    console.print(f"[bold]Running letcook loop:[/bold] {target_dir.name}")
    console.print(f"  [dim]Goal:[/dim] {goal}")
    console.print(
        f"  [dim]Max iterations:[/dim] {max_iter}  "
        f"[dim]Threshold:[/dim] {threshold}"
    )
    console.print()

    instructions = _build_execution_prompt(
        skill_text, program_text, restrictions_text, str(target_dir),
    )

    original_rounds = agent.ai_model.max_tool_rounds
    agent.ai_model.max_tool_rounds = max(original_rounds, 30)

    start = time.monotonic()
    try:
        result = agent.message(
            f"Execute the autonomous loop for the task in {target_dir}.",
            skill_instructions=instructions,
        )
    finally:
        agent.ai_model.max_tool_rounds = original_rounds

    elapsed = time.monotonic() - start
    console.print(f"\n[bold green]Loop complete.[/bold green] ({elapsed:.1f}s)")

    state_file = target_dir / "loop-state.md"
    if state_file.exists():
        status = _read_loop_state(state_file)
        console.print(f"  [dim]Status:[/dim] {status}")

    console.print(f"\n{result}\n")


def _build_execution_prompt(
    skill_text: str,
    program_text: str,
    restrictions_text: str,
    working_dir: str,
) -> str:
    """Compose the full execution prompt from the three spec files."""
    return (
        f"You are executing an autonomous producer/evaluator loop.\n"
        f"Working directory: {working_dir}\n\n"
        f"Follow the loop engine specification below exactly.\n\n"
        f"--- LOOP ENGINE (specs/skill.md) ---\n{skill_text}\n"
        f"--- END LOOP ENGINE ---\n\n"
        f"--- PROGRAM (specs/program.md) ---\n{program_text}\n"
        f"--- END PROGRAM ---\n\n"
        f"--- RESTRICTIONS (specs/restrictions.md) ---\n{restrictions_text}\n"
        f"--- END RESTRICTIONS ---\n"
    )


def _resolve_task_dir(name: str) -> Path:
    """Resolve a task name to a directory path."""
    if not name:
        return _TASKS_DIR / f"task-{datetime.now():%Y%m%d-%H%M%S}"

    p = Path(name).expanduser()
    if p.is_absolute():
        return p

    # Check if it's a name under ~/.qubito/letcook/
    candidate = _TASKS_DIR / name
    if candidate.exists():
        return candidate

    # Check as relative path from cwd
    cwd_candidate = Path.cwd() / name
    if cwd_candidate.exists():
        return cwd_candidate

    # Default to creating under ~/.qubito/letcook/
    return _TASKS_DIR / name


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML-like frontmatter fields from markdown text."""
    match = re.match(r"^---\n(.*?\n)---", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^(\w+):\s*(.+?)(?:\s*#.*)?$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def _parse_goal(text: str) -> str:
    """Extract the first non-empty line from the ## Goal section."""
    in_goal = False
    for line in text.splitlines():
        if re.match(r"^##\s+Goal", line):
            in_goal = True
            continue
        if in_goal:
            if re.match(r"^##\s", line):
                break
            if line.startswith("<!--") or not line.strip():
                continue
            return line.strip()
    return "(not set)"


def _read_loop_state(state_file: Path) -> str:
    """Read the current status from a loop-state.md file."""
    if not state_file.exists():
        return "not started"
    text = state_file.read_text(encoding="utf-8")
    if "## Summary" in text:
        match = re.search(r"\*\*Final status\*\*:\s*(.+)", text)
        return match.group(1).strip() if match else "done"
    # Find last iteration status
    statuses = re.findall(r"\*\*Status\*\*:\s*(.+)", text)
    return statuses[-1].strip() if statuses else "running"
