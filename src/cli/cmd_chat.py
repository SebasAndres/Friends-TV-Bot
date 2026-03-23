"""Interactive terminal chat loop."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.agents.agent import Agent
from src.agents.agent_manager import AgentManager
from src.mcp import get_mcp_manager
from src.skills import load_all_skills, SkillRegistry
from src.skills.generators import set_output_dirs
from src.display import (
    console,
    print_goodbye,
    print_response,
    print_user_message,
    print_welcome,
    prompt_input,
    set_commands,
    thinking_spinner,
)

if TYPE_CHECKING:
    from src.config.resolver import QConfig


def run_chat(config: QConfig) -> None:
    """Run the interactive assistant terminal loop."""
    # Configure generator output dirs (prefer project-local .qubito/, then global)
    if config.local_dir:
        set_output_dirs(
            agents=config.local_dir / "agents",
            skills=config.local_dir / "skills",
            rules=config.local_dir / "rules",
        )
    elif config.global_dir.exists():
        set_output_dirs(
            agents=config.global_dir / "agents",
            skills=config.global_dir / "skills",
            rules=config.global_dir / "rules",
        )

    skills = SkillRegistry(load_all_skills(dirs=config.skills_dirs))
    agent: Agent = AgentManager.start_agent(config=config)

    mcp_tools: list[str] | None = None
    if agent.mcp_manager:
        mcp_tools = [t["name"] for t in agent.mcp_manager.get_tools()]

    set_commands([(s.name, s.description) for s in skills.list_all()])

    greeting = agent.get_start_message()
    print_welcome(agent.name, agent.emoji, agent.color, greeting, mcp_tools)

    try:
        while True:
            user_input = prompt_input(agent.emoji)

            if not user_input:
                continue

            if user_input in ['q', '/exit', '/quit']:
                print_goodbye(agent.name, agent.emoji, agent.bye_message)
                break

            print_user_message(user_input)

            # Skill dispatch
            if user_input.startswith('/'):
                command = user_input.split()[0].lstrip('/')

                if command == "ctx":
                    command = "context"

                skill = skills.get(command)

                if skill is None:
                    console.print(f"[red]Unknown command: /{command}[/red]. Type /help for available commands.")
                    continue

                if skill.skill_type == "handler":
                    skills.execute_handler(skill, agent, user_input)
                    continue

                if skill.skill_type == "llm":
                    user_msg = user_input[len(f"/{command}"):].strip()
                    t0 = time.monotonic()
                    with thinking_spinner(agent.thinking, agent.color):
                        response = agent.message(
                            user_msg or skill.instructions,
                            skill_instructions=skill.instructions,
                        )
                    elapsed = time.monotonic() - t0
                    agent.response_times.append(elapsed)
                    print_response(agent.name, agent.emoji, agent.color, response, elapsed)
                    continue

            # Regular conversation
            t0 = time.monotonic()
            with thinking_spinner():
                response = agent.message(user_input)
            elapsed = time.monotonic() - t0
            agent.response_times.append(elapsed)
            print_response(agent.name, agent.emoji, agent.color, response, elapsed)

    finally:
        mcp = get_mcp_manager()
        if mcp:
            mcp.close()
