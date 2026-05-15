import re
from typing import Optional

from tools.query_tool import (
    get_booking_revenue_by_channel,
    get_booking_revenue_by_month,
    get_bookings,
    get_hotels_by_price,
    get_performance_metrics,
    get_reviews,
    get_room_type_summary,
    get_seasonal_pricing,
    list_all_hotels_with_offers,
    search_hotels,
)

_TOWNS = [
    "Newquay",
    "Falmouth",
    "St Austell",
    "Penzance",
    "Camborne",
    "Hayle",
    "Land's End",
    "Bude",
    "Padstow",
    "St Ives",
]


def resolve_data_query(user_text: str) -> Optional[list[dict]]:
    """
    Deterministic fallback for common data requests.

    This protects the data path when the LLM emits malformed tool calls or
    describes a tool call as JSON text instead of executing it.
    """
    text = user_text.lower()

    if "review" in text:
        return get_reviews.invoke({
            "hotel_id": None,
            "reviewer_type": _match_choice(text, ["Solo", "Couple", "Family", "Business"]),
            "nationality": _match_choice(text, ["UK", "Germany", "France", "Netherlands", "USA", "Australia"]),
            "min_score": _number_after_threshold(text),
        })

    if "room type" in text or "inventory" in text:
        return get_room_type_summary.invoke({})

    if "seasonal" in text or "price per night" in text:
        return get_seasonal_pricing.invoke({
            "hotel_id": None,
            "room_type": _match_choice(text, ["Single", "Double", "Suite", "Family"]),
            "season": _match_choice(text, ["Spring", "Summer", "Autumn", "Winter"]),
        })

    if "booking revenue by channel" in text or "revenue by channel" in text:
        return get_booking_revenue_by_channel.invoke({})

    if "booking revenue by month" in text or "revenue by month" in text:
        return get_booking_revenue_by_month.invoke({})

    if "booking" in text or "bookings" in text:
        return get_bookings.invoke({
            "hotel_id": None,
            "booking_channel": _match_choice(text, ["Direct", "OTA", "Travel Agent", "Corporate"]),
            "guest_nationality": _match_choice(text, ["UK", "Germany", "France", "Netherlands", "USA", "Australia"]),
            "room_type": _match_choice(text, ["Single", "Double", "Suite", "Family"]),
            "month": _month_number(text),
            "is_cancelled": 1 if "cancelled" in text or "canceled" in text else None,
        })

    if "performance" in text or "occupancy" in text or "monthly revenue" in text:
        return _filter_rows(
            get_performance_metrics.invoke({
                "market_segment": _match_choice(text, ["Luxury", "Family", "Business", "Leisure", "Adventure", "Foodie"]),
                "star_category": _match_choice(text, ["Luxury", "Upscale", "Boutique", "Midscale", "Resort"]),
                "min_occupancy": _percent_after_threshold(text),
            }),
            town=_town(text),
        )

    if "price" in text and ("under" in text or "below" in text or "less than" in text):
        max_price = _number_after_threshold(text)
        return get_hotels_by_price.invoke({"max_single": max_price, "max_double": max_price})

    if "hotel" in text or "room" in text or "available" in text:
        rows = list_all_hotels_with_offers.invoke({})
        rows = _filter_rows(rows, town=_town(text))
        if "available" in text:
            rows = [row for row in rows if row.get("available_rooms", 0) > 0]
        min_rating = _number_after_threshold(text) if "rating" in text else None
        if min_rating is not None:
            rows = [row for row in rows if row.get("rating", 0) >= min_rating]
        return rows

    if "rating" in text:
        return search_hotels.invoke({"town": _town(text), "min_rating": _number_after_threshold(text)})

    return None


def _filter_rows(rows: list[dict], town: Optional[str] = None) -> list[dict]:
    if not town:
        return rows
    return [row for row in rows if str(row.get("town", "")).lower() == town.lower()]


def _town(text: str) -> Optional[str]:
    for town in _TOWNS:
        if town.lower() in text:
            return town
    return None


def _match_choice(text: str, choices: list[str]) -> Optional[str]:
    for choice in choices:
        if choice.lower() in text:
            return choice
    return None


def _number_after_threshold(text: str) -> Optional[float]:
    match = re.search(r"(?:above|over|at least|under|below|less than)\s+(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _percent_after_threshold(text: str) -> Optional[float]:
    value = _number_after_threshold(text)
    if value is None:
        return None
    return value / 100 if value > 1 else value


def _month_number(text: str) -> Optional[int]:
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    for month, number in months.items():
        if month in text:
            return number
    match = re.search(r"\bmonth\s+(\d{1,2})\b", text)
    if not match:
        return None
    number = int(match.group(1))
    return number if 1 <= number <= 12 else None
