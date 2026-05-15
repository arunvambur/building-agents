import os
import sqlite3
from typing import Optional

from langchain_core.tools import tool

from core.plugin.interfaces import ToolPlugin

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "hotel_db", "cornwall_hotels.db")
)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── original tools ────────────────────────────────────────────────────────

@tool
def search_hotels(town: Optional[str] = None, min_rating: Optional[float] = None) -> list[dict]:
    """
    Search hotels in Cornwall, optionally filtered by town and/or minimum rating.
    Args:
        town: Name of the town (e.g. 'St Ives', 'Newquay'). Optional.
        min_rating: Minimum star rating (e.g. 4.0). Optional.
    Returns:
        List of hotels with hotel_id, hotel_name, town, address, rating, description.
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
        return [dict(r) for r in conn.execute(query, params).fetchall()]


@tool
def get_room_offers(hotel_id: int) -> dict:
    """
    Get room availability and pricing for a specific hotel.
    Args:
        hotel_id: The ID of the hotel.
    Returns:
        Dict with hotel_name, available_rooms, price_single, price_double.
    """
    query = """
        SELECT h.hotel_name, o.available_rooms, o.price_single, o.price_double
        FROM hotel_room_offers o JOIN hotels h ON h.hotel_id = o.hotel_id
        WHERE o.hotel_id = ?
    """
    with _get_connection() as conn:
        row = conn.execute(query, [hotel_id]).fetchone()
    return dict(row) if row else {"error": f"No room offers found for hotel_id={hotel_id}"}


@tool
def list_all_hotels_with_offers() -> list[dict]:
    """
    Returns all hotels joined with their room offers and performance metrics.
    Useful for building overview charts and dashboards.
    Returns:
        List of dicts with hotel_name, town, rating, available_rooms,
        price_single, price_double, market_segment, star_category,
        occupancy_rate, monthly_revenue.
    """
    query = """
        SELECT h.hotel_name, h.town, h.rating,
               o.available_rooms, o.price_single, o.price_double,
               m.market_segment, m.star_category,
               m.occupancy_rate, m.monthly_revenue
        FROM hotels h
        JOIN hotel_room_offers o ON h.hotel_id = o.hotel_id
        JOIN hotel_performance_metrics m ON h.hotel_id = m.hotel_id
        ORDER BY h.rating DESC
    """
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


@tool
def get_hotels_by_price(
    max_single: Optional[float] = None, max_double: Optional[float] = None
) -> list[dict]:
    """
    Find hotels filtered by maximum room price.
    Args:
        max_single: Maximum price for a single room. Optional.
        max_double: Maximum price for a double room. Optional.
    Returns:
        List of hotels with pricing within the given budget.
    """
    query = """
        SELECT h.hotel_name, h.town, h.rating,
               o.available_rooms, o.price_single, o.price_double
        FROM hotels h JOIN hotel_room_offers o ON h.hotel_id = o.hotel_id
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
        return [dict(r) for r in conn.execute(query, params).fetchall()]


# ── performance & analytics tools ────────────────────────────────────────

@tool
def get_performance_metrics(
    market_segment: Optional[str] = None,
    star_category: Optional[str] = None,
    min_occupancy: Optional[float] = None,
) -> list[dict]:
    """
    Query hotel performance metrics with optional filters.
    Args:
        market_segment: e.g. 'Luxury', 'Family', 'Business', 'Leisure', 'Adventure', 'Foodie'. Optional.
        star_category: e.g. 'Luxury', 'Upscale', 'Boutique', 'Midscale', 'Resort'. Optional.
        min_occupancy: Minimum occupancy rate (0.0–1.0). Optional.
    Returns:
        List of hotels with full performance metrics joined with hotel name and town.
    """
    query = """
        SELECT h.hotel_name, h.town, h.rating,
               m.market_segment, m.star_category, m.peak_season,
               m.occupancy_rate, m.cancellation_rate, m.avg_length_of_stay,
               m.monthly_revenue, m.review_count, m.repeat_guest_rate,
               m.distance_beach_km, m.family_score, m.business_score,
               m.sustainability_score, m.spa_available, m.pet_friendly,
               m.parking_spaces
        FROM hotel_performance_metrics m
        JOIN hotels h ON h.hotel_id = m.hotel_id
        WHERE 1=1
    """
    params: list = []
    if market_segment:
        query += " AND LOWER(m.market_segment) = LOWER(?)"
        params.append(market_segment)
    if star_category:
        query += " AND LOWER(m.star_category) = LOWER(?)"
        params.append(star_category)
    if min_occupancy is not None:
        query += " AND m.occupancy_rate >= ?"
        params.append(min_occupancy)
    query += " ORDER BY m.monthly_revenue DESC"
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


