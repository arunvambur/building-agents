
from runtime.core.interfaces import AgentPlugin, ToolPlugin


class PluginRegistry:
    def __init__(self):
        self.agents = {}
        self.tools = {}

    def register_agent(self, agent: AgentPlugin):
        self.agents[agent.name] = agent

    def register_tools(self, tool_plugin: ToolPlugin):
        self.tools[tool_plugin.name] = tool_plugin.get_tools()

    def get_tools_for_agent(self, agent_name):
        return self.tools.get(agent_name, [])