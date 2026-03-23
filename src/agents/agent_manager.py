from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.agent import Agent
from src.agents.character_loader import load_character_by_filename, load_random_character
from src.constants import DEFAULT_CHARACTER
from src.rules import load_all_rules

if TYPE_CHECKING:
    from src.config.resolver import QConfig


class AgentManager:
    """Factory/cache helper for selecting character agents."""

    AGENTS: dict[str, Agent] = {}

    @staticmethod
    def start_agent(config: QConfig | None = None) -> Agent:
        """Start the default character agent, or a random one if unset.

        Uses the ``DEFAULT_CHARACTER`` env var (filename without .md).
        Falls back to a random character when the variable is empty.
        """
        agent_dirs = config.agents_dirs if config else None
        rules_dirs = config.rules_dirs if config else None
        mcp_paths = config.mcp_config_paths() if config else None

        if DEFAULT_CHARACTER:
            character = load_character_by_filename(DEFAULT_CHARACTER, dirs=agent_dirs)
        else:
            character = load_random_character(dirs=agent_dirs)

        if character.name in AgentManager.AGENTS:
            return AgentManager.AGENTS[character.name]

        rules = load_all_rules(dirs=rules_dirs)
        agent = Agent(character, rules=rules, mcp_config_paths=mcp_paths)
        AgentManager.AGENTS[character.name] = agent
        return agent