@tool
def get_seasonal_pricing(
    hotel_id: Optional[int] = None,
    room_type: Optional[str] = None,
    season: Optional[str] = None,
) -> list[dict]:
    """
    Query seasonal room pricing across hotels.
    Args:
        hotel_id: Filter by specific hotel. Optional.
        room_type: 'Single', 'Double', 'Suite', or 'Family'. Optional.
        season: 'Spring', 'Summer', 'Autumn', or 'Winter'. Optional.
    Returns:
        List of pricing records with hotel_name, room_type, season, price_per_night, min_stay_nights.
    """
    query = """
        SELECT h.hotel_name, h.town, sp.room_type, sp.season,
               sp.price_per_night, sp.min_stay_nights
        FROM seasonal_pricing sp
        JOIN hotels h ON h.hotel_id = sp.hotel_id
        WHERE 1=1
    """
    params: list = []
    if hotel_id is not None:
        query += " AND sp.hotel_id = ?"
        params.append(hotel_id)
    if room_type:
        query += " AND LOWER(sp.room_type) = LOWER(?)"
        params.append(room_type)
    if season:
        query += " AND LOWER(sp.season) = LOWER(?)"
        params.append(season)
    query += " ORDER BY h.hotel_name, sp.room_type, sp.season"
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


@tool
def get_bookings(
    hotel_id: Optional[int] = None,
    booking_channel: Optional[str] = None,
    guest_nationality: Optional[str] = None,
    room_type: Optional[str] = None,
    month: Optional[int] = None,
    is_cancelled: Optional[int] = None,
) -> list[dict]:
    """
    Query booking records with flexible filters.
    Args:
        hotel_id: Filter by hotel. Optional.
        booking_channel: 'Direct', 'OTA', 'Travel Agent', or 'Corporate'. Optional.
        guest_nationality: e.g. 'UK', 'Germany', 'France'. Optional.
        room_type: 'Single', 'Double', 'Suite', or 'Family'. Optional.
        month: Month number 1–12 to filter check-in month. Optional.
        is_cancelled: 0 for confirmed, 1 for cancelled. Optional.
    Returns:
        List of booking records with hotel_name, room_type, dates, channel,
        nationality, revenue, nights, and cancellation status.
    """
    query = """
        SELECT h.hotel_name, h.town, b.room_type,
               b.check_in_date, b.check_out_date, b.nights, b.guests,
               b.booking_channel, b.guest_nationality,
               b.room_revenue, b.extras_revenue,
               (b.room_revenue + b.extras_revenue) AS total_revenue,
               b.is_cancelled, b.lead_time_days
        FROM bookings b
        JOIN hotels h ON h.hotel_id = b.hotel_id
        WHERE 1=1
    """
    params: list = []
    if hotel_id is not None:
        query += " AND b.hotel_id = ?"
        params.append(hotel_id)
    if booking_channel:
        query += " AND LOWER(b.booking_channel) = LOWER(?)"
        params.append(booking_channel)
    if guest_nationality:
        query += " AND LOWER(b.guest_nationality) = LOWER(?)"
        params.append(guest_nationality)
    if room_type:
        query += " AND LOWER(b.room_type) = LOWER(?)"
        params.append(room_type)
    if month is not None:
        query += " AND CAST(strftime('%m', b.check_in_date) AS INTEGER) = ?"
        params.append(month)
    if is_cancelled is not None:
        query += " AND b.is_cancelled = ?"
        params.append(is_cancelled)
    query += " ORDER BY b.check_in_date"
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


@tool
def get_booking_revenue_by_month() -> list[dict]:
    """
    Returns total room revenue, extras revenue, and booking count grouped by month.
    Useful for time-series charts showing revenue trends across 2024.
    Returns:
        List of monthly aggregates: month, month_name, total_revenue,
        room_revenue, extras_revenue, booking_count, cancelled_count.
    """
    query = """
        SELECT
            CAST(strftime('%m', check_in_date) AS INTEGER) AS month,
            CASE strftime('%m', check_in_date)
                WHEN '01' THEN 'January'  WHEN '02' THEN 'February'
                WHEN '03' THEN 'March'    WHEN '04' THEN 'April'
                WHEN '05' THEN 'May'      WHEN '06' THEN 'June'
                WHEN '07' THEN 'July'     WHEN '08' THEN 'August'
                WHEN '09' THEN 'September'WHEN '10' THEN 'October'
                WHEN '11' THEN 'November' WHEN '12' THEN 'December'
            END AS month_name,
            ROUND(SUM(room_revenue + extras_revenue), 2) AS total_revenue,
            ROUND(SUM(room_revenue), 2)   AS room_revenue,
            ROUND(SUM(extras_revenue), 2) AS extras_revenue,
            COUNT(*) AS booking_count,
            SUM(is_cancelled) AS cancelled_count
        FROM bookings
        GROUP BY month
        ORDER BY month
    """
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


