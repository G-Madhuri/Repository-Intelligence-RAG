from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    """
    Abstract Base Class for all LLM-callable tools.
    Compatible with Model Context Protocol (MCP) and agent execution environments.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Executes the tool's action with provided arguments."""
        pass
