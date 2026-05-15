import pytest

from tools.query_tool import (
    get_booking_revenue_by_channel,
    get_booking_revenue_by_month,
    get_bookings,
    get_hotels_by_price,
    get_performance_metrics,
    get_review_category_averages,
    get_reviews,
    get_room_offers,
    get_room_type_summary,
    get_seasonal_pricing,
    list_all_hotels_with_offers,
    search_hotels,
)

# ── original tools ────────────────────────────────────────────────────────

def test_search_hotels_returns_all():
    results = search_hotels.invoke({"town": None, "min_rating": None})
    assert len(results) == 10

def test_search_hotels_by_town():
    results = search_hotels.invoke({"town": "St Ives", "min_rating": None})
    assert len(results) == 1
    assert results[0]["hotel_name"] == "St Ives Bay Resort"

def test_search_hotels_by_min_rating():
    results = search_hotels.invoke({"town": None, "min_rating": 4.5})
    assert all(r["rating"] >= 4.5 for r in results)

def test_search_hotels_case_insensitive():
    results = search_hotels.invoke({"town": "newquay", "min_rating": None})
    assert len(results) == 1
    assert results[0]["town"] == "Newquay"

def test_get_room_offers_valid():
    result = get_room_offers.invoke({"hotel_id": 1})
    assert "hotel_name" in result
    assert "price_single" in result

def test_get_room_offers_invalid():
    result = get_room_offers.invoke({"hotel_id": 9999})
    assert "error" in result

def test_list_all_hotels_with_offers():
    results = list_all_hotels_with_offers.invoke({})
    assert len(results) == 10
    assert "market_segment" in results[0]
    assert "occupancy_rate" in results[0]

def test_get_hotels_by_price_single():
    results = get_hotels_by_price.invoke({"max_single": 100.0, "max_double": None})
    assert all(r["price_single"] <= 100.0 for r in results)

def test_get_hotels_by_price_double():
    results = get_hotels_by_price.invoke({"max_single": None, "max_double": 160.0})
    assert all(r["price_double"] <= 160.0 for r in results)

def test_get_hotels_by_price_no_filter():
    results = get_hotels_by_price.invoke({"max_single": None, "max_double": None})
    assert len(results) == 10

# ── performance metrics ───────────────────────────────────────────────────

def test_get_performance_metrics_all():
    results = get_performance_metrics.invoke({"market_segment": None, "star_category": None, "min_occupancy": None})
    assert len(results) == 10
    assert "occupancy_rate" in results[0]
    assert "monthly_revenue" in results[0]

def test_get_performance_metrics_by_segment():
    results = get_performance_metrics.invoke({"market_segment": "Luxury", "star_category": None, "min_occupancy": None})
    assert all(r["market_segment"] == "Luxury" for r in results)
    assert len(results) == 2

def test_get_performance_metrics_by_star_category():
    results = get_performance_metrics.invoke({"market_segment": None, "star_category": "Boutique", "min_occupancy": None})
    assert all(r["star_category"] == "Boutique" for r in results)

def test_get_performance_metrics_by_min_occupancy():
    results = get_performance_metrics.invoke({"market_segment": None, "star_category": None, "min_occupancy": 0.85})
    assert all(r["occupancy_rate"] >= 0.85 for r in results)

# ── seasonal pricing ──────────────────────────────────────────────────────

def test_get_seasonal_pricing_all():
    results = get_seasonal_pricing.invoke({"hotel_id": None, "room_type": None, "season": None})
    assert len(results) == 160  # 10 hotels × 4 room types × 4 seasons

def test_get_seasonal_pricing_by_season():
    results = get_seasonal_pricing.invoke({"hotel_id": None, "room_type": None, "season": "Summer"})
    assert all(r["season"] == "Summer" for r in results)
    assert len(results) == 40  # 10 hotels × 4 room types

def test_get_seasonal_pricing_by_room_type():
    results = get_seasonal_pricing.invoke({"hotel_id": None, "room_type": "Suite", "season": None})
    assert all(r["room_type"] == "Suite" for r in results)
    assert len(results) == 40  # 10 hotels × 4 seasons

def test_get_seasonal_pricing_summer_suites_most_expensive():
    results = get_seasonal_pricing.invoke({"hotel_id": None, "room_type": "Suite", "season": "Summer"})
    winter = get_seasonal_pricing.invoke({"hotel_id": None, "room_type": "Suite", "season": "Winter"})
    avg_summer = sum(r["price_per_night"] for r in results) / len(results)
    avg_winter = sum(r["price_per_night"] for r in winter) / len(winter)
    assert avg_summer > avg_winter

