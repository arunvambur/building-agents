import uuid
from typing import Optional

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from core.plugin.runtime import AgentRuntime

router = APIRouter()


class VisualizeRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class VisualizeResponse(BaseModel):
    response: str
    session_id: str


def register(runtime: AgentRuntime) -> APIRouter:
    """Returns the router with the runtime injected via closure."""

    @router.post("/visualize", response_model=VisualizeResponse)
    async def visualize(request: VisualizeRequest) -> VisualizeResponse:
        thread_id = request.session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [HumanMessage(content=request.message)]}

        result = await runtime.ainvoke(state, config=config)

        return VisualizeResponse(
            response=result["messages"][-1].content,
            session_id=thread_id,
        )

    return router
