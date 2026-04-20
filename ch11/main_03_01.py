
import os
import asyncio
import operator
import json
import random

from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict, Literal, Optional
from langchain_chroma import Chroma
from llm_models import get_llm
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.prebuilt import create_react_agent

# -----------------------------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------------------------

load_dotenv()

# ----------------------------------------------------------------------------
# Prepgare knowledge base
# ----------------------------------------------------------------------------

UK_DESTINATIONS = [
    "Cornwall",
    "North_Cornwall",
    "South_Cornwall",
    "West_Cornwall",
]

async def build_vectorstore(destinations: Sequence[str]) -> Chroma:
    """Download Wikivoyage pages and create a Chroma vector store."""
    urls = [f"https://en.wikivoyage.org/wiki/{slug}" for slug in destinations]
    
    loader = AsyncHtmlLoader(urls)
    print("Downloading destination pages ...")
    docs = await loader.aload()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=128)
    chunks = sum([splitter.split_documents([d]) for d in docs], [])

    print(f"Embedding {len(chunks)} chunks ...")
    vectordb_client = Chroma.from_documents(chunks, embedding=OpenAIEmbeddings())
    print("Vector store ready.\n")

    return vectordb_client

_ti_vectorstore_client: Chroma | None = None

def get_travel_info_vectorstore() -> Chroma:
    global _ti_vectorstore_client
    if _ti_vectorstore_client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("""Set OPENAI_API_KEY env variable and re-run""")
        _ti_vectorstore_client = asyncio.run(build_vectorstore(UK_DESTINATIONS))

    return _ti_vectorstore_client

_ti_vectorstore_client = get_travel_info_vectorstore()
ti_retriever = _ti_vectorstore_client.as_retriever()

# ----------------------------------------------------------------------------
# WeatherForecastService
# ----------------------------------------------------------------------------
class WeatherForecast(TypedDict):
    town: str
    weather: Literal["sunny", "foggy", "rainy", "windy"]
    temperature: int

class WeatherForecastService:
    _weather_options = ["sunny", "foggy", "rainy", "windy"]
    _temp_min = 18
    _temp_max = 31

    @classmethod
    def get_forecast(cls, town: str) -> Optional[WeatherForecast]:
        weather = random.choice(cls._weather_options)
        temperature = random.randint(cls._temp_min, cls._temp_max)
        return WeatherForecast(town=town, weather=weather, temperature=temperature)

# ----------------------------------------------------------------------------
# 2. Define the tool
# ----------------------------------------------------------------------------

@tool(description="""Search travel information about destinations in England.""")
def search_travel_info(query: str)-> str:
    """Search embedded wikivoyage contnet for information about destinations in England."""
    docs = ti_retriever.invoke(query)
    top = docs[:4] if isinstance(docs, list) else docs
    return "\n--\n".join(d.page_content for d in top)

@tool(description="Get the weather forecase, given a town name.")
def weather_forecast(town: str) -> dict:
    """Get a mock weather forecast for a given town. Returns a WeatherForecast object with weather and temperature."""
    forecast = WeatherForecastService.get_forecast(town)
    if forecast is None:
        return {"error": f"No weather data available for '{town}'."}
    return forecast




# Registering tools with the LLM
TOOLS = [
    search_travel_info,
    weather_forecast
]

llm_model = get_llm()
#llm_with_tools = llm_model.bind_tools(TOOLS)

# Agent state: Tracking the conversation
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    remaining_steps: RemainingSteps

# ----------------------------------------------------------------------------
# Build the travel info assistant React Agent
# ----------------------------------------------------------------------------

travel_info_agent = create_react_agent(
    model= llm_model,
    tools=TOOLS,
    state_schema=AgentState,
    prompt="You are a helpful assistant that can search travel information and get the weather forecast. Only use the tools to find the information you need (including town names).",
)

# Running the agent chatbot: The Read-Eval-Print Loop

def chat_loop():
    print("UK Travel Assistant (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        state = {"messages": [HumanMessage(content=user_input)]}
        result = travel_info_agent.invoke(state)
        response_msg = result["messages"][-1]
        print(f"Assistant: {response_msg.content}\n")

if __name__ == "__main__":
    chat_loop()