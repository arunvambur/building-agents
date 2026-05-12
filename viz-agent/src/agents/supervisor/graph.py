from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


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
    Supervisor that sequences data_agent → viz_agent deterministically.
    - data_agent runs first, its messages (including tool results) are passed to viz_agent.
    - viz_agent must call render_visualization and its tool result becomes the final message.
    - The last message in state is the raw renderer output (base64 image or file:// path).
    """

    def supervisor_node(state: SupervisorState) -> dict:
        if not state.get("data_ready", False):
            return {"next": "data_agent"}
        if not state.get("viz_ready", False):
            return {"next": "viz_agent"}
        return {"next": "FINISH"}

    def data_agent_node(state: SupervisorState) -> dict:
        result = data_agent_graph.invoke({"messages": state["messages"]})
        # Pass all data agent messages (including tool results) forward
        # so the viz_agent can extract the raw data from them.
        return {
            "messages": result["messages"],
            "data_ready": True,
        }

    def viz_agent_node(state: SupervisorState) -> dict:
        result = viz_agent_graph.invoke({"messages": state["messages"]})
        all_messages = result["messages"]

        # Find the last ToolMessage — that is the raw renderer output
        # (base64 PNG or file:// path). Surface it as the final AI message
        # so the API layer can detect the prefix correctly.
        from langchain_core.messages import AIMessage, ToolMessage

        renderer_output = None
        for msg in reversed(all_messages):
            if isinstance(msg, ToolMessage):
                renderer_output = msg.content
                break

        if renderer_output and (
            renderer_output.startswith("data:image/png;base64,")
            or renderer_output.startswith("file://")
        ):
            # Replace the last message with an AIMessage carrying the raw output
            final_messages = list(all_messages) + [AIMessage(content=renderer_output)]
        else:
            # viz_agent responded with text — keep as-is
            final_messages = list(all_messages)

        return {
            "messages": final_messages,
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
