from fastapi import FastAPI
import uuid
from langchain_core.messages import HumanMessage
from app.bootstrap import build_runtime


app = FastAPI()

runtime = build_runtime()

thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "thread_id": thread_id
    }
}


@app.post("/visualize")
async def visualize(user_input: str):

    state = {
            "messages": [
                HumanMessage(content=user_input)
            ]
        }

    result = runtime.invoke(state)


    return result["messages"][-1].content