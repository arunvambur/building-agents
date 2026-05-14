import json
import logging
from typing import Annotated, Any, Callable, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agents.supervisor.fallback import (
    is_visualization_request,
    latest_human_text,
    render_fallback_visualization,
)

logger = logging.getLogger(__name__)


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

    def supervisor_node(state: SupervisorState) -> dict:
        data_ready = state.get("data_ready", False)
        viz_ready = state.get("viz_ready", False)
        last_message = state["messages"][-1] if state.get("messages") else None
        request_text = latest_human_text(state["messages"])

        # Reset flags if a new human message arrives mid-session
        if (
            getattr(last_message, "type", None) == "human"
            and (data_ready or viz_ready)
        ):
            logger.info("[supervisor] new human message — resetting pipeline flags")
            if _can_render_direct(request_text):
                logger.info("[supervisor] routing → direct_renderer")
                return {"next": "direct_renderer", "data_ready": False, "viz_ready": False}
            return {"next": "data_agent", "data_ready": False, "viz_ready": False}

        if not data_ready:
            if _can_render_direct(request_text):
                logger.info("[supervisor] routing → direct_renderer")
                return {"next": "direct_renderer"}
            logger.info("[supervisor] routing → data_agent")
            return {"next": "data_agent"}

        if not is_visualization_request(request_text):
            logger.info("[supervisor] data-only request complete → FINISH")
            return {"next": "FINISH"}

        if not viz_ready:
            logger.info("[supervisor] routing → viz_agent")
            return {"next": "viz_agent"}

        logger.info("[supervisor] pipeline complete → FINISH")
        return {"next": "FINISH"}

    def _can_render_direct(request_text: str) -> bool:
        return bool(renderer_registry and default_data_loader and is_visualization_request(request_text))

    def direct_renderer_node(state: SupervisorState) -> dict:
        request_text = latest_human_text(state["messages"])
        logger.info("[direct_renderer] starting")
        output = render_fallback_visualization(
            request_text,
            state["messages"],
            renderer_registry,
            default_data_loader,
        )
        if not output:
            logger.warning("[direct_renderer] no output — falling back to data_agent")
            return {"next": "data_agent", "data_ready": False, "viz_ready": False}
        logger.info("[direct_renderer] completed — output length: %d", len(output))
        return {
            "messages": [AIMessage(content=output)],
            "data_ready": True,
            "viz_ready": True,
        }

    def data_agent_node(state: SupervisorState) -> dict:
        logger.info("[data_agent] starting — message count: %d", len(state["messages"]))
        try:
            result = data_agent_graph.invoke({"messages": state["messages"]})
            messages = list(result["messages"])
            logger.info("[data_agent] completed — returned %d messages", len(messages))

            # Log tool calls made
            for msg in messages:
                if isinstance(msg, ToolMessage):
                    preview = msg.content[:120].replace("\n", " ")
                    logger.debug("[data_agent] tool result (%s): %s", msg.name, preview)

        except Exception as e:
            logger.error("[data_agent] error: %s", e, exc_info=True)
            fallback_output = render_fallback_visualization(
                latest_human_text(state["messages"]),
                state["messages"],
                renderer_registry,
                default_data_loader,
            )
            if fallback_output:
                logger.warning("[data_agent] rendered fallback output after data agent error")
                return {
                    "messages": [AIMessage(content=fallback_output)],
                    "data_ready": True,
                    "viz_ready": True,
                }
            raise

        # Fallback: if no tool results found, inject default hotel data
        has_tool_data = any(isinstance(m, ToolMessage) for m in messages)
        if not has_tool_data and default_data_loader:
            logger.warning("[data_agent] no tool results found — injecting fallback hotel data")
            data = default_data_loader()
            tool_call_id = "fallback-list-all-hotels"
            messages.extend([
                AIMessage(
                    content="",
                    tool_calls=[{"name": "list_all_hotels_with_offers", "args": {}, "id": tool_call_id}],
                ),
                ToolMessage(
                    content=json.dumps(data),
                    name="list_all_hotels_with_offers",
                    tool_call_id=tool_call_id,
                ),
            ])
            logger.info("[data_agent] fallback data injected — %d records", len(data))

        if not is_visualization_request(latest_human_text(state["messages"])):
            data_response = _data_response_message(messages)
            if data_response:
                messages.append(data_response)

        return {"messages": messages, "data_ready": True}

    def viz_agent_node(state: SupervisorState) -> dict:
        logger.info("[viz_agent] starting — message count: %d", len(state["messages"]))
        try:
            result = viz_agent_graph.invoke({"messages": state["messages"]})
            all_messages = result["messages"]
            logger.info("[viz_agent] completed — returned %d messages", len(all_messages))

            # Log tool calls made by viz agent
            for msg in all_messages:
                if isinstance(msg, ToolMessage):
                    preview = msg.content[:120].replace("\n", " ")
                    logger.debug("[viz_agent] tool result (%s): %s", msg.name, preview)

        except Exception as e:
            logger.error("[viz_agent] error: %s", e, exc_info=True)
            fallback_output = render_fallback_visualization(
                latest_human_text(state["messages"]),
                state["messages"],
                renderer_registry,
                default_data_loader,
            )
            if fallback_output:
                logger.warning("[viz_agent] rendered fallback output after viz agent error")
                return {
                    "messages": [AIMessage(content=fallback_output)],
                    "viz_ready": True,
                }
            raise

        # Find the last ToolMessage with a renderer output prefix
        renderer_output = None
        for msg in reversed(all_messages):
            if isinstance(msg, ToolMessage):
                c = msg.content
                if c.startswith("data:image/png;base64,") or c.startswith("file://"):
                    renderer_output = c
                    logger.info(
                        "[viz_agent] renderer output detected — type: %s, length: %d",
                        "image" if c.startswith("data:") else "file",
                        len(c),
                    )
                    break

        if renderer_output:
            final_messages = list(all_messages) + [AIMessage(content=renderer_output)]
        else:
            logger.warning("[viz_agent] no renderer output found in tool messages — returning last message as-is")
            last_content = getattr(all_messages[-1], "content", "")[:120] if all_messages else ""
            logger.debug("[viz_agent] last message content: %r", last_content)
            fallback_output = render_fallback_visualization(
                latest_human_text(all_messages),
                all_messages,
                renderer_registry,
                default_data_loader,
            )
            if fallback_output:
                logger.warning("[viz_agent] rendered fallback output after missing renderer output")
                final_messages = list(all_messages) + [AIMessage(content=fallback_output)]
            else:
                final_messages = list(all_messages)

        return {"messages": final_messages, "viz_ready": True}

    def route_supervisor(state: SupervisorState) -> str:
        next_step = state.get("next", "FINISH")
        if next_step == "direct_renderer":
            return "direct_renderer"
        if next_step == "data_agent":
            return "data_agent"
        if next_step == "viz_agent":
            return "viz_agent"
        return END

    def _data_response_message(messages: list[BaseMessage]) -> Optional[AIMessage]:
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                records = _records_from_tool_message(msg)
                if records:
                    return AIMessage(content=_format_data_response(records))
        return None

    def _records_from_tool_message(msg: ToolMessage) -> list[dict]:
        try:
            payload = json.loads(msg.content)
        except (TypeError, json.JSONDecodeError):
            return []
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            if "error" in payload:
                return []
            return [payload]
        return []

    def _format_data_response(records: list[dict]) -> str:
        preview = records[:20]
        payload = {
            "row_count": len(records),
            "columns": list(preview[0].keys()) if preview else [],
            "rows": preview,
            "truncated": len(records) > len(preview),
        }
        return json.dumps(payload, indent=2)

    builder = StateGraph(SupervisorState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("direct_renderer", direct_renderer_node)
    builder.add_node("data_agent", data_agent_node)
    builder.add_node("viz_agent", viz_agent_node)

    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", route_supervisor)
    builder.add_edge("direct_renderer", "supervisor")
    builder.add_edge("data_agent", "supervisor")
    builder.add_edge("viz_agent", "supervisor")

    return builder.compile(checkpointer=checkpointer)
