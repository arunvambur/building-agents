import pytest

from tools.query_tool import get_hotels_by_price, get_room_offers, list_all_hotels_with_offers, search_hotels


def test_search_hotels_returns_results():
    results = search_hotels.invoke({"town": None, "min_rating": None})
    assert isinstance(results, list)
    assert len(results) == 10  # all 10 hotels in seed data


def test_search_hotels_by_town():
    results = search_hotels.invoke({"town": "St Ives", "min_rating": None})
    assert len(results) == 1
    assert results[0]["hotel_name"] == "St Ives Bay Resort"


def test_search_hotels_by_min_rating():
    results = search_hotels.invoke({"town": None, "min_rating": 4.5})
    assert all(r["rating"] >= 4.5 for r in results)
    assert len(results) > 0


def test_search_hotels_town_case_insensitive():
    results = search_hotels.invoke({"town": "newquay", "min_rating": None})
    assert len(results) == 1
    assert results[0]["town"] == "Newquay"


def test_get_room_offers_valid_hotel():
    result = get_room_offers.invoke({"hotel_id": 1})
    assert "hotel_name" in result
    assert "available_rooms" in result
    assert "price_single" in result
    assert "price_double" in result


def test_get_room_offers_invalid_hotel():
    result = get_room_offers.invoke({"hotel_id": 9999})
    assert "error" in result


def test_list_all_hotels_with_offers():
    results = list_all_hotels_with_offers.invoke({})
    assert len(results) == 10
    assert "hotel_name" in results[0]
    assert "price_single" in results[0]


def test_get_hotels_by_price_single():
    results = get_hotels_by_price.invoke({"max_single": 100.0, "max_double": None})
    assert all(r["price_single"] <= 100.0 for r in results)


def test_get_hotels_by_price_double():
    results = get_hotels_by_price.invoke({"max_single": None, "max_double": 160.0})
    assert all(r["price_double"] <= 160.0 for r in results)


def test_get_hotels_by_price_no_filter():
    results = get_hotels_by_price.invoke({"max_single": None, "max_double": None})
    assert len(results) == 10
