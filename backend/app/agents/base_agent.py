import uuid
from typing import Any, Dict, Tuple
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Abstract base class for all autonomous agents in the RailMind ecosystem.
    Provides standard logging, timing, and interface contract structures.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    @abstractmethod
    async def process(self, state: Any) -> Tuple[Dict[str, Any], float, str]:
        """
        Processes the current network state and returns:
        1. A dict of state modifications.
        2. A confidence score between 0.0 and 1.0.
        3. A detailed reasoning text explaining the agent's logic.
        """
        pass

    def log(self, message: str):
        print(f"[{self.agent_name}] {message}")

    def _generate_uuid(self) -> str:
        return str(uuid.uuid4())
