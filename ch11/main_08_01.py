
from enum import Enum
import os
import asyncio
import operator
import json
import random
import uuid

from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict, Literal, Optional, List, Dict
from langchain_chroma import Chroma
from pydantic import BaseModel, Field
from llm_models import get_llm
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver


# -----------------------------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------------------------

load_dotenv()

llm_model = get_llm()

# -----------------------------------------------------------------------------
# Instantiate the SQLite database
# -----------------------------------------------------------------------------
hotel_db = SQLDatabase.from_uri("sqlite:///hotel_db/cornwall_hotels.db")
hotel_db_toolkit = SQLDatabaseToolkit(db=hotel_db, llm=llm_model)
hotel_db_toolkit_tools = hotel_db_toolkit.get_tools()

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
# B&B booking tool
# ----------------------------------------------------------------------------
class BnBOffer(TypedDict): #A
    bnb_id: int
    bnb_name: str
    town: str
    available_rooms: int
    price_per_room: float

class BnBBookingService: #B
    @staticmethod
    def get_offers_near_town(town: str, num_rooms: int) \
        -> List[BnBOffer]: #C
        # Mocked REST API response: multiple BnBs per destination
        mock_bnb_offers = [ #D
            # Newquay
            {"bnb_id": 1, "bnb_name": "Seaside BnB", 
            "town": "Newquay", "available_rooms": 3, 
            "price_per_room": 80.0},
            {"bnb_id": 2, "bnb_name": "Surfside Guesthouse", 
            "town": "Newquay", "available_rooms": 2, 
            "price_per_room": 85.0},
            # Falmouth
            {"bnb_id": 3, "bnb_name": "Harbour View BnB", 
            "town": "Falmouth", "available_rooms": 4, 
            "price_per_room": 78.0},
            {"bnb_id": 4, "bnb_name": "Seafarer's Rest", 
            "town": "Falmouth", "available_rooms": 1, 
            "price_per_room": 90.0},
            # St Austell
            {"bnb_id": 5, "bnb_name": "Garden Gate BnB", 
            "town": "St Austell", "available_rooms": 2, "price_per_room": 82.0},
            {"bnb_id": 6, "bnb_name": "Coastal Cottage BnB", 
            "town": "St Austell", "available_rooms": 3, "price_per_room": 88.0},
            # Penzance
            {"bnb_id": 7, "bnb_name": "Penzance Pier BnB", 
            "town": "Penzance", "available_rooms": 2, "price_per_room": 95.0},
            {"bnb_id": 8, "bnb_name": "Cornish Charm BnB", 
            "town": "Penzance", "available_rooms": 3, "price_per_room": 87.0},
            # Camborne
            {"bnb_id": 9, "bnb_name": "Camborne Corner BnB", 
            "town": "Camborne", "available_rooms": 2, "price_per_room": 75.0},
            {"bnb_id": 10, "bnb_name": "Rose Cottage BnB", 
            "town": "Camborne", "available_rooms": 2, "price_per_room": 79.0},
            # Hayle
            {"bnb_id": 11, "bnb_name": "Hayle Haven BnB", 
            "town": "Hayle", "available_rooms": 3, "price_per_room": 83.0},
            {"bnb_id": 12, "bnb_name": "Dune View BnB", 
            "town": "Hayle", "available_rooms": 1, "price_per_room": 81.0},
            # Land's End
            {"bnb_id": 13, "bnb_name": "Land's End Lookout BnB", 
            "town": "Land's End", "available_rooms": 2, "price_per_room": 100.0},
            {"bnb_id": 14, "bnb_name": "Atlantic Edge BnB", 
            "town": "Land's End", "available_rooms": 2, "price_per_room": 105.0},
            # Bude
            {"bnb_id": 15, "bnb_name": "Bude Beach BnB", 
            "town": "Bude", "available_rooms": 2, "price_per_room": 77.0},
            {"bnb_id": 16, "bnb_name": "Cliffside BnB", 
            "town": "Bude", "available_rooms": 3, "price_per_room": 80.0},
            # Padstow
            {"bnb_id": 17, "bnb_name": "Padstow Harbour BnB", 
            "town": "Padstow", "available_rooms": 2, "price_per_room": 92.0},
            {"bnb_id": 18, "bnb_name": "Fisherman's Rest BnB", 
            "town": "Padstow", "available_rooms": 2, "price_per_room": 89.0},
            # St Ives
            {"bnb_id": 19, "bnb_name": "St Ives Bay BnB", "town": "St Ives", "available_rooms": 3, "price_per_room": 97.0},
            {"bnb_id": 20, "bnb_name": "Artists' Retreat BnB", "town": "St Ives", "available_rooms": 2, "price_per_room": 102.0},
            # Looe
            {"bnb_id": 21, "bnb_name": "Looe Riverside BnB", "town": "Looe", "available_rooms": 2, "price_per_room": 84.0},
            {"bnb_id": 22, "bnb_name": "Harbour Lights BnB", "town": "Looe", "available_rooms": 2, "price_per_room": 86.0},
            # Polperro
            {"bnb_id": 23, "bnb_name": "Polperro Cove BnB", "town": "Polperro", "available_rooms": 2, "price_per_room": 91.0},
            {"bnb_id": 24, "bnb_name": "Smuggler's Rest BnB", "town": "Polperro", "available_rooms": 2, "price_per_room": 93.0},
            # Mevagissey
            {"bnb_id": 25, "bnb_name": "Mevagissey Harbour BnB", "town": "Mevagissey", "available_rooms": 2, "price_per_room": 90.0},
            {"bnb_id": 26, "bnb_name": "Seafarer's BnB", "town": "Mevagissey", "available_rooms": 2, "price_per_room": 88.0},
            # Port Isaac
            {"bnb_id": 27, "bnb_name": "Port Isaac View BnB", 
            "town": "Port Isaac", "available_rooms": 2, 
            "price_per_room": 99.0},
            {"bnb_id": 28, "bnb_name": "Fisherman's Cottage BnB", 
            "town": "Port Isaac", "available_rooms": 2, 
            "price_per_room": 101.0},
            # Fowey
            {"bnb_id": 29, "bnb_name": "Fowey Quay BnB", 
            "town": "Fowey", "available_rooms": 2, 
            "price_per_room": 94.0},
            {"bnb_id": 30, "bnb_name": "Riverside Rest BnB", 
            "town": "Fowey", "available_rooms": 2, 
            "price_per_room": 96.0},
        ]
        offers = [offer for offer in 
            mock_bnb_offers 
            if offer["town"].lower() == town.lower() 
               and offer["available_rooms"] >= num_rooms]
        return offers


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