@tool
def get_booking_revenue_by_channel() -> list[dict]:
    """
    Returns total revenue and booking count grouped by booking channel.
    Useful for comparing Direct vs OTA vs Travel Agent vs Corporate performance.
    Returns:
        List with booking_channel, total_revenue, booking_count,
        avg_revenue_per_booking, cancellation_rate.
    """
    query = """
        SELECT
            booking_channel,
            ROUND(SUM(room_revenue + extras_revenue), 2) AS total_revenue,
            COUNT(*) AS booking_count,
            ROUND(AVG(room_revenue + extras_revenue), 2) AS avg_revenue_per_booking,
            ROUND(AVG(is_cancelled) * 100, 1) AS cancellation_rate_pct
        FROM bookings
        GROUP BY booking_channel
        ORDER BY total_revenue DESC
    """
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


@tool
def get_reviews(
    hotel_id: Optional[int] = None,
    reviewer_type: Optional[str] = None,
    nationality: Optional[str] = None,
    min_score: Optional[float] = None,
) -> list[dict]:
    """
    Query guest reviews with optional filters.
    Args:
        hotel_id: Filter by hotel. Optional.
        reviewer_type: 'Solo', 'Couple', 'Family', or 'Business'. Optional.
        nationality: e.g. 'UK', 'Germany'. Optional.
        min_score: Minimum overall score. Optional.
    Returns:
        List of reviews with hotel_name, date, all category scores,
        reviewer_type, and nationality.
    """
    query = """
        SELECT h.hotel_name, h.town, r.review_date,
               r.overall_score, r.cleanliness, r.service,
               r.location, r.value_for_money, r.food_score,
               r.reviewer_type, r.nationality
        FROM reviews r
        JOIN hotels h ON h.hotel_id = r.hotel_id
        WHERE 1=1
    """
    params: list = []
    if hotel_id is not None:
        query += " AND r.hotel_id = ?"
        params.append(hotel_id)
    if reviewer_type:
        query += " AND LOWER(r.reviewer_type) = LOWER(?)"
        params.append(reviewer_type)
    if nationality:
        query += " AND LOWER(r.nationality) = LOWER(?)"
        params.append(nationality)
    if min_score is not None:
        query += " AND r.overall_score >= ?"
        params.append(min_score)
    query += " ORDER BY r.review_date"
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


@tool
def get_review_category_averages() -> list[dict]:
    """
    Returns average scores per review category grouped by hotel.
    Useful for radar/heatmap charts comparing hotels across cleanliness,
    service, location, value, and food.
    Returns:
        List with hotel_name, town, avg_overall, avg_cleanliness, avg_service,
        avg_location, avg_value, avg_food, review_count.
    """
    query = """
        SELECT h.hotel_name, h.town,
               ROUND(AVG(r.overall_score), 2)   AS avg_overall,
               ROUND(AVG(r.cleanliness), 2)      AS avg_cleanliness,
               ROUND(AVG(r.service), 2)          AS avg_service,
               ROUND(AVG(r.location), 2)         AS avg_location,
               ROUND(AVG(r.value_for_money), 2)  AS avg_value,
               ROUND(AVG(r.food_score), 2)       AS avg_food,
               COUNT(*) AS review_count
        FROM reviews r
        JOIN hotels h ON h.hotel_id = r.hotel_id
        GROUP BY r.hotel_id
        ORDER BY avg_overall DESC
    """
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


@tool
def get_room_type_summary() -> list[dict]:
    """
    Returns room inventory summary per hotel including total capacity,
    room mix, and sea view availability.
    Returns:
        List with hotel_name, town, room_type, total_rooms,
        floor_area_sqm, max_occupancy, has_sea_view.
    """
    query = """
        SELECT h.hotel_name, h.town, rt.room_type,
               rt.total_rooms, rt.floor_area_sqm,
               rt.max_occupancy, rt.has_sea_view
        FROM room_types rt
        JOIN hotels h ON h.hotel_id = rt.hotel_id
        ORDER BY h.hotel_name, rt.room_type
    """
    with _get_connection() as conn:
        return [dict(r) for r in conn.execute(query).fetchall()]


# ── plugin ────────────────────────────────────────────────────────────────

class QueryTools(ToolPlugin):
    """
    Tool plugin for the data_agent.
    Provides SQLite-backed tools for querying the Cornwall hotels database.
    """

    name = "query_tools"

    def get_tools(self) -> list:
        return [
            # Core
            search_hotels,
            get_room_offers,
            list_all_hotels_with_offers,
            get_hotels_by_price,
            # Performance & analytics
            get_performance_metrics,
            get_seasonal_pricing,
            get_bookings,
            get_booking_revenue_by_month,
            get_booking_revenue_by_channel,
            get_reviews,
            get_review_category_averages,
            get_room_type_summary,
        ]
