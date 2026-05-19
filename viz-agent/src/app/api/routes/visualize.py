import json
import os
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agents.supervisor.formatting import extract_records_from_tool_messages, wants_csv, write_csv
from app.api.routes.download import register_file
from core.plugin.runtime import AgentRuntime
from tools.query_tool import list_all_hotels_with_offers

IMAGE_PREFIX = "data:image/png;base64,"
FILE_PREFIX  = "file://"
TABLE_PREFIX = "table://"
CSV_PREFIX   = "csv://"

_EXT_TO_FRIENDLY = {
    ".xlsx": ("excel", "cornwall_hotels_{}.xlsx"),
    ".pdf":  ("pdf",   "cornwall_hotels_{}.pdf"),
    ".pptx": ("ppt",   "cornwall_hotels_{}.pptx"),
    ".csv":  ("csv",   "cornwall_hotels_{}.csv"),
    ".html": ("map",   "cornwall_hotels_map_{}.html"),
}


class VisualizeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class VisualizeResponse(BaseModel):
    session_id: str
    type: Literal["text", "image", "file", "table"]
    content: str
    filename: Optional[str] = None
    file_format: Optional[str] = None      # "excel" | "pdf" | "ppt" | "csv" | "map"
    # Populated for type="table" and optionally for type="image" (both intent)
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    row_count: Optional[int] = None


def register(runtime: AgentRuntime) -> APIRouter:
    router = APIRouter()

    @router.post("/visualize", response_model=VisualizeResponse)
    async def visualize(request: VisualizeRequest):
        thread_id = request.session_id or str(uuid.uuid4())

        # CSV downloads are data exports — handle before the agent graph so
        # keyword routing cannot accidentally render a chart instead.
        if wants_csv(request.message.lower()):
            records = list_all_hotels_with_offers.invoke({})
            raw_csv = write_csv(records)
            if raw_csv.startswith(CSV_PREFIX):
                return _file_response(thread_id, raw_csv[len(CSV_PREFIX):])
            return VisualizeResponse(session_id=thread_id, type="text", content=raw_csv)

        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [HumanMessage(content=request.message)]}

        try:
            result = await runtime.ainvoke(state, config=config)
        except TimeoutError as exc:
            return JSONResponse(status_code=504, content={"detail": str(exc)})

        raw: str = result["messages"][-1].content

        # --- Inline PNG image ---
        if raw.startswith(IMAGE_PREFIX):
            table = _table_from_result(result)
            return VisualizeResponse(
                session_id=thread_id,
                type="image",
                content=raw[len(IMAGE_PREFIX):],
                headers=table["headers"] if table else None,
                rows=table["rows"] if table else None,
                row_count=table["row_count"] if table else None,
            )

        # --- Rendered file (excel / pdf / ppt / map) ---
        if raw.startswith(FILE_PREFIX):
            return _file_response(thread_id, raw[len(FILE_PREFIX):])

        # --- CSV download ---
        if raw.startswith(CSV_PREFIX):
            return _file_response(thread_id, raw[len(CSV_PREFIX):])

        # --- Tabular data with table:// prefix ---
        if raw.startswith(TABLE_PREFIX):
            try:
                payload: Dict[str, Any] = json.loads(raw[len(TABLE_PREFIX):])
                return VisualizeResponse(
                    session_id=thread_id,
                    type="table",
                    content="",
                    headers=payload.get("headers", []),
                    rows=payload.get("rows", []),
                    row_count=payload.get("count", 0),
                )
            except (json.JSONDecodeError, KeyError):
                pass

        # --- Raw JSON tabular data (LLM summarised as JSON) ---
        table = _parse_table_payload(raw)
        if table:
            return _table_response(thread_id, table)

        # --- Plain text ---
        return VisualizeResponse(
            session_id=thread_id,
            type="text",
            content=raw,
        )

    return router


def _table_response(thread_id: str, table: Dict[str, Any]) -> VisualizeResponse:
    return VisualizeResponse(
        session_id=thread_id,
        type="table",
        content="",
        headers=table["headers"],
        rows=table["rows"],
        row_count=table["row_count"],
    )


def _table_from_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """For 'both' intent responses, extract the data table alongside the image."""
    if result.get("intent") != "both":
        return None
    records = extract_records_from_tool_messages(result.get("messages", []))
    if not isinstance(records, list) or not records:
        return None
    return _records_to_table(records)


def _parse_table_payload(content: str) -> Optional[Dict[str, Any]]:
    stripped = _strip_json_fence(content)
    try:
        payload = json.loads(stripped)
    except (TypeError, json.JSONDecodeError):
        return None
    return _normalize_table_payload(payload)


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    if lines[-1].strip() == "```":
        lines = lines[1:-1]
    else:
        lines = lines[1:]
    return "\n".join(lines).strip()


def _normalize_table_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, list):
        records = [row for row in payload if isinstance(row, dict)]
        if len(records) != len(payload) or not records:
            return None
        return _records_to_table(records)

    if not isinstance(payload, dict):
        return None

    # Internal table:// shape: {"headers": [...], "rows": [...], "count": n}
    if isinstance(payload.get("headers"), list) and isinstance(payload.get("rows"), list):
        return _rows_to_table(
            headers=payload["headers"],
            rows=payload["rows"],
            row_count=payload.get("count", payload.get("row_count")),
        )

    # LLM summary shape: {"row_count": n, "columns": [...], "data": [{...}]}
    headers = payload.get("columns") or payload.get("headers")
    data = (
        payload.get("data")
        or (payload.get("rows") if isinstance(headers, list) else None)
        or payload.get("records")
        or payload.get("results")
    )
    if isinstance(headers, list) and isinstance(data, list):
        return _rows_to_table(headers=headers, rows=data, row_count=payload.get("row_count"))

    # Alternate shape: {"row_count": n, "rows": [{...}]}
    rows = payload.get("rows")
    if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
        return _rows_to_table(
            headers=headers or list(rows[0].keys()),
            rows=rows,
            row_count=payload.get("row_count"),
        )

    return None


def _records_to_table(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    headers = list(records[0].keys())
    rows = [[str(record.get(header, "")) for header in headers] for record in records]
    return {"headers": headers, "rows": rows, "row_count": len(records)}


def _rows_to_table(
    headers: List[Any],
    rows: List[Any],
    row_count: Any = None,
) -> Optional[Dict[str, Any]]:
    normalized_headers = [str(h) for h in headers]
    normalized_rows: List[List[str]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append([str(row.get(h, "")) for h in normalized_headers])
        elif isinstance(row, list):
            normalized_rows.append([str(cell) for cell in row])
        else:
            return None
    if not normalized_headers:
        return None
    count = row_count if isinstance(row_count, int) else len(normalized_rows)
    return {"headers": normalized_headers, "rows": normalized_rows, "row_count": count}


def _file_response(thread_id: str, file_path: str) -> VisualizeResponse:
    ext = os.path.splitext(file_path)[-1].lower()
    file_format, name_template = _EXT_TO_FRIENDLY.get(ext, ("file", "output_{}.bin"))
    friendly_name = name_template.format(thread_id[:8])
    file_id = register_file(file_path, friendly_name)
    return VisualizeResponse(
        session_id=thread_id,
        type="file",
        content=f"/download/{file_id}",
        filename=friendly_name,
        file_format=file_format,
    )
