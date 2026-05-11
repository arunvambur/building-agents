import os
import sqlite3
from typing import Optional

from langchain_core.tools import tool

from core.plugin.interfaces import ToolPlugin

# Resolve DB path relative to the project root (two levels up from src/)
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "hotel_db", "cornwall_hotels.db")
_DB_PATH = os.path.normpath(_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@tool
def search_hotels(town: Optional[str] = None, min_rating: Optional[float] = None) -> list[dict]:
    """
    Search hotels in Cornwall, optionally filtered by town and/or minimum rating.
    Args:
        town: Name of the town to filter by (e.g. 'St Ives', 'Newquay'). Optional.
        min_rating: Minimum star rating (e.g. 4.0). Optional.
    Returns:
        List of matching hotels with hotel_id, hotel_name, town, address, rating, description.
    """
    query = "SELECT hotel_id, hotel_name, town, address, rating, description FROM hotels WHERE 1=1"
    params: list = []

    if town:
        query += " AND LOWER(town) = LOWER(?)"
        params.append(town)

    if min_rating is not None:
        query += " AND rating >= ?"
        params.append(min_rating)

    query += " ORDER BY rating DESC"

    with _get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


@tool
def get_room_offers(hotel_id: int) -> dict:
    """
    Get room availability and pricing for a specific hotel.
    Args:
        hotel_id: The ID of the hotel to look up.
    Returns:
        Dict with hotel name, available_rooms, price_single, price_double.
        Returns an error message if the hotel is not found.
    """
    query = """
        SELECT h.hotel_name, o.available_rooms, o.price_single, o.price_double
        FROM hotel_room_offers o
        JOIN hotels h ON h.hotel_id = o.hotel_id
        WHERE o.hotel_id = ?
    """
    with _get_connection() as conn:
        row = conn.execute(query, [hotel_id]).fetchone()

    if not row:
        return {"error": f"No room offers found for hotel_id={hotel_id}"}

    return dict(row)


@tool
def list_all_hotels_with_offers() -> list[dict]:
    """
    Returns all hotels in Cornwall joined with their room offers.
    Useful for building overview charts and dashboards.
    Returns:
        List of dicts with hotel_name, town, rating, available_rooms, price_single, price_double.
    """
    query = """
        SELECT h.hotel_name, h.town, h.rating, o.available_rooms, o.price_single, o.price_double
        FROM hotels h
        JOIN hotel_room_offers o ON h.hotel_id = o.hotel_id
        ORDER BY h.rating DESC
    """
    with _get_connection() as conn:
        rows = conn.execute(query).fetchall()

    return [dict(row) for row in rows]


@tool
def get_hotels_by_price(max_single: Optional[float] = None, max_double: Optional[float] = None) -> list[dict]:
    """
    Find hotels filtered by maximum room price.
    Args:
        max_single: Maximum price for a single room. Optional.
        max_double: Maximum price for a double room. Optional.
    Returns:
        List of hotels with pricing that fits within the given budget.
    """
    query = """
        SELECT h.hotel_name, h.town, h.rating, o.available_rooms, o.price_single, o.price_double
        FROM hotels h
        JOIN hotel_room_offers o ON h.hotel_id = o.hotel_id
        WHERE 1=1
    """
    params: list = []

    if max_single is not None:
        query += " AND o.price_single <= ?"
        params.append(max_single)

    if max_double is not None:
        query += " AND o.price_double <= ?"
        params.append(max_double)

    query += " ORDER BY o.price_single ASC"

    with _get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


class QueryTools(ToolPlugin):
    """
    Tool plugin for the data_agent.
    Provides SQLite-backed tools for querying the Cornwall hotels database.
    """

    name = "query_tools"

    def get_tools(self) -> list:
        return [
            search_hotels,
            get_room_offers,
            list_all_hotels_with_offers,
            get_hotels_by_price,
        ]
