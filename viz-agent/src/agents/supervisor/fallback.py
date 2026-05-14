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
    r"report|export|download|file|xlsx|histogram|distribution|heat\s*map|heatmap|"
    r"bubble|waterfall|gauge|kpi|donut|doughnut|pie|line|trend|scatter|"
    r"horizontal|sideways|stacked|grouped|area)\b",
    re.IGNORECASE,
)

_EXCEL_RE = re.compile(
    r"\b(excel|spreadsheet|xlsx)\b",
    re.IGNORECASE,
)

_PDF_RE = re.compile(
    r"\b(pdf)\b",
    re.IGNORECASE,
)

_PPT_RE = re.compile(
    r"\b(powerpoint|presentation|slides?|pptx?)\b",
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
    output = _infer_output(lower)
    charts = [_build_chart(clause, rows) for clause in _chart_clauses(lower)]
    return VisualizationSpec(
        charts=charts,
        filters=None,
        layout="grid" if len(charts) > 1 else "single",
        output=output,
    )


def _infer_output(lower: str) -> str:
    if _PDF_RE.search(lower):
        return "pdf"
    if _PPT_RE.search(lower):
        return "ppt"
    if _EXCEL_RE.search(lower):
        return "excel"
    return "image"


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


def _chart_clauses(lower: str) -> list[str]:
    text = lower.strip().rstrip(".")
    if ":" in text:
        prefix, tail = text.split(":", 1)
        if any(token in prefix for token in ("chart", "charts", "dashboard", "report", "workbook", "presentation")):
            parts = re.split(r",\s*(?:and\s+)?|;\s*", tail)
            clauses = [part.strip(" .") for part in parts if part.strip(" .")]
            if clauses:
                return clauses
    return [text]


def _build_chart(lower: str, rows: list[dict]) -> Chart:
    chart_type = _infer_chart_type(lower)
    x_field = _infer_x_field(lower, rows)
    y_field = _infer_y_field(lower, rows, x_field)
    y2_field = _infer_y2_field(lower, rows, chart_type, x_field, y_field)
    aggregation_op = _infer_aggregation_op(lower, y_field)
    title = _title_for(chart_type, x_field, y_field, y2_field)

    return Chart(
        type=chart_type,
        x=Axis(field=x_field, type="dimension"),
        y=Axis(field=y_field, type="measure"),
        y2=Axis(field=y2_field, type="measure") if y2_field else None,
        aggregation=Aggregation(field=y_field, op=aggregation_op),
        title=title,
    )


def _infer_chart_type(lower: str) -> str:
    if "heatmap" in lower or "heat map" in lower:
        return "heatmap"
    if "bubble" in lower:
        return "bubble"
    if "waterfall" in lower:
        return "waterfall"
    if "gauge" in lower or "kpi" in lower or "speedometer" in lower or "meter" in lower:
        return "gauge"
    if "stacked" in lower:
        return "stacked_bar"
    if "grouped" in lower or "side by side" in lower:
        return "grouped_bar"
    if "horizontal" in lower or "sideways" in lower:
        return "horizontal_bar"
    if "histogram" in lower:
        return "histogram"
    if "area" in lower:
        return "area"
    if "donut" in lower or "doughnut" in lower:
        return "donut"
    if "pie" in lower or "distribution" in lower:
        return "pie"
    if "line" in lower or "trend" in lower:
        return "line"
    if "scatter" in lower:
        return "scatter"
    return "bar"


def _infer_x_field(lower: str, rows: list[dict]) -> str:
    ordered_metrics = _metric_fields_in_order(lower)
    if _has_versus(lower) and ordered_metrics:
        return ordered_metrics[0]
    if "segment" in lower:
        return "market_segment"
    if "season" in lower:
        return "peak_season"
    if "category" in lower or "class" in lower:
        return "star_category"
    if "town" in lower or "city" in lower:
        return "town"
    if "hotel" in lower or "name" in lower:
        return "hotel_name"

    for field in ("town", "market_segment", "peak_season", "star_category", "hotel_name"):
        if _has_field(rows, field):
            return field

    return _first_text_field(rows) or "town"


def _infer_y_field(lower: str, rows: list[dict], x_field: str) -> str:
    ordered_metrics = _metric_fields_in_order(lower)
    if _has_versus(lower) and len(ordered_metrics) >= 2:
        candidate = ordered_metrics[1]
    elif "occupancy" in lower:
        candidate = "occupancy_rate"
    elif "cancellation" in lower or "cancelation" in lower:
        candidate = "cancellation_rate"
    elif "revenue" in lower or "sales" in lower:
        candidate = "monthly_revenue"
    elif "review" in lower:
        candidate = "review_count"
    elif "repeat" in lower or "loyal" in lower:
        candidate = "repeat_guest_rate"
    elif "length" in lower or "stay" in lower or "nights" in lower:
        candidate = "avg_length_of_stay"
    elif "beach" in lower:
        candidate = "distance_beach_km"
    elif "station" in lower or "train" in lower:
        candidate = "distance_station_km"
    elif "family" in lower:
        candidate = "family_score"
    elif "business" in lower:
        candidate = "business_score"
    elif "sustainability" in lower or "sustainable" in lower or "green" in lower:
        candidate = "sustainability_score"
    elif "parking" in lower:
        candidate = "parking_spaces"
    elif "spa" in lower:
        candidate = "spa_available"
    elif "pet" in lower:
        candidate = "pet_friendly"
    elif "latitude" in lower:
        candidate = "latitude"
    elif "longitude" in lower:
        candidate = "longitude"
    elif "rating" in lower:
        candidate = "rating"
    elif "single" in lower:
        candidate = "price_single"
    elif "double" in lower:
        candidate = "price_double"
    elif "price" in lower or "pricing" in lower or "cost" in lower:
        candidate = "price_single"
    elif "available" in lower or "availability" in lower or "room" in lower:
        candidate = "available_rooms"
    elif "count" in lower or "number" in lower:
        candidate = "hotel_id"
    else:
        candidate = _first_numeric_field(rows, exclude={x_field}) or "rating"

    if candidate == x_field:
        return _first_numeric_field(rows, exclude={x_field}) or "rating"
    return candidate


def _has_versus(lower: str) -> bool:
    return " versus " in lower or " vs " in lower or " against " in lower


def _metric_fields_in_order(lower: str) -> list[str]:
    metric_patterns = [
        ("occupancy", "occupancy_rate"),
        ("cancellation", "cancellation_rate"),
        ("cancelation", "cancellation_rate"),
        ("revenue", "monthly_revenue"),
        ("sales", "monthly_revenue"),
        ("review", "review_count"),
        ("repeat", "repeat_guest_rate"),
        ("loyal", "repeat_guest_rate"),
        ("length", "avg_length_of_stay"),
        ("stay", "avg_length_of_stay"),
        ("nights", "avg_length_of_stay"),
        ("beach", "distance_beach_km"),
        ("station", "distance_station_km"),
        ("train", "distance_station_km"),
        ("family", "family_score"),
        ("business", "business_score"),
        ("sustainability", "sustainability_score"),
        ("sustainable", "sustainability_score"),
        ("green", "sustainability_score"),
        ("parking", "parking_spaces"),
        ("spa", "spa_available"),
        ("pet", "pet_friendly"),
        ("latitude", "latitude"),
        ("longitude", "longitude"),
        ("rating", "rating"),
        ("single", "price_single"),
        ("double", "price_double"),
        ("price", "price_single"),
        ("cost", "price_single"),
        ("available", "available_rooms"),
        ("availability", "available_rooms"),
        ("room", "available_rooms"),
        ("count", "hotel_id"),
        ("number", "hotel_id"),
    ]
    matches: list[tuple[int, str]] = []
    for token, field in metric_patterns:
        index = lower.find(token)
        if index >= 0 and field not in [match[1] for match in matches]:
            matches.append((index, field))
    return [field for _, field in sorted(matches)]


def _infer_y2_field(
    lower: str,
    rows: list[dict],
    chart_type: str,
    x_field: str,
    y_field: str,
) -> Optional[str]:
    comparative_types = {"grouped_bar", "stacked_bar", "area"}
    if chart_type in comparative_types:
        if "single" in lower and "double" in lower and y_field != "price_double":
            return "price_double"
        if "single" in lower and "double" in lower and y_field != "price_single":
            return "price_single"
        if "occupancy" in lower and ("revenue" in lower or "sales" in lower) and y_field != "monthly_revenue":
            return "monthly_revenue"
        if "family" in lower and "business" in lower and y_field != "business_score":
            return "business_score"
        if "rating" in lower and ("price" in lower or "cost" in lower) and y_field != "price_single":
            return "price_single"

    if chart_type == "bubble":
        if "available_rooms" != y_field and _has_field(rows, "available_rooms"):
            return "available_rooms"
        return _first_numeric_field(rows, exclude={x_field, y_field})

    if chart_type == "heatmap":
        if "hotel" in lower or "name" in lower:
            return "hotel_name"
        return _first_text_field(rows, exclude={x_field})

    return None


def _infer_aggregation_op(lower: str, y_field: str) -> str:
    if "count" in lower or "number" in lower:
        return "count"
    if y_field == "available_rooms":
        return "sum"
    return "avg"


def _title_for(chart_type: str, x_field: str, y_field: str, y2_field: Optional[str] = None) -> str:
    chart_name = chart_type.title()
    x_label = x_field.replace("_", " ").title()
    y_label = y_field.replace("_", " ").title()
    if y2_field:
        y2_label = y2_field.replace("_", " ").title()
        return f"{chart_name}: {y_label} and {y2_label} by {x_label}"
    return f"{chart_name}: {y_label} by {x_label}"


def _has_field(rows: list[dict], field: str) -> bool:
    return any(field in row for row in rows)


def _first_text_field(rows: list[dict], exclude: Optional[set[str]] = None) -> Optional[str]:
    exclude = exclude or set()
    for row in rows:
        for key, value in row.items():
            if key in exclude:
                continue
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
