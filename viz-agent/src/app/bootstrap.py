from agents.data_agent.plugin import DataAgentPlugin
from agents.supervisor.graph import build_supervisor_graph
from agents.viz_agent.plugin import VizAgentPlugin
from core.plugin.guardrail import VizGuardrailPlugin
from core.plugin.registry import PluginRegistry
from core.plugin.runtime import AgentRuntime
from core.renderer.excel.excel import ExcelRenderer
from core.renderer.registry import RendererRegistry
from core.renderer.tableau.tableau import TableauRenderer
from infra.checkpointer import build_checkpointer
from infra.llm_models import get_llm
from tools.query_tool import QueryTools
from tools.rendering_tool import RenderingTools


def build_runtime() -> AgentRuntime:

    llm = get_llm()
    checkpointer = build_checkpointer()

    # --- Renderer registry ---
    renderer_registry = RendererRegistry()
    renderer_registry.register(TableauRenderer())
    renderer_registry.register(ExcelRenderer())

    # --- Plugin registry ---
    registry = PluginRegistry()

    registry.register_agent(
        DataAgentPlugin(),
        tool_plugins=[QueryTools()],
    )
    registry.register_agent(
        VizAgentPlugin(),
        tool_plugins=[RenderingTools(renderer_registry)],
    )

    # --- Build sub-agent graphs ---
    data_agent_graph = registry.get_agent("data_agent").build_graph(
        llm,
        registry.get_tools("data_agent"),
    )
    viz_agent_graph = registry.get_agent("viz_agent").build_graph(
        llm,
        registry.get_tools("viz_agent"),
    )

    # --- Supervisor graph (sequences data_agent → viz_agent) ---
    supervisor_graph = build_supervisor_graph(
        llm,
        data_agent_graph,
        viz_agent_graph,
        checkpointer=checkpointer,
    )

    # --- Guardrail ---
    guardrail = VizGuardrailPlugin(llm)

    return AgentRuntime(
        registry=registry,
        llm=llm,
        router=None,
        guardrail=guardrail,
        checkpointer=checkpointer,
        supervisor=supervisor_graph,
    )