@tool(description="""Chck BnB rom availability and price for a destination in Cornwall.""")
def check_bnb_availability(destination: str, num_rooms: int )-> List[Dict]:
    offers = BnBBookingService.get_offers_near_town(destination, num_rooms)
    if not offers:
        return [{"error": f"No available BnB's found in {destination} for {num_rooms} rooms."}]
    return offers

# ----------------------------------------------------------------------------
# Registering tools with the LLM
# ----------------------------------------------------------------------------
TOOLS = [
    search_travel_info,
    weather_forecast,
    check_bnb_availability
]

BOOKING_TOOLS = hotel_db_toolkit_tools + [check_bnb_availability]


llm_with_tools = llm_model.bind_tools(TOOLS)
llm_with_booking_tools = llm_model.bind_tools(BOOKING_TOOLS)

# Agent state: Tracking the conversation
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# Executing tool calls

class ToolsExecutionNode:
    """Execute tools requested by the LLM in the last AI Message."""

    def __init__(self, tools: Sequence):
        self._tools_by_name = {t.name: t for t in tools}

    def __call__(self, state: dict):
        messages: Sequence[BaseMessage] = state.get("messages", [])

        last_msg = messages[-1]
        tool_messages: list[ToolMessage] = []
        tool_calls = getattr(last_msg, "tool_calls", [])

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool = self._tools_by_name[tool_name]
            result = tool.invoke(tool_args)
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    name=tool_name,
                    tool_call_id = tool_call["id"],
                )
            )

        return {"messages": tool_messages}
    
tools_execution_node = ToolsExecutionNode(TOOLS)
booking_tools_execution_node = ToolsExecutionNode(BOOKING_TOOLS)

