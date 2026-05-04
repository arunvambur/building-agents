
from agents.data_agent.plugin import DataAgentPlugin
from agents.viz_agent.plugin import VizAgentPlugin
from context.checkpoint import build_checkpointer
from core.plugin.registry import PluginRegistry
from core.plugin.runtime import AgentRuntime
from infra.llm_models import get_llm
from router.router import LLMRouter
from tools.query_tool import QueryTools
from tools.rendering_tool import RenderingTools
from guard.viz_guardrail import VizGuardrailPlugin


def build_runtime():

    llm = get_llm()

    registry = PluginRegistry()

    registry.register_agent(DataAgentPlugin())
    registry.register_agent(VizAgentPlugin())

    registry.register_tools(QueryTools())
    registry.register_tools(RenderingTools())

    router = LLMRouter(llm)

    guardrail = VizGuardrailPlugin(llm)

    checkpointer = build_checkpointer()

    return AgentRuntime(
        registry,
        llm,
        router,
        guardrail=guardrail,
        checkpointer=checkpointer
    )