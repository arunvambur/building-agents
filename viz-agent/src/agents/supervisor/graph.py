import logging
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agents.supervisor.formatting import (
    extract_records_from_tool_messages,
    format_table,
    get_user_text,
    last_ai_content,
    wants_csv,
    write_csv,
)
from agents.supervisor.intent import IntentType, build_intent_classifier

logger = logging.getLogger(__name__)


class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent:   str        # "data" | "viz" | "both" | ""
    data_ready: bool
    viz_ready:  bool


def build_supervisor_graph(
    llm: Any,
    data_agent_graph: Any,
    viz_agent_graph: Any,
    checkpointer: Optional[Any] = None,
    renderer_registry: Optional[Any] = None,
    default_data_loader: Optional[Any] = None,
) -> Any:

    classify_intent = build_intent_classifier(llm)

    # ------------------------------------------------------------------ #
    # intent_node                                                           #
    # ------------------------------------------------------------------ #
    def intent_node(state: SupervisorState) -> dict:
        last = state["messages"][-1] if state["messages"] else None
        text = getattr(last, "content", "") if isinstance(last, HumanMessage) else ""
        intent = classify_intent(text)
        logger.info("[intent] '%s' → %s", text[:80], intent.value)
        return {"intent": intent.value, "data_ready": False, "viz_ready": False}

    # ------------------------------------------------------------------ #
    # supervisor_node                                                        #
    # ------------------------------------------------------------------ #
    def supervisor_node(state: SupervisorState) -> dict:
        intent     = state.get("intent", "data")
        data_ready = state.get("data_ready", False)
        viz_ready  = state.get("viz_ready", False)

        if intent == IntentType.data:
            if not data_ready:
                logger.info("[supervisor] intent=data → data_agent")
                return {"next": "data_agent"}
            logger.info("[supervisor] intent=data, data ready → FINISH")
            return {"next": "FINISH"}

        if not data_ready:
            logger.info("[supervisor] intent=%s → data_agent", intent)
            return {"next": "data_agent"}

        if not viz_ready:
            logger.info("[supervisor] intent=%s, data ready → viz_agent", intent)
            return {"next": "viz_agent"}

        logger.info("[supervisor] pipeline complete → FINISH")
        return {"next": "FINISH"}

    # ------------------------------------------------------------------ #
    # data_agent_node                                                        #
    # ------------------------------------------------------------------ #
    def data_agent_node(state: SupervisorState) -> dict:
        logger.info("[data_agent] starting — message count: %d", len(state["messages"]))

        result = data_agent_graph.invoke({"messages": state["messages"]})
        agent_messages = list(result["messages"])
        logger.info("[data_agent] completed — returned %d messages", len(agent_messages))

        for msg in agent_messages:
            if isinstance(msg, ToolMessage):
                logger.debug("[data_agent] tool result (%s): %s",
                             msg.name, msg.content[:120].replace("\n", " "))

        intent = state.get("intent", "data")

        if intent == IntentType.data:
            # Detect CSV intent from the original user message in state
            user_text = get_user_text(state["messages"])
            csv_requested = wants_csv(user_text)

            # Extract records directly from ToolMessages — bypass the LLM's
            # final AIMessage which may reformat the data as JSON text.
            records = extract_records_from_tool_messages(agent_messages)

            if records is not None:
                if isinstance(records, str):
                    formatted = records                          # error string
                elif csv_requested:
                    formatted = write_csv(records)
                    logger.info("[data_agent] CSV written — %d records", len(records))
                else:
                    formatted = format_table(records)
                    logger.info("[data_agent] table formatted — %d records", len(records))

                # Return only the formatted AIMessage — prevents the LLM's
                # JSON summary from leaking through as the final response.
                return {
                    "messages": [AIMessage(content=formatted)],
                    "data_ready": True,
                }

            # No tool results — fall back to the agent's last AIMessage
            fallback = last_ai_content(agent_messages)
            if fallback:
                return {
                    "messages": [AIMessage(content=fallback)],
                    "data_ready": True,
                }

        return {"messages": agent_messages, "data_ready": True}

    # ------------------------------------------------------------------ #
    # viz_agent_node                                                         #
    # ------------------------------------------------------------------ #
    def viz_agent_node(state: SupervisorState) -> dict:
        logger.info("[viz_agent] starting — message count: %d", len(state["messages"]))

        result = viz_agent_graph.invoke({"messages": state["messages"]})
        all_messages = result["messages"]
        logger.info("[viz_agent] completed — returned %d messages", len(all_messages))

        for msg in all_messages:
            if isinstance(msg, ToolMessage):
                logger.debug("[viz_agent] tool result (%s): %s",
                             msg.name, msg.content[:120].replace("\n", " "))

        renderer_output = None
        for msg in reversed(all_messages):
            if isinstance(msg, ToolMessage):
                c = msg.content
                if c.startswith("data:image/png;base64,") or c.startswith("file://"):
                    renderer_output = c
                    logger.info("[viz_agent] renderer output detected — type: %s, length: %d",
                                "image" if c.startswith("data:") else "file", len(c))
                    break

        if renderer_output:
            final_messages = list(all_messages) + [AIMessage(content=renderer_output)]
        else:
            logger.warning("[viz_agent] no renderer output found — returning last message as-is")
            logger.debug("[viz_agent] last content: %r",
                         getattr(all_messages[-1], "content", "")[:200] if all_messages else "")
            final_messages = list(all_messages)

        return {"messages": final_messages, "viz_ready": True}

    # ------------------------------------------------------------------ #
    # routing                                                               #
    # ------------------------------------------------------------------ #
    def route_supervisor(state: SupervisorState) -> str:
        next_step = state.get("next", "FINISH")
        if next_step == "data_agent":
            return "data_agent"
        if next_step == "viz_agent":
            return "viz_agent"
        return END

    def route_entry(state: SupervisorState) -> str:
        last = state["messages"][-1] if state["messages"] else None
        data_ready = state.get("data_ready", False)
        viz_ready  = state.get("viz_ready", False)
        if isinstance(last, HumanMessage) and not data_ready and not viz_ready:
            return "intent"
        return "supervisor"

    # ------------------------------------------------------------------ #
    # graph assembly                                                         #
    # ------------------------------------------------------------------ #
    builder = StateGraph(SupervisorState)
    builder.add_node("intent",     intent_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("data_agent", data_agent_node)
    builder.add_node("viz_agent",  viz_agent_node)

    builder.set_conditional_entry_point(route_entry)
    builder.add_edge("intent", "supervisor")
    builder.add_conditional_edges("supervisor", route_supervisor)
    builder.add_edge("data_agent", "supervisor")
    builder.add_edge("viz_agent",  "supervisor")

    return builder.compile(checkpointer=checkpointer)
