from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage

from .bootstrap import build_runtime


# --------------------------------------------------
# App initialization
# --------------------------------------------------

app = FastAPI(
    title="Agent Runtime API",
    description="Plugin-based multi-agent runtime",
    version="1.0.0"
)

runtime = build_runtime()


# --------------------------------------------------
# Request / Response models
# --------------------------------------------------

class ChatRequest(BaseModel):

    message: str

    conversation_id: Optional[str] = None

    metadata: Optional[dict] = None


class ChatResponse(BaseModel):

    response: str

    agent_used: Optional[str] = None


class HealthResponse(BaseModel):

    status: str


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/health", response_model=HealthResponse)

async def health():

    return {

        "status": "ok"

    }


# --------------------------------------------------
# Chat endpoint
# --------------------------------------------------

@app.post("/chat", response_model=ChatResponse)

async def chat(request: ChatRequest):

    try:

        state = {

            "messages": [

                HumanMessage(

                    content=request.message

                )

            ]

        }

        result = runtime.invoke(state)

        response_msg = result["messages"][-1]

        return ChatResponse(

            response=response_msg.content,

            agent_used=result.get("agent")

        )

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


# --------------------------------------------------
# Debug endpoint
# --------------------------------------------------

@app.post("/debug")

async def debug_chat(request: ChatRequest):

    state = {

        "messages": [

            HumanMessage(

                content=request.message

            )

        ]

    }

    result = runtime.invoke(state)

    return result


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")

async def root():

    return {

        "service": "agent-runtime",

        "version": "1.0.0"

    }