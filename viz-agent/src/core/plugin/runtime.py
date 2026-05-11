from typing import Any, Optional

from core.plugin.interfaces import GuardrailPlugin
from core.plugin.registry import PluginRegistry


class AgentRuntime:
    """
    Orchestrates guardrail validation and supervisor graph invocation.
    The supervisor graph handles all routing and agent sequencing internally.
    Supports both sync (invoke) and async (ainvoke) execution.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        llm: Any,
        supervisor: Any,
        guardrail: Optional[GuardrailPlugin] = None,
        checkpointer: Optional[Any] = None,
        router: Optional[Any] = None,  # retained for interface compatibility, unused
    ):
        self.registry = registry
        self.llm = llm
        self.supervisor = supervisor
        self.guardrail = guardrail
        self.checkpointer = checkpointer

    def _check_guardrail(self, state: dict) -> Optional[dict]:
        """Returns a blocked response dict if guardrail rejects, else None."""
        if not self.guardrail:
            return None
        allowed, message = self.guardrail.validate(state)
        if not allowed:
            return {"messages": [message]}
        return None

    def invoke(self, state: dict, config: Optional[dict] = None) -> dict:
        blocked = self._check_guardrail(state)
        if blocked:
            return blocked
        return self.supervisor.invoke(state, config=config)

    async def ainvoke(self, state: dict, config: Optional[dict] = None) -> dict:
        blocked = self._check_guardrail(state)
        if blocked:
            return blocked
        return await self.supervisor.ainvoke(state, config=config)

    def shutdown(self) -> None:
        self.registry.shutdown()
