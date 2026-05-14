import logging
from typing import Any, Optional

from core.plugin.interfaces import GuardrailPlugin
from core.plugin.registry import PluginRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Orchestrates guardrail validation and supervisor graph invocation.
    Supports both sync (invoke) and async (ainvoke) execution.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        llm: Any,
        supervisor: Any,
        guardrail: Optional[GuardrailPlugin] = None,
        checkpointer: Optional[Any] = None,
        router: Optional[Any] = None,
    ):
        self.registry = registry
        self.llm = llm
        self.supervisor = supervisor
        self.guardrail = guardrail
        self.checkpointer = checkpointer
        logger.info("AgentRuntime initialised — agents: %s", registry.agent_names)

    def _check_guardrail(self, state: dict) -> Optional[dict]:
        if not self.guardrail:
            return None
        user_text = state.get("messages", [{}])[-1]
        content = getattr(user_text, "content", "")[:80]
        logger.debug("[guardrail] checking: %r", content)
        allowed, message = self.guardrail.validate(state)
        if not allowed:
            logger.warning("[guardrail] BLOCKED: %r", content)
            return {"messages": [message]}
        logger.debug("[guardrail] allowed")
        return None

    def invoke(self, state: dict, config: Optional[dict] = None) -> dict:
        content = getattr(state.get("messages", [None])[-1], "content", "")[:80]
        logger.info("[runtime] invoke — user: %r", content)
        blocked = self._check_guardrail(state)
        if blocked:
            return blocked
        result = self.supervisor.invoke(state, config=config)
        last = result.get("messages", [None])[-1]
        last_content = getattr(last, "content", "")[:120]
        logger.info("[runtime] invoke complete — last message: %r", last_content)
        return result

    async def ainvoke(self, state: dict, config: Optional[dict] = None) -> dict:
        content = getattr(state.get("messages", [None])[-1], "content", "")[:80]
        logger.info("[runtime] ainvoke — user: %r", content)
        blocked = self._check_guardrail(state)
        if blocked:
            return blocked
        result = await self.supervisor.ainvoke(state, config=config)
        last = result.get("messages", [None])[-1]
        last_content = getattr(last, "content", "")[:120]
        logger.info("[runtime] ainvoke complete — last message: %r", last_content)
        return result

    def shutdown(self) -> None:
        logger.info("[runtime] shutting down")
        self.registry.shutdown()
