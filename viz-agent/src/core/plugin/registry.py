


class PluginRegistry:
    def __init__(self):
        self.agents = {}
        self.tools = {}

    def register_agent(self, plugin):
        plugin.initialize()
        self.agents[plugin.name] = plugin

    def register_tools(self, plugin):
        plugin.initialize()
        self.tools[plugin.name] = plugin

    def get_tools(self, name):
        plugin = self.tools.get(name)
        return plugin.get_tools() if plugin else []

    def shutdown(self):
        for p in self.agents.values():
            p.shutdown()

        for p in self.tools.values():
            p.shutdown()