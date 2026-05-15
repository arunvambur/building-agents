"""
Pure data formatting helpers for the supervisor's data-only response path.
No LangGraph or LangChain imports — safe to import in tests without those deps.
"""
import csv
import json
import logging
import os
import tempfile
import uuid as _uuid
from typing import Optional, Union

logger = logging.getLogger(__name__)

TABLE_PREFIX = "table://"
CSV_PREFIX   = "csv://"


def parse_json_records(content: str) -> Optional[Union[list[dict], str]]:
    """
    Parses a JSON string into a list of dicts.
    Strips markdown code fences if present.
    Returns:
      - list[dict]  — records found
      - str         — error message if tool returned an error dict
      - None        — not valid JSON or not tabular
    """
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]
        stripped = "\n".join(inner)

    try:
        payload = json.loads(stripped)
    except (TypeError, json.JSONDecodeError):
        return None

    if isinstance(payload, dict) and "error" in payload:
        return f"Sorry, I could not retrieve the data: {payload['error']}"

    if isinstance(payload, list):
        records = [r for r in payload if isinstance(r, dict)]
        return records if records else None

    if isinstance(payload, dict):
        return [payload]

    return None


def extract_records_from_tool_messages(messages: list) -> Optional[Union[list[dict], str]]:
    """
    Scans messages in reverse for the last ToolMessage containing JSON records.
    Avoids importing LangChain at module level — imports inside function.
    """
    from langchain_core.messages import ToolMessage
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        result = parse_json_records(msg.content)
        if result is not None:
            return result
    return None


def get_user_text(messages: list) -> str:
    """Returns the content of the last HumanMessage, lowercased."""
    from langchain_core.messages import HumanMessage
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content.lower()
    return ""


def wants_csv(user_text: str) -> bool:
    return any(kw in user_text for kw in (
        "csv", "comma separated", "comma-separated", "download csv"
    ))


def last_ai_content(messages: list) -> Optional[str]:
    """Returns the content of the last non-empty AIMessage."""
    from langchain_core.messages import AIMessage
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return None


def format_table(records: list[dict]) -> str:
    """
    Returns a 'table://<json>' string for multi-row results.
    Single-record results are also returned as tables so the UI has a
    consistent data display path.
    """
    if not records:
        return "No results found."

    headers = list(records[0].keys())
    rows = [[str(r.get(h, "")) for h in headers] for r in records]
    payload = json.dumps({"headers": headers, "rows": rows, "count": len(records)})
    return f"{TABLE_PREFIX}{payload}"


def write_csv(records: list[dict]) -> str:
    """
    Writes records to a temp CSV file.
    Returns a 'csv://<path>' string for the API layer to register as a download.
    """
    if not records:
        return "No results found."

    headers = list(records[0].keys())
    path = os.path.join(tempfile.gettempdir(), f"{_uuid.uuid4()}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)

    logger.info("[data_agent] CSV written — %s (%d records)", path, len(records))
    return f"{CSV_PREFIX}{path}"