# ── bookings ──────────────────────────────────────────────────────────────

def test_get_bookings_all():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": None, "guest_nationality": None,
                                   "room_type": None, "month": None, "is_cancelled": None})
    assert len(results) == 127

def test_get_bookings_by_channel():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": "Direct",
                                   "guest_nationality": None, "room_type": None,
                                   "month": None, "is_cancelled": None})
    assert all(r["booking_channel"] == "Direct" for r in results)

def test_get_bookings_by_nationality():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": None,
                                   "guest_nationality": "Germany", "room_type": None,
                                   "month": None, "is_cancelled": None})
    assert all(r["guest_nationality"] == "Germany" for r in results)

def test_get_bookings_by_month():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": None,
                                   "guest_nationality": None, "room_type": None,
                                   "month": 7, "is_cancelled": None})
    assert all("2024-07" in r["check_in_date"] for r in results)

def test_get_bookings_cancelled_only():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": None,
                                   "guest_nationality": None, "room_type": None,
                                   "month": None, "is_cancelled": 1})
    assert all(r["is_cancelled"] == 1 for r in results)
    assert len(results) > 0

def test_get_bookings_have_total_revenue():
    results = get_bookings.invoke({"hotel_id": None, "booking_channel": None,
                                   "guest_nationality": None, "room_type": None,
                                   "month": None, "is_cancelled": 0})
    assert all("total_revenue" in r for r in results)
    assert all(r["total_revenue"] >= r["room_revenue"] for r in results)

# ── revenue aggregates ────────────────────────────────────────────────────

def test_get_booking_revenue_by_month_returns_12_months():
    results = get_booking_revenue_by_month.invoke({})
    assert len(results) == 12

def test_get_booking_revenue_by_month_july_highest():
    results = get_booking_revenue_by_month.invoke({})
    by_month = {r["month"]: r["total_revenue"] for r in results}
    assert by_month[7] == max(by_month.values())

def test_get_booking_revenue_by_channel_returns_all_channels():
    results = get_booking_revenue_by_channel.invoke({})
    channels = {r["booking_channel"] for r in results}
    assert {"Direct", "OTA", "Travel Agent", "Corporate"}.issubset(channels)

def test_get_booking_revenue_by_channel_has_cancellation_rate():
    results = get_booking_revenue_by_channel.invoke({})
    assert all("cancellation_rate_pct" in r for r in results)

# ── reviews ───────────────────────────────────────────────────────────────

def test_get_reviews_all():
    results = get_reviews.invoke({"hotel_id": None, "reviewer_type": None,
                                  "nationality": None, "min_score": None})
    assert len(results) == 101

def test_get_reviews_by_reviewer_type():
    results = get_reviews.invoke({"hotel_id": None, "reviewer_type": "Family",
                                  "nationality": None, "min_score": None})
    assert all(r["reviewer_type"] == "Family" for r in results)

def test_get_reviews_by_nationality():
    results = get_reviews.invoke({"hotel_id": None, "reviewer_type": None,
                                  "nationality": "UK", "min_score": None})
    assert all(r["nationality"] == "UK" for r in results)

def test_get_reviews_by_min_score():
    results = get_reviews.invoke({"hotel_id": None, "reviewer_type": None,
                                  "nationality": None, "min_score": 4.8})
    assert all(r["overall_score"] >= 4.8 for r in results)

def test_get_review_category_averages():
    results = get_review_category_averages.invoke({})
    assert len(results) == 10
    assert "avg_cleanliness" in results[0]
    assert "avg_food" in results[0]
    assert "review_count" in results[0]

def test_get_review_category_averages_st_ives_top():
    results = get_review_category_averages.invoke({})
    top = results[0]
    assert top["hotel_name"] == "St Ives Bay Resort"

# ── room types ────────────────────────────────────────────────────────────

def test_get_room_type_summary_returns_40_rows():
    results = get_room_type_summary.invoke({})
    assert len(results) == 40  # 10 hotels × 4 room types

def test_get_room_type_summary_has_sea_view_field():
    results = get_room_type_summary.invoke({})
    assert all("has_sea_view" in r for r in results)

def test_get_room_type_summary_suite_largest():
    results = get_room_type_summary.invoke({})
    suites = [r for r in results if r["room_type"] == "Suite"]
    others = [r for r in results if r["room_type"] != "Suite"]
    avg_suite = sum(r["floor_area_sqm"] for r in suites) / len(suites)
    avg_other = sum(r["floor_area_sqm"] for r in others) / len(others)
    assert avg_suite > avg_other
