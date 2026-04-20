
from langchain_chroma import Chroma
from runtime.core.interfaces import ToolPlugin
from runtime.tools.vector_store import search_travel_info
from runtime.tools.weather_service import weather_forecast




class TravelTools(ToolPlugin):
    name = "travel_info_agent"

    def get_tools(self):
        return [search_travel_info, weather_forecast]