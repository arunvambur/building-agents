import json
import re
from typing import Any, Callable, Optional

from langchain_core.messages import BaseMessage

from core.dsl.schema import Aggregation, Axis, Chart, VisualizationSpec
from core.dsl.validator import validate_spec
from core.renderer.registry import RendererRegistry


IMAGE_PREFIX = "data:image/png;base64,"
FILE_PREFIX = "file://"

_VISUALIZATION_RE = re.compile(
    r"\b(chart|graph|plot|visuali[sz]e|visuali[sz]ation|dashboard|excel|spreadsheet|"
    r"report|export|download|file|xlsx)\b",
    re.IGNORECASE,
)

_EXCEL_RE = re.compile(
    r"\b(excel|spreadsheet|report|export|download|file|xlsx)\b",
    re.IGNORECASE,
)


def is_visualization_request(text: str) -> bool:
    return bool(_VISUALIZATION_RE.search(text or ""))


def latest_human_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "human":
            return str(msg.content)
    return ""


def has_renderer_output(content: Any) -> bool:
    text = str(content or "")
    return text.startswith(IMAGE_PREFIX) or text.startswith(FILE_PREFIX)


def extract_latest_records(messages: list[BaseMessage]) -> list[dict]:
    for msg in reversed(messages):
        records = _records_from_content(msg.content)
        if records:
            return records
    return []


def render_fallback_visualization(
    request_text: str,
    messages: list[BaseMessage],
    renderer_registry: Optional[RendererRegistry],
    default_data_loader: Optional[Callable[[], list[dict]]] = None,
) -> Optional[str]:
    if not renderer_registry or not is_visualization_request(request_text):
        return None

    records = extract_latest_records(messages)
    if not records and default_data_loader:
        records = default_data_loader()

    spec = build_fallback_spec(request_text, records)
    validate_spec(spec)
    return renderer_registry.get(spec.output).render(spec, records)


def build_fallback_spec(request_text: str, rows: list[dict]) -> VisualizationSpec:
    lower = request_text.lower()
    chart_type = _infer_chart_type(lower)
    output = "excel" if _EXCEL_RE.search(lower) else "image"
    x_field = _infer_x_field(lower, rows)
    y_field = _infer_y_field(lower, rows, x_field)
    aggregation_op = _infer_aggregation_op(lower, y_field)
    title = _title_for(chart_type, x_field, y_field)

    chart = Chart(
        type=chart_type,
        x=Axis(field=x_field, type="dimension"),
        y=Axis(field=y_field, type="measure"),
        aggregation=Aggregation(field=y_field, op=aggregation_op),
        title=title,
    )
    return VisualizationSpec(
        charts=[chart],
        filters=None,
        layout="single",
        output=output,
    )


def _records_from_content(content: Any) -> list[dict]:
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]

    if not isinstance(content, str):
        return []

    text = content.strip()
    if not text or has_renderer_output(text):
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]

    if isinstance(parsed, dict):
        for key in ("data", "rows", "records", "results"):
            value = parsed.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _infer_chart_type(lower: str) -> str:
    if "pie" in lower or "distribution" in lower:
        return "pie"
    if "line" in lower or "trend" in lower:
        return "line"
    if "scatter" in lower:
        return "scatter"
    return "bar"


def _infer_x_field(lower: str, rows: list[dict]) -> str:
    if "town" in lower or "city" in lower:
        return "town"
    if "hotel" in lower or "name" in lower:
        return "hotel_name"

    for field in ("town", "hotel_name"):
        if _has_field(rows, field):
            return field

    return _first_text_field(rows) or "town"


def _infer_y_field(lower: str, rows: list[dict], x_field: str) -> str:
    if "rating" in lower:
        candidate = "rating"
    elif "available" in lower or "availability" in lower or "room" in lower:
        candidate = "available_rooms"
    elif "double" in lower:
        candidate = "price_double"
    elif "price" in lower or "pricing" in lower or "cost" in lower:
        candidate = "price_single"
    elif "count" in lower or "number" in lower:
        candidate = "hotel_id"
    else:
        candidate = _first_numeric_field(rows, exclude={x_field}) or "rating"

    if candidate == x_field:
        return _first_numeric_field(rows, exclude={x_field}) or "rating"
    return candidate


def _infer_aggregation_op(lower: str, y_field: str) -> str:
    if "count" in lower or "number" in lower:
        return "count"
    if y_field == "available_rooms":
        return "sum"
    return "avg"


def _title_for(chart_type: str, x_field: str, y_field: str) -> str:
    chart_name = chart_type.title()
    x_label = x_field.replace("_", " ").title()
    y_label = y_field.replace("_", " ").title()
    return f"{chart_name}: {y_label} by {x_label}"


def _has_field(rows: list[dict], field: str) -> bool:
    return any(field in row for row in rows)


def _first_text_field(rows: list[dict]) -> Optional[str]:
    for row in rows:
        for key, value in row.items():
            if isinstance(value, str):
                return key
    return None


def _first_numeric_field(rows: list[dict], exclude: set[str]) -> Optional[str]:
    for row in rows:
        for key, value in row.items():
            if key in exclude:
                continue
            if isinstance(value, (int, float)):
                return key
    return None
