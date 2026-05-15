"""
Tests for the supervisor intent classifier.
Covers keyword fast-path and LLM fallback behaviour.
"""
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents.supervisor.intent import (
    IntentOutput,
    IntentType,
    build_intent_classifier,
    classify_intent_fast,
)


# ============================================================
# Fast classifier — no LLM involved
# ============================================================

class TestFastClassifier:

    # --- viz-only (no data keywords) ---

    def test_pure_chart_keyword_is_viz(self):
        assert classify_intent_fast("generate a scatter plot") == IntentType.viz

    def test_pure_excel_keyword_is_viz(self):
        assert classify_intent_fast("export to xlsx") == IntentType.viz

    def test_powerpoint_only_is_viz(self):
        assert classify_intent_fast("make a PowerPoint presentation") == IntentType.viz

    def test_pdf_only_is_viz(self):
        assert classify_intent_fast("create a PDF") == IntentType.viz

    def test_histogram_with_show_is_both(self):
        # "show" matches data pattern, "histogram" matches viz → both
        assert classify_intent_fast("show a histogram") == IntentType.both

    def test_visualize_alone_is_viz(self):
        # "visualize" matches viz; "data" alone is not in the data keyword list
        assert classify_intent_fast("visualize the data") == IntentType.viz

    # --- data-only (no viz keywords) ---

    def test_list_hotels_is_data(self):
        assert classify_intent_fast("list all hotels in Cornwall") == IntentType.data

    def test_find_hotel_is_data(self):
        assert classify_intent_fast("which hotels in St Ives have available rooms?") == IntentType.data

    def test_cheapest_hotel_is_data(self):
        assert classify_intent_fast("what is the cheapest hotel?") == IntentType.data

    def test_price_query_is_data(self):
        assert classify_intent_fast("find hotels with price under 100") == IntentType.data

    def test_rating_query_is_data(self):
        assert classify_intent_fast("find hotels with rating above 4.5") == IntentType.data

    def test_town_query_is_data(self):
        assert classify_intent_fast("hotels in Newquay") == IntentType.data

    def test_availability_query_is_data(self):
        assert classify_intent_fast("which rooms are available?") == IntentType.data

    # --- both (viz + data keywords together) ---

    def test_show_bar_chart_is_both(self):
        # "show" = data keyword, "bar chart" = viz keyword
        assert classify_intent_fast("show me a bar chart of hotel ratings") == IntentType.both

    def test_excel_report_with_hotels_is_both(self):
        # "hotels" = data keyword, "Excel" = viz keyword
        assert classify_intent_fast("generate an Excel report of all hotels") == IntentType.both

    def test_chart_and_list_is_both(self):
        assert classify_intent_fast("list hotels and show a bar chart") == IntentType.both

    def test_find_and_visualize_is_both(self):
        assert classify_intent_fast("find hotels in Newquay and plot their ratings") == IntentType.both

    def test_data_and_excel_is_both(self):
        assert classify_intent_fast("show me hotel data and export to Excel") == IntentType.both

    def test_pie_chart_with_rooms_is_viz(self):
        # "room distribution" — "room" is in data pattern → both
        # actual: "rooms" is in data pattern but "room" alone is not
        assert classify_intent_fast("pie chart of room distribution") == IntentType.viz

    def test_pie_chart_with_rooms_keyword_is_both(self):
        # "rooms" (plural) IS in the data pattern
        assert classify_intent_fast("pie chart of available rooms") == IntentType.both

    # --- ambiguous ---

    def test_ambiguous_returns_none(self):
        assert classify_intent_fast("hello") is None

    def test_greeting_returns_none(self):
        assert classify_intent_fast("good morning") is None

    # --- case insensitivity ---

    def test_case_insensitive_viz(self):
        assert classify_intent_fast("GENERATE A SCATTER PLOT") == IntentType.viz

    def test_case_insensitive_data(self):
        assert classify_intent_fast("LIST ALL HOTELS") == IntentType.data


# ============================================================
# Full classifier with LLM fallback
# ============================================================

def _mock_llm(intent: IntentType) -> Any:
    mock = MagicMock()
    mock.with_structured_output.return_value.invoke.return_value = IntentOutput(
        intent=intent,
        reason="test",
    )
    return mock


class TestBuildIntentClassifier:

    def test_fast_path_skips_llm_for_viz(self):
        mock_llm = _mock_llm(IntentType.data)
        classify = build_intent_classifier(mock_llm)
        result = classify("generate a scatter plot")
        assert result == IntentType.viz
        mock_llm.with_structured_output.return_value.invoke.assert_not_called()

    def test_fast_path_skips_llm_for_data(self):
        mock_llm = _mock_llm(IntentType.viz)
        classify = build_intent_classifier(mock_llm)
        result = classify("list all hotels in Cornwall")
        assert result == IntentType.data
        mock_llm.with_structured_output.return_value.invoke.assert_not_called()

    def test_fast_path_skips_llm_for_both(self):
        mock_llm = _mock_llm(IntentType.data)
        classify = build_intent_classifier(mock_llm)
        result = classify("list hotels and show a bar chart")
        assert result == IntentType.both
        mock_llm.with_structured_output.return_value.invoke.assert_not_called()

    def test_llm_fallback_called_for_ambiguous(self):
        mock_llm = _mock_llm(IntentType.data)
        classify = build_intent_classifier(mock_llm)
        result = classify("hello there")
        assert result == IntentType.data
        mock_llm.with_structured_output.return_value.invoke.assert_called_once()

    def test_llm_fallback_returns_viz(self):
        mock_llm = _mock_llm(IntentType.viz)
        classify = build_intent_classifier(mock_llm)
        result = classify("something unclear")
        assert result == IntentType.viz

    def test_llm_fallback_returns_both(self):
        mock_llm = _mock_llm(IntentType.both)
        classify = build_intent_classifier(mock_llm)
        result = classify("something unclear")
        assert result == IntentType.both


# ============================================================
# IntentType enum
# ============================================================

class TestIntentType:

    def test_values(self):
        assert IntentType.data == "data"
        assert IntentType.viz  == "viz"
        assert IntentType.both == "both"

    def test_from_string(self):
        assert IntentType("data") == IntentType.data
        assert IntentType("viz")  == IntentType.viz
        assert IntentType("both") == IntentType.both
