from core.plugin.interfaces import AgentPlugin, ToolPlugin


class PluginRegistry:
    """
    Holds registered agent and tool plugins.
    Tools are bound to agents explicitly at registration time,
    not looked up by name at runtime.
    """

    def __init__(self):
        self._agents: dict[str, AgentPlugin] = {}
        self._agent_tools: dict[str, list] = {}
        self._tool_plugins: dict[str, ToolPlugin] = {}

    def register_agent(self, plugin: AgentPlugin, tool_plugins: list[ToolPlugin] = None) -> None:
        """Register an agent plugin with its associated tool plugins."""
        plugin.initialize()
        self._agents[plugin.name] = plugin

        tools = []
        for tp in (tool_plugins or []):
            tp.initialize()
            self._tool_plugins[tp.name] = tp
            tools.extend(tp.get_tools())

        self._agent_tools[plugin.name] = tools

    def get_agent(self, name: str) -> AgentPlugin:
        if name not in self._agents:
            raise KeyError(f"No agent registered with name '{name}'.")
        return self._agents[name]

    def get_tools(self, agent_name: str) -> list:
        return self._agent_tools.get(agent_name, [])

    @property
    def agent_names(self) -> list[str]:
        return list(self._agents.keys())

    def shutdown(self) -> None:
        for plugin in self._agents.values():
            plugin.shutdown()
        for plugin in self._tool_plugins.values():
            plugin.shutdown()
