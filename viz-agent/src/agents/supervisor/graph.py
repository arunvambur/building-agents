import json
from typing import Annotated, Any, Callable, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agents.supervisor.fallback import (
    extract_latest_records,
    has_renderer_output,
    is_visualization_request,
    latest_human_text,
    render_fallback_visualization,
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
    renderer_registry: Optional[Any] = None,
    default_data_loader: Optional[Callable[[], list[dict]]] = None,
) -> Any:
    """
    Supervisor that sequences data_agent → viz_agent deterministically.
    - data_agent runs first, its messages (including tool results) are passed to viz_agent.
    - viz_agent must call render_visualization and its tool result becomes the final message.
    - If the local model misses a required data/render tool call for a visualization request,
      the supervisor falls back to the default hotel dataset and renderer registry.
    - The last message in state is the raw renderer output (base64 image or file:// path).
    """

    def supervisor_node(state: SupervisorState) -> dict:
        last_message = state["messages"][-1] if state.get("messages") else None
        if (
            getattr(last_message, "type", None) == "human"
            and (state.get("data_ready", False) or state.get("viz_ready", False))
        ):
            return {
                "next": "data_agent",
                "data_ready": False,
                "viz_ready": False,
            }
        if not state.get("data_ready", False):
            return {"next": "data_agent"}
        if not state.get("viz_ready", False):
            return {"next": "viz_agent"}
        return {"next": "FINISH"}

    def data_agent_node(state: SupervisorState) -> dict:
        try:
            result = data_agent_graph.invoke({"messages": state["messages"]})
            messages = list(result["messages"])
        except Exception:
            request_text = latest_human_text(state["messages"])
            if not default_data_loader or not is_visualization_request(request_text):
                raise
            messages = list(state["messages"])

        request_text = latest_human_text(messages)
        if (
            default_data_loader
            and is_visualization_request(request_text)
            and not extract_latest_records(messages)
        ):
            data = default_data_loader()
            tool_call_id = "fallback-list-all-hotels"
            messages.extend(
                [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "list_all_hotels_with_offers",
                                "args": {},
                                "id": tool_call_id,
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps(data),
                        name="list_all_hotels_with_offers",
                        tool_call_id=tool_call_id,
                    ),
                ]
            )

        # Pass all data agent messages (including tool results) forward
        # so the viz_agent can extract the raw data from them.
        return {
            "messages": messages,
            "data_ready": True,
        }

    def viz_agent_node(state: SupervisorState) -> dict:
        try:
            result = viz_agent_graph.invoke({"messages": state["messages"]})
            all_messages = result["messages"]
        except Exception:
            request_text = latest_human_text(state["messages"])
            fallback_output = render_fallback_visualization(
                request_text=request_text,
                messages=state["messages"],
                renderer_registry=renderer_registry,
                default_data_loader=default_data_loader,
            )
            if fallback_output:
                return {
                    "messages": list(state["messages"]) + [AIMessage(content=fallback_output)],
                    "viz_ready": True,
                }
            raise

        # Find the last ToolMessage — that is the raw renderer output
        # (base64 PNG or file:// path). Surface it as the final AI message
        # so the API layer can detect the prefix correctly.
        renderer_output = None
        for msg in reversed(all_messages):
            if isinstance(msg, ToolMessage) and has_renderer_output(msg.content):
                renderer_output = msg.content
                break

        if renderer_output:
            # Replace the last message with an AIMessage carrying the raw output
            final_messages = list(all_messages) + [AIMessage(content=renderer_output)]
        else:
            request_text = latest_human_text(all_messages)
            fallback_output = render_fallback_visualization(
                request_text=request_text,
                messages=all_messages,
                renderer_registry=renderer_registry,
                default_data_loader=default_data_loader,
            )
            if fallback_output:
                final_messages = list(all_messages) + [AIMessage(content=fallback_output)]
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