# The LLM node: Coordinating reasoning and action

def llm_node(state: AgentState):
    """LLM note that decides whether to call the search tool."""
    #current_messages = state["messages"] 
    system_message = SystemMessage(content="""You are a helpful assistant
    that can search travel information and get the weather forecast.
    Only use the tools to find the information
    you need (including town names).""")
    current_messages = state["messages"] + [system_message]

    response_message = llm_with_tools.invoke(current_messages)

    return {"messages": [response_message]}

def llm_booking_node(state: AgentState):
    """LLM node that decides whether to call the booking tool."""
    #current_messages = state["messages"]
    system_message = SystemMessage(content="""You are a helpful assistant that can check
    hotel and BnB room availability and price for a
    destination in Cornwall. You can use the tools to
    get the information you need. If the users does
    not specify the accommodation type, you should
    check both hotels and BnBs.""")
    # current_messages.append(system_message)
    current_messages = state["messages"] + [system_message]

    response_message = llm_with_booking_tools.invoke(current_messages)

    return {"messages": [response_message]}


def route_tools(state):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# Assembling the agent graph

builder = StateGraph(AgentState)
builder.add_node("llm_node", llm_node)
builder.add_node("tools", tools_execution_node)

builder.add_conditional_edges("llm_node", route_tools)

builder.add_edge("tools", "llm_node")
builder.set_entry_point("llm_node")
travel_info_agent = builder.compile()

booking_builder = StateGraph(AgentState)
booking_builder.add_node("llm_node", llm_booking_node)
booking_builder.add_node("tools", booking_tools_execution_node)

booking_builder.add_conditional_edges("llm_node", route_tools)

booking_builder.add_edge("tools", "llm_node")
booking_builder.set_entry_point("llm_node")
accommodation_booking_agent = booking_builder.compile()

# ----------------------------------------------------------------------------
# Router Agent
# ----------------------------------------------------------------------------
class AgentType(str, Enum):
    travel_info_agent = "travel_info_agent"
    accommodation_booking_agent = "accommodation_booking_agent"

class AgentTypeOutput(BaseModel):
    agent: AgentType = Field(..., description="Which agent should handle the query?")

llm_router = llm_model.with_structured_output(AgentTypeOutput)

ROUTER_SYSTEM_PROMPT = (
    """You are a router. Given the following user message,
    decide if it is a travel information question
    (about destinations, attractions, or general travel info) """
    """or an accommodation booking question (about hotels,
    BnBs, room availability, or prices).\n"""
    """If it is a travel information question,
    respond with 'travel_info_agent'.\n"""
    """If it is an accommodation booking question,
    respond with 'accommodation_booking_agent'."""
)

def router_agent_node(state: AgentState) -> Command[AgentType]:
    """Router node: decides which agent should handle the user query."""
    messages = state["messages"]
    last_msg = messages[-1] if messages else None
    if isinstance(last_msg, HumanMessage):
        user_input = last_msg.content
        router_messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_input)
        ]
    router_response = llm_router.invoke(router_messages)
    agent_name = router_response.agent.value

    return Command(update = state, goto=agent_name)

graph = StateGraph(AgentState)
graph.add_node("router_agent", router_agent_node)
graph.add_node("travel_info_agent", travel_info_agent)
graph.add_node("accommodation_booking_agent", accommodation_booking_agent)

graph.add_edge("travel_info_agent", END)
graph.add_edge("accommodation_booking_agent", END)

graph.set_entry_point("router_agent")

checkpointer = InMemorySaver()
travel_assistant = graph.compile(checkpointer=checkpointer)


# ----------------------------------------------------------------------------
# Running the agent chatbot: The Read-Eval-Print Loop
# ----------------------------------------------------------------------------


def chat_loop():
    thread_id = uuid.uuid1()
    print(f'Thread ID: {thread_id}')

    config = {"configurable": {"thread_id": thread_id}}

    print("UK Travel Assistant (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        state = {"messages": [HumanMessage(content=user_input)]}
        result = travel_assistant.invoke(state, config=config)
        response_msg = result["messages"][-1]
        print(f"Assistant: {response_msg.content}\n")

if __name__ == "__main__":
    chat_loop()