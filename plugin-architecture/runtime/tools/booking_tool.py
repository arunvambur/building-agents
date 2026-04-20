


from runtime.core.interfaces import ToolPlugin
from runtime.tools.bnb_service import check_bnb_availability
from runtime.tools.hotel_store import get_hotel_info_store


class BookingTools(ToolPlugin):
    name = "accommodation_booking_agent"

    def get_tools(self):
        hotel_db_toolkit_tools = get_hotel_info_store().get_tools()
        return hotel_db_toolkit_tools + [check_bnb_availability]
