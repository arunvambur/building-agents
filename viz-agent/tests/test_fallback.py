"""
Tests for agents/supervisor/fallback.py — spec inference and record extraction.
"""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agents.supervisor.fallback import (
    build_fallback_spec,
    extract_latest_records,
    has_renderer_output,
    is_visualization_request,
    latest_human_text,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_HOTEL_ROWS = [
    {"hotel_name": "St Ives Bay Resort", "town": "St Ives", "rating": 4.8,
     "available_rooms": 12, "price_single": 95.0, "price_double": 140.0},
    {"hotel_name": "Seaview Hotel", "town": "Newquay", "rating": 4.5,
     "available_rooms": 5, "price_single": 80.0, "price_double": 120.0},
]

# ---------------------------------------------------------------------------
# is_visualization_request
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Show me a bar chart",
    "Generate an Excel report",
    "Show me a histogram of hotel ratings",
    "Create a heatmap of hotel ratings",
    "Create a bubble visualization",
    "Plot hotel ratings",
    "Create a dashboard",
    "Export to xlsx",
    "Visualize the data",
])
def test_is_visualization_request_positive(text):
    assert is_visualization_request(text) is True


@pytest.mark.parametrize("text", [
    "What is the capital of France?",
    "Tell me a joke",
    "",
])
def test_is_visualization_request_negative(text):
    assert is_visualization_request(text) is False


# ---------------------------------------------------------------------------
# has_renderer_output
# ---------------------------------------------------------------------------

def test_has_renderer_output_image():
    assert has_renderer_output("data:image/png;base64,abc123") is True


def test_has_renderer_output_file():
    assert has_renderer_output("file:///tmp/report.xlsx") is True


def test_has_renderer_output_plain_text():
    assert has_renderer_output("Here are the hotels...") is False


def test_has_renderer_output_none():
    assert has_renderer_output(None) is False


# ---------------------------------------------------------------------------
# latest_human_text
# ---------------------------------------------------------------------------

def test_latest_human_text_returns_last_human():
    messages = [
        HumanMessage(content="first"),
        AIMessage(content="response"),
        HumanMessage(content="second"),
    ]
    assert latest_human_text(messages) == "second"


def test_latest_human_text_no_human_returns_empty():
    messages = [AIMessage(content="response")]
    assert latest_human_text(messages) == ""


# ---------------------------------------------------------------------------
# extract_latest_records
# ---------------------------------------------------------------------------

def test_extract_latest_records_from_tool_message():
    messages = [
        HumanMessage(content="show chart"),
        ToolMessage(content=json.dumps(_HOTEL_ROWS), name="list_all", tool_call_id="tc-1"),
    ]
    records = extract_latest_records(messages)
    assert records == _HOTEL_ROWS


def test_extract_latest_records_from_nested_json():
    payload = {"data": _HOTEL_ROWS}
    messages = [
        ToolMessage(content=json.dumps(payload), name="query", tool_call_id="tc-1"),
    ]
    records = extract_latest_records(messages)
    assert records == _HOTEL_ROWS


def test_extract_latest_records_skips_renderer_output():
    messages = [
        ToolMessage(content="data:image/png;base64,abc", name="render", tool_call_id="tc-1"),
    ]
    assert extract_latest_records(messages) == []


def test_extract_latest_records_empty_messages():
    assert extract_latest_records([]) == []


def test_extract_latest_records_invalid_json():
    messages = [ToolMessage(content="not json", name="q", tool_call_id="tc-1")]
    assert extract_latest_records(messages) == []


# ---------------------------------------------------------------------------
# build_fallback_spec — chart type inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected_type", [
    ("Show me a bar chart of ratings by town", "bar"),
    ("Create a horizontal bar chart of prices by town", "horizontal_bar"),
    ("Plot a line chart of prices over time", "line"),
    ("Show a pie chart of room distribution", "pie"),
    ("Show me a donut chart of hotel count by town", "donut"),
    ("Show me a histogram of hotel ratings", "histogram"),
    ("Create a heatmap of hotel ratings by town and hotel name", "heatmap"),
    ("Create a grouped bar chart comparing prices by town", "grouped_bar"),
    ("Create a stacked bar chart comparing prices by town", "stacked_bar"),
    ("Create a bubble chart of price and rating", "bubble"),
    ("Create a gauge chart showing average hotel rating", "gauge"),
    ("Create a waterfall chart of prices by town", "waterfall"),
    ("Show an area chart of prices by town", "area"),
    ("Scatter plot of price vs rating", "scatter"),
    ("Show the trend of ratings", "line"),
])
def test_build_fallback_spec_chart_type(text, expected_type):
    spec = build_fallback_spec(text, _HOTEL_ROWS)
    assert spec.charts[0].type == expected_type


# ---------------------------------------------------------------------------
# build_fallback_spec — field inference
# ---------------------------------------------------------------------------

def test_infers_x_field_town_from_keyword():
    spec = build_fallback_spec("bar chart by town", _HOTEL_ROWS)
    assert spec.charts[0].x.field == "town"


def test_infers_x_field_hotel_name_from_keyword():
    spec = build_fallback_spec("bar chart by hotel name", _HOTEL_ROWS)
    assert spec.charts[0].x.field == "hotel_name"


