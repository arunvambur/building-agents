import json
import os
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.api.routes.download import register_file
from core.plugin.runtime import AgentRuntime

IMAGE_PREFIX = "data:image/png;base64,"
FILE_PREFIX  = "file://"
TABLE_PREFIX = "table://"
CSV_PREFIX   = "csv://"

_EXT_TO_FRIENDLY = {
    ".xlsx": ("excel", "cornwall_hotels_{}.xlsx"),
    ".pdf":  ("pdf",   "cornwall_hotels_{}.pdf"),
    ".pptx": ("ppt",   "cornwall_hotels_{}.pptx"),
    ".csv":  ("csv",   "cornwall_hotels_{}.csv"),
}


class VisualizeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class VisualizeResponse(BaseModel):
    session_id: str
    type: Literal["text", "image", "file", "table"]
    content: str
    filename: Optional[str] = None
    file_format: Optional[str] = None      # "excel" | "pdf" | "ppt" | "csv"
    # Populated for type="table"
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    row_count: Optional[int] = None


def register(runtime: AgentRuntime) -> APIRouter:
    router = APIRouter()

    @router.post("/visualize", response_model=VisualizeResponse)
    async def visualize(request: VisualizeRequest):
        thread_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [HumanMessage(content=request.message)]}

        try:
            result = await runtime.ainvoke(state, config=config)
        except TimeoutError as exc:
            return JSONResponse(status_code=504, content={"detail": str(exc)})

        raw: str = result["messages"][-1].content

        # --- Inline PNG image ---
        if raw.startswith(IMAGE_PREFIX):
            return VisualizeResponse(
                session_id=thread_id,
                type="image",
                content=raw[len(IMAGE_PREFIX):],
            )

        # --- Rendered file (excel / pdf / ppt) ---
        if raw.startswith(FILE_PREFIX):
            return _file_response(thread_id, raw[len(FILE_PREFIX):])

        # --- CSV download ---
        if raw.startswith(CSV_PREFIX):
            return _file_response(thread_id, raw[len(CSV_PREFIX):])

        # --- Tabular data (rendered as table in UI) ---
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
                pass  # fall through to plain text

        # --- Plain text ---
        return VisualizeResponse(
            session_id=thread_id,
            type="text",
            content=raw,
        )

    return router


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
