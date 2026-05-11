import uuid
from typing import Literal, Optional

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.api.routes.download import register_file
from core.plugin.runtime import AgentRuntime

router = APIRouter()

# Sentinel prefix the rendering tools embed in their return value
# so the API layer can detect image vs file vs text responses.
IMAGE_PREFIX = "data:image/png;base64,"
FILE_PREFIX = "file://"


class VisualizeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class VisualizeResponse(BaseModel):
    session_id: str
    type: Literal["text", "image", "file"]
    content: str                  # base64 PNG | download URL | plain text
    filename: Optional[str] = None


def register(runtime: AgentRuntime) -> APIRouter:

    @router.post("/visualize", response_model=VisualizeResponse)
    async def visualize(request: VisualizeRequest) -> VisualizeResponse:
        thread_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [HumanMessage(content=request.message)]}

        result = await runtime.ainvoke(state, config=config)
        raw: str = result["messages"][-1].content

        # --- Image response ---
        if raw.startswith(IMAGE_PREFIX):
            return VisualizeResponse(
                session_id=thread_id,
                type="image",
                content=raw[len(IMAGE_PREFIX):],  # strip prefix, send raw base64
            )

        # --- File response ---
        if raw.startswith(FILE_PREFIX):
            file_path = raw[len(FILE_PREFIX):]
            filename = file_path.split("/")[-1].split("\\")[-1]
            friendly_name = f"cornwall_hotels_{thread_id[:8]}.xlsx"
            file_id = register_file(file_path, friendly_name)
            return VisualizeResponse(
                session_id=thread_id,
                type="file",
                content=f"/download/{file_id}",
                filename=friendly_name,
            )

        # --- Plain text response ---
        return VisualizeResponse(
            session_id=thread_id,
            type="text",
            content=raw,
        )

    return router
