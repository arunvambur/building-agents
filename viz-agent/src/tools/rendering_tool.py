
from core.plugin.interfaces import ToolPlugin


class TravelTools(ToolPlugin):
    name = "rendering_agent"

    def get_tools(self):
        return []