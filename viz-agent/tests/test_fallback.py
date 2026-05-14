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
    ("Plot a line chart of prices over time", "line"),
    ("Show a pie chart of room distribution", "pie"),
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


def test_infers_y_field_rating():
    spec = build_fallback_spec("show ratings by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "rating"


def test_infers_y_field_available_rooms():
    spec = build_fallback_spec("show available rooms by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "available_rooms"


def test_infers_y_field_price_double():
    # "double" without "room" triggers price_double; "room" takes priority over "double"
    spec = build_fallback_spec("show double prices by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "price_double"



def test_infers_y_field_price_single_for_price_keyword():
    spec = build_fallback_spec("show prices by town", _HOTEL_ROWS)
    assert spec.charts[0].y.field == "price_single"


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


def test_output_image_by_default():
    spec = build_fallback_spec("show a bar chart", _HOTEL_ROWS)
    assert spec.output == "image"


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
