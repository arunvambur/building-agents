from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class AgentPlugin(ABC):
    name: str

    @abstractmethod
    def build_graph(self, llm: Any, tools: list, checkpointer: Optional[Any] = None) -> Any:
        """Build and return a compiled LangGraph graph."""

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class RouterPlugin(ABC):

    @abstractmethod
    def route(self, state: dict) -> str:
        """Return the name of the agent that should handle this state."""


class ToolPlugin(ABC):
    name: str

    @abstractmethod
    def get_tools(self) -> list:
        """Return a list of LangChain tools."""

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class GuardrailPlugin(ABC):

    @abstractmethod
    def validate(self, state: dict) -> Tuple[bool, Optional[Any]]:
        """
        Validate the incoming state synchronously.
        Returns (True, None) if allowed, (False, AIMessage) if blocked.
        """

    async def avalidate(self, state: dict) -> Tuple[bool, Optional[Any]]:
        """
        Async variant of validate. Default implementation offloads to a thread
        so blocking LLM calls do not stall the event loop.
        Subclasses may override with a native async implementation.
        """
        import asyncio
        return await asyncio.to_thread(self.validate, state)

