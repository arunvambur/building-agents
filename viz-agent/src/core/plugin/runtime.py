import asyncio
import logging
import os
from typing import Any, Optional

from core.plugin.interfaces import GuardrailPlugin
from core.plugin.registry import PluginRegistry

logger = logging.getLogger(__name__)

# Maximum seconds to wait for the supervisor graph to complete.
# Covers the full data-agent + viz-agent pipeline including LLM round-trips.
_INVOKE_TIMEOUT_S = float(os.getenv("INVOKE_TIMEOUT_S", "120"))


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

    # ---- guardrail ----

    def _check_guardrail(self, state: dict) -> Optional[dict]:
        """Synchronous guardrail check — used by invoke()."""
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

    async def _async_check_guardrail(self, state: dict) -> Optional[dict]:
        """Async guardrail check — uses avalidate() to avoid blocking the event loop."""
        if not self.guardrail:
            return None
        user_text = state.get("messages", [{}])[-1]
        content = getattr(user_text, "content", "")[:80]
        logger.debug("[guardrail] checking (async): %r", content)
        allowed, message = await self.guardrail.avalidate(state)
        if not allowed:
            logger.warning("[guardrail] BLOCKED: %r", content)
            return {"messages": [message]}
        logger.debug("[guardrail] allowed")
        return None

    # ---- public API ----

    def invoke(self, state: dict, config: Optional[dict] = None) -> dict:
        content = getattr(state.get("messages", [None])[-1], "content", "")[:80]
        logger.info("[runtime] invoke — user: %r", content)
        blocked = self._check_guardrail(state)
        if blocked:
            return blocked
        result = self.supervisor.invoke(state, config=config)
        last = result.get("messages", [None])[-1]
        logger.info("[runtime] invoke complete — last message: %r", getattr(last, "content", "")[:120])
        return result

    async def ainvoke(self, state: dict, config: Optional[dict] = None) -> dict:
        content = getattr(state.get("messages", [None])[-1], "content", "")[:80]
        logger.info("[runtime] ainvoke — user: %r", content)

        blocked = await self._async_check_guardrail(state)
        if blocked:
            return blocked

        try:
            result = await asyncio.wait_for(
                self.supervisor.ainvoke(state, config=config),
                timeout=_INVOKE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.error("[runtime] ainvoke timed out after %.0fs", _INVOKE_TIMEOUT_S)
            raise TimeoutError(
                f"The request timed out after {_INVOKE_TIMEOUT_S:.0f}s. "
                "The pipeline is taking too long — please try again."
            )

        last = result.get("messages", [None])[-1]
        logger.info("[runtime] ainvoke complete — last message: %r", getattr(last, "content", "")[:120])
        return result

    def shutdown(self) -> None:
        logger.info("[runtime] shutting down")
        self.registry.shutdown()
