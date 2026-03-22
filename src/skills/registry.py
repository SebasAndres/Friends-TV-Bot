from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from src.skills.skill_loader import SkillData

if TYPE_CHECKING:
    from src.agents.agent import Agent


class SkillRegistry:
    """Maps slash commands to skill definitions and dispatches execution."""

    def __init__(self, skills: list[SkillData]) -> None:
        self._skills: dict[str, SkillData] = {s.name: s for s in skills}

    def get(self, name: str) -> SkillData | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillData]:
        return list(self._skills.values())

    def execute_handler(self, skill: SkillData, agent: Agent, user_input: str) -> None:
        """Resolve dotted handler path and call it with (agent, user_input)."""
        if not skill.handler:
            raise ValueError(f"Skill '{skill.name}' has no handler defined")

        module_path, _, func_name = skill.handler.rpartition(".")
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        func(agent, user_input)
