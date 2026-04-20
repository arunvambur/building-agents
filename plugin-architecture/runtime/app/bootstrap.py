


from runtime.agents.booking_agent.plugin import BookingAgentPlugin
from runtime.agents.travel_agent.plugin import TravelAgentPlugin
from runtime.core.registry import PluginRegistry
from runtime.core.runtime import AgentRuntime
from runtime.infrastructure.llm_models import get_llm
from runtime.router.router import LLMRouter
from runtime.router.schema import AgentTypeOutput
from runtime.tools.booking_tool import BookingTools
from runtime.tools.travel_tool import TravelTools


def build_runtime():

    llm = get_llm()

    registry = PluginRegistry()

    registry.register_agent(TravelAgentPlugin())
    registry.register_agent(BookingAgentPlugin())

    registry.register_tools(TravelTools())
    registry.register_tools(BookingTools())

    router = LLMRouter(
        llm,
        AgentTypeOutput
    )

    return AgentRuntime(
        registry,
        llm,
        router
    )