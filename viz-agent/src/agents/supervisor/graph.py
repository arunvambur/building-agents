from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


SUPERVISOR_SYSTEM_PROMPT = (
    "You are a supervisor orchestrating a data visualization pipeline. "
    "Given the user request and the current conversation, decide the next step:\n"
    "- 'data_agent': fetch or query the required data.\n"
    "- 'viz_agent': build and render the visualization from available data.\n"
    "- 'FINISH': the task is complete and a final answer is ready.\n"
    "Always run 'data_agent' before 'viz_agent' unless data is already present."
)


class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str
    data_ready: bool
    viz_ready: bool


def build_supervisor_graph(
    llm: Any,
    data_agent_graph: Any,
    viz_agent_graph: Any,
    checkpointer: Optional[Any] = None,
) -> Any:
    """
    Builds a LangGraph supervisor that sequences data_agent → viz_agent.
    The supervisor LLM decides routing at each step until FINISH.
    """

    from pydantic import BaseModel, Field

    class NextStep(BaseModel):
        next: str = Field(
            ...,
            description="Next agent to call: 'data_agent', 'viz_agent', or 'FINISH'.",
        )

    supervisor_llm = llm.with_structured_output(NextStep)

    def supervisor_node(state: SupervisorState) -> dict:

        if not state.get("data_ready", False):
            return {"next": "data_agent"}

        if not state.get("viz_ready", False):
            return {"next": "viz_agent"}

        return {"next": "FINISH"}

    def data_agent_node(state: SupervisorState) -> dict:
        result = data_agent_graph.invoke(
            {"messages": state["messages"]}
        )
        
        messages = result["messages"]
        
        messages.append(
            SystemMessage(content="Data agent completed.")
        )

        return {
            "messages": result["messages"],
            "data_ready": True,
        }

    def viz_agent_node(state: SupervisorState) -> dict:
        result = viz_agent_graph.invoke(
            {"messages": state["messages"]}
        )
        
        messages = result["messages"]
        
        messages.append(
            SystemMessage(content="Visualization generation completed.")
        )

        return {
            "messages": result["messages"],
            "viz_ready": True,
        }

    def route_supervisor(state: SupervisorState) -> str:
        next_step = state.get("next", "FINISH")
        if next_step == "data_agent":
            return "data_agent"
        if next_step == "viz_agent":
            return "viz_agent"
        return END

    builder = StateGraph(SupervisorState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("data_agent", data_agent_node)
    builder.add_node("viz_agent", viz_agent_node)

    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", route_supervisor)
    builder.add_edge("data_agent", "supervisor")
    builder.add_edge("viz_agent", "supervisor")

    return builder.compile(checkpointer=checkpointer)
