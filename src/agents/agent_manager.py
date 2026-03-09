import random

from src.agents import (
    Agent,
    get_joey,
    get_monica,
    get_ross,
    get_chandler,
    get_phoebe,
)

class AgentManager:
    """Factory/cache helper for selecting character agents."""

    AVAILABLE_CONSTRUCTORS = {
        'joey': get_joey,
        'monica': get_monica,
        'ross': get_ross,
        'chandler': get_chandler,
        'phoebe': get_phoebe,
    }

    AGENTS = { }

    @staticmethod
    def start_random_agent() -> Agent:
        """
        Randomly selects and starts an agent from the available agents.

        Parameters
        ----------
        None
            Static method with no runtime parameters.

        Returns
        -------
        Agent
            An instance of the randomly selected agent.
        """

        agent_name = random.choice(list(AgentManager.AVAILABLE_CONSTRUCTORS.keys()))
        if agent_name in AgentManager.AGENTS:
            return AgentManager.AGENTS[agent_name]

        agent_constructor_class = AgentManager.AVAILABLE_CONSTRUCTORS[agent_name]
        AgentManager.AGENTS[agent_name] = agent_constructor_class()
        return AgentManager.AGENTS[agent_name]
