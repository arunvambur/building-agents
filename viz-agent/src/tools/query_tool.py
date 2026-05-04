
from core.plugin.interfaces import ToolPlugin


class QueryTools(ToolPlugin):
    name = "data_intelligent_query_agent"

    def get_tools(self):
        #hotel_db_toolkit_tools = get_hotel_info_store().get_tools()
        return [] # hotel_db_toolkit_tools + [check_bnb_availability]
