"""
Tests for the data formatting helpers in agents/supervisor/formatting.py.
Verifies table://, csv://, and plain-text responses are produced correctly.
No LangGraph dependency — imports only from the pure formatting module.
"""
import json
import os

import pytest

from agents.supervisor.formatting import (
    extract_records_from_tool_messages,
    format_table,
    get_user_text,
    last_ai_content,
    parse_json_records,
    wants_csv,
    write_csv,
)

# ---- shared fixtures ----

SAMPLE_RECORDS = [
    {"hotel_name": "St Ives Bay Resort", "town": "St Ives",  "rating": "4.8"},
    {"hotel_name": "Harbour Inn",        "town": "Falmouth", "rating": "4.2"},
    {"hotel_name": "Seaview Hotel",      "town": "Newquay",  "rating": "4.5"},
]


# ============================================================
# parse_json_records
# ============================================================

def test_parse_json_list_of_dicts():
    result = parse_json_records(json.dumps(SAMPLE_RECORDS))
    assert result == SAMPLE_RECORDS


def test_parse_json_single_dict():
    result = parse_json_records(json.dumps({"hotel_name": "Harbour Inn", "rating": "4.2"}))
    assert result == [{"hotel_name": "Harbour Inn", "rating": "4.2"}]


def test_parse_json_error_dict_returns_string():
    result = parse_json_records(json.dumps({"error": "not found"}))
    assert isinstance(result, str)
    assert "not found" in result


def test_parse_json_plain_text_returns_none():
    assert parse_json_records("plain text response") is None


def test_parse_json_empty_string_returns_none():
    assert parse_json_records("") is None


def test_parse_json_bad_json_returns_none():
    assert parse_json_records("{bad json}") is None


def test_parse_json_strips_markdown_fences():
    content = "```json\n" + json.dumps(SAMPLE_RECORDS) + "\n```"
    assert parse_json_records(content) == SAMPLE_RECORDS


def test_parse_json_empty_list_returns_none():
    assert parse_json_records("[]") is None


def test_parse_json_list_without_dicts_returns_none():
    assert parse_json_records("[1, 2, 3]") is None


# ============================================================
# extract_records_from_tool_messages
# ============================================================

def _make_messages(tool_content: str = None, ai_content: str = None):
    """Build a minimal message list using real LangChain message types."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    msgs = [HumanMessage(content="list all hotels")]
    if tool_content is not None:
        msgs.append(ToolMessage(content=tool_content, name="search_hotels", tool_call_id="t1"))
    if ai_content is not None:
        msgs.append(AIMessage(content=ai_content))
    return msgs


def test_extract_records_from_tool_message():
    msgs = _make_messages(tool_content=json.dumps(SAMPLE_RECORDS))
    result = extract_records_from_tool_messages(msgs)
    assert result == SAMPLE_RECORDS


def test_extract_records_picks_last_tool_message():
    from langchain_core.messages import ToolMessage
    old = ToolMessage(content=json.dumps([{"hotel_name": "Old"}]),
                      name="search_hotels", tool_call_id="t0")
    new = ToolMessage(content=json.dumps(SAMPLE_RECORDS),
                      name="search_hotels", tool_call_id="t1")
    result = extract_records_from_tool_messages([old, new])
    assert result == SAMPLE_RECORDS


def test_extract_records_ignores_ai_message_json():
    """The LLM's JSON summary in an AIMessage must NOT be used — only ToolMessages."""
    from langchain_core.messages import AIMessage, ToolMessage
    msgs = [
        ToolMessage(content=json.dumps(SAMPLE_RECORDS), name="search_hotels", tool_call_id="t1"),
        AIMessage(content=json.dumps([{"hotel_name": "LLM summary"}])),
    ]
    result = extract_records_from_tool_messages(msgs)
    assert result == SAMPLE_RECORDS  # ToolMessage wins, not the AIMessage


def test_extract_records_returns_none_when_no_tool_messages():
    from langchain_core.messages import AIMessage, HumanMessage
    msgs = [HumanMessage(content="hello"), AIMessage(content="hi")]
    assert extract_records_from_tool_messages(msgs) is None


# ============================================================
# format_table
# ============================================================

def test_format_table_multi_row_returns_table_prefix():
    result = format_table(SAMPLE_RECORDS)
    assert result.startswith("table://")
    payload = json.loads(result[len("table://"):])
    assert payload["headers"] == ["hotel_name", "town", "rating"]
    assert len(payload["rows"]) == 3
    assert payload["count"] == 3


def test_format_table_rows_are_strings():
    result = format_table(SAMPLE_RECORDS)
    payload = json.loads(result[len("table://"):])
    for row in payload["rows"]:
        assert all(isinstance(cell, str) for cell in row)


def test_format_table_single_row_returns_plain_text():
    result = format_table([{"hotel_name": "Harbour Inn", "rating": "4.2"}])
    assert not result.startswith("table://")
    assert "hotel_name" in result
    assert "Harbour Inn" in result


def test_format_table_empty_returns_no_results():
    assert format_table([]) == "No results found."


# ============================================================
# write_csv
# ============================================================

def test_write_csv_returns_csv_prefix():
    result = write_csv(SAMPLE_RECORDS)
    assert result.startswith("csv://")


def test_write_csv_creates_valid_file():
    import csv as csv_mod
    path = write_csv(SAMPLE_RECORDS)[len("csv://"):]
    assert os.path.exists(path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv_mod.DictReader(f)
        rows = list(reader)
    assert len(rows) == 3
    assert rows[0]["hotel_name"] == "St Ives Bay Resort"
    assert rows[1]["town"] == "Falmouth"
    os.remove(path)


def test_write_csv_headers_match_record_keys():
    import csv as csv_mod
    path = write_csv(SAMPLE_RECORDS)[len("csv://"):]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv_mod.reader(f)
        headers = next(reader)
    assert headers == ["hotel_name", "town", "rating"]
    os.remove(path)


def test_write_csv_empty_returns_no_results():
    assert write_csv([]) == "No results found."


# ============================================================
# get_user_text / wants_csv
# ============================================================

def test_get_user_text_returns_last_human_message_lowercased():
    from langchain_core.messages import HumanMessage
    msgs = [HumanMessage(content="First"), HumanMessage(content="List All Hotels")]
    assert get_user_text(msgs) == "list all hotels"


def test_get_user_text_empty_when_no_human_message():
    from langchain_core.messages import AIMessage
    assert get_user_text([AIMessage(content="hi")]) == ""


def test_wants_csv_true_for_csv_keyword():
    assert wants_csv("give me the data as csv") is True


def test_wants_csv_true_for_download_csv():
    assert wants_csv("download csv please") is True


def test_wants_csv_true_for_comma_separated():
    assert wants_csv("comma-separated format") is True
    assert wants_csv("comma separated") is True


def test_wants_csv_false_for_data_query():
    assert wants_csv("list all hotels") is False


def test_wants_csv_false_for_chart_query():
    assert wants_csv("show me a bar chart") is False


# ============================================================
# last_ai_content
# ============================================================

def test_last_ai_content_returns_last_non_empty():
    from langchain_core.messages import AIMessage
    msgs = [AIMessage(content="first"), AIMessage(content=""), AIMessage(content="last")]
    assert last_ai_content(msgs) == "last"


def test_last_ai_content_skips_empty():
    from langchain_core.messages import AIMessage
    msgs = [AIMessage(content="only"), AIMessage(content="")]
    assert last_ai_content(msgs) == "only"


def test_last_ai_content_none_when_no_ai_messages():
    from langchain_core.messages import HumanMessage
    assert last_ai_content([HumanMessage(content="hi")]) is None
