from runtime.core.interfaces import RouterPlugin
from runtime.core.registry import PluginRegistry



class AgentRuntime:

    def __init__(self, registry, llm, router, guardrail=None, checkpointer=None):
        self.registry = registry
        self.llm = llm
        self.router = router
        self.guardrail = guardrail
        self.checkpointer = checkpointer
        self.compiled_agents = {}

    def get_agent(self, name):
        if name not in self.compiled_agents:
            plugin = self.registry.agents[name]
            tools = self.registry.get_tools(name)

            self.compiled_agents[name] = plugin.build_graph(
                self.llm,
                tools,
                self.checkpointer
            )

        return self.compiled_agents[name]

    def invoke(self, state, config=None):

        if self.guardrail:
            allowed, msg = self.guardrail.validate(state)
            if not allowed:
                return {"messages": [{"content": msg}]}

        agent_name = self.router.route(state)
        agent = self.get_agent(agent_name)
        return agent.invoke(state, config=config)