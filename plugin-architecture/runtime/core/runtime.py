from runtime.core.interfaces import RouterPlugin
from runtime.core.registry import PluginRegistry



class AgentRuntime:

    def __init__(self, registry: PluginRegistry, llm, router: RouterPlugin):
        self.registry = registry
        self.llm = llm
        self.router = router
        self.compiled_agents = {}

    def get_agent(self, agent_name):
        if agent_name not in self.compiled_agents:
            plugin = self.registry.agents[agent_name]
            tools = self.registry.get_tools_for_agent(agent_name)
            self.compiled_agents[agent_name] = plugin.build_graph(self.llm, tools)

        return self.compiled_agents[agent_name]

    def invoke(self, state):
        agent_name = self.router.route(state)
        agent = self.get_agent(agent_name)
        return agent.invoke(state)