def test_infers_x_field_market_segment_from_keyword():
    spec = build_fallback_spec("bar chart of revenue by market segment", _HOTEL_ROWS)
    assert spec.charts[0].x.field == "market_segment"


def test_infers_y_field_rating():
    spec = build_fallback_spec("show ratings by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "rating"


def test_infers_y_field_available_rooms():
    spec = build_fallback_spec("show available rooms by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "available_rooms"


def test_infers_y_field_price_double():
    spec = build_fallback_spec("show double room prices by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "price_double"


def test_infers_y_field_price_single_for_single_room_price():
    spec = build_fallback_spec("show average single room price by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "price_single"


def test_infers_y_field_price_single_for_price_keyword():
    spec = build_fallback_spec("show prices by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "price_single"


@pytest.mark.parametrize("text,expected_field", [
    ("show occupancy by town", "occupancy_rate"),
    ("show cancellation rate by town", "cancellation_rate"),
    ("show monthly revenue by market segment", "monthly_revenue"),
    ("show review count by town", "review_count"),
    ("show repeat guest rate by town", "repeat_guest_rate"),
    ("show beach distance by town", "distance_beach_km"),
    ("show family score by town", "family_score"),
    ("show sustainability score by town", "sustainability_score"),
    ("show parking spaces by town", "parking_spaces"),
])
def test_infers_enriched_metric_fields(text, expected_field):
    spec = build_fallback_spec(text, _HOTEL_ROWS)
    assert spec.charts[0].y.field == expected_field


def test_grouped_bar_infers_second_price_measure():
    spec = build_fallback_spec(
        "Create a grouped bar chart comparing single room price and double room price by town",
        _HOTEL_ROWS,
    )
    chart = spec.charts[0]
    assert chart.type == "grouped_bar"
    assert chart.y.field == "price_single"
    assert chart.y2 is not None
    assert chart.y2.field == "price_double"


def test_scatter_uses_metric_order_for_versus_prompt():
    spec = build_fallback_spec(
        "scatter plot of occupancy rate versus monthly revenue",
        _HOTEL_ROWS,
    )
    chart = spec.charts[0]
    assert chart.x.field == "occupancy_rate"
    assert chart.y.field == "monthly_revenue"


def test_stacked_bar_infers_second_price_measure():
    spec = build_fallback_spec(
        "Create a stacked bar chart comparing single room price and double room price by town",
        _HOTEL_ROWS,
    )
    chart = spec.charts[0]
    assert chart.type == "stacked_bar"
    assert chart.y.field == "price_single"
    assert chart.y2 is not None
    assert chart.y2.field == "price_double"


# ---------------------------------------------------------------------------
# build_fallback_spec — aggregation inference
# ---------------------------------------------------------------------------

def test_aggregation_count_for_count_keyword():
    spec = build_fallback_spec("count hotels by town", _HOTEL_ROWS)
    assert spec.charts[0].aggregation.op == "count"


def test_aggregation_sum_for_available_rooms():
    spec = build_fallback_spec("show available rooms by town", _HOTEL_ROWS)
    assert spec.charts[0].aggregation.op == "sum"


def test_aggregation_avg_default():
    spec = build_fallback_spec("show ratings by town", _HOTEL_ROWS)
    assert spec.charts[0].aggregation.op == "avg"


# ---------------------------------------------------------------------------
# build_fallback_spec — output format
# ---------------------------------------------------------------------------

def test_output_excel_for_excel_keyword():
    spec = build_fallback_spec("generate an Excel report", _HOTEL_ROWS)
    assert spec.output == "excel"


def test_output_pdf_for_pdf_keyword():
    spec = build_fallback_spec("create a PDF report", _HOTEL_ROWS)
    assert spec.output == "pdf"


def test_output_ppt_for_powerpoint_keyword():
    spec = build_fallback_spec("make a PowerPoint presentation", _HOTEL_ROWS)
    assert spec.output == "ppt"


def test_output_image_by_default():
    spec = build_fallback_spec("show a bar chart", _HOTEL_ROWS)
    assert spec.output == "image"


def test_builds_multiple_charts_from_report_prompt():
    spec = build_fallback_spec(
        "Create a PDF report of Cornwall hotels with three charts: "
        "average rating by town as a bar chart, "
        "average single room price by town as a horizontal bar chart, "
        "and hotel count by town as a donut chart.",
        _HOTEL_ROWS,
    )

    assert spec.output == "pdf"
    assert spec.layout == "grid"
    assert [chart.type for chart in spec.charts] == ["bar", "horizontal_bar", "donut"]
    assert [chart.y.field for chart in spec.charts] == ["rating", "price_single", "hotel_id"]
    assert spec.charts[2].aggregation.op == "count"


# ---------------------------------------------------------------------------
# build_fallback_spec — title generation
# ---------------------------------------------------------------------------

def test_title_is_generated():
    spec = build_fallback_spec("show ratings by town", _HOTEL_ROWS)
    title = spec.charts[0].title
    assert title  # non-empty
    assert "Rating" in title or "rating" in title.lower()


# ---------------------------------------------------------------------------
# build_fallback_spec — x and y fields never the same
# ---------------------------------------------------------------------------

def test_x_and_y_fields_are_different():
    spec = build_fallback_spec("show town by town", _HOTEL_ROWS)
    chart = spec.charts[0]
    assert chart.x.field != chart.y.field
