import json
import logging
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

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
    # kept for signature compatibility — unused in this implementation
    renderer_registry: Optional[Any] = None,
    default_data_loader: Optional[Any] = None,
) -> Any:

    classify_intent = build_intent_classifier(llm)

    # ------------------------------------------------------------------ #
    # intent_node — runs once per new human message                        #
    # ------------------------------------------------------------------ #
    def intent_node(state: SupervisorState) -> dict:
        last = state["messages"][-1] if state["messages"] else None
        text = getattr(last, "content", "") if isinstance(last, HumanMessage) else ""
        intent = classify_intent(text)
        logger.info("[intent] '%s' → %s", text[:80], intent.value)
        return {
            "intent":     intent.value,
            "data_ready": False,
            "viz_ready":  False,
        }

    # ------------------------------------------------------------------ #
    # supervisor_node — routes between agents based on intent + flags      #
    # ------------------------------------------------------------------ #
    def supervisor_node(state: SupervisorState) -> dict:
        intent     = state.get("intent", "data")
        data_ready = state.get("data_ready", False)
        viz_ready  = state.get("viz_ready", False)

        # Data-only intent: run data_agent once, then finish
        if intent == IntentType.data:
            if not data_ready:
                logger.info("[supervisor] intent=data → data_agent")
                return {"next": "data_agent"}
            logger.info("[supervisor] intent=data, data ready → FINISH")
            return {"next": "FINISH"}

        # Viz or both: data_agent first, then viz_agent
        if not data_ready:
            logger.info("[supervisor] intent=%s → data_agent", intent)
            return {"next": "data_agent"}

        if not viz_ready:
            logger.info("[supervisor] intent=%s, data ready → viz_agent", intent)
            return {"next": "viz_agent"}

        logger.info("[supervisor] pipeline complete → FINISH")
        return {"next": "FINISH"}

    # ------------------------------------------------------------------ #
    # data_agent_node                                                       #
    # ------------------------------------------------------------------ #
    def data_agent_node(state: SupervisorState) -> dict:
        logger.info("[data_agent] starting — message count: %d", len(state["messages"]))

        result = data_agent_graph.invoke({"messages": state["messages"]})
        messages = list(result["messages"])
        logger.info("[data_agent] completed — returned %d messages", len(messages))

        for msg in messages:
            if isinstance(msg, ToolMessage):
                logger.debug("[data_agent] tool result (%s): %s",
                             msg.name, msg.content[:120].replace("\n", " "))

        intent = state.get("intent", "data")

        # For data-only intent: format tool results into a readable text response
        if intent == IntentType.data:
            text_response = _build_text_response(messages)
            if text_response:
                logger.info("[data_agent] data-only — appending formatted text response")
                messages = messages + [AIMessage(content=text_response)]

        return {"messages": messages, "data_ready": True}

    # ------------------------------------------------------------------ #
    # viz_agent_node                                                        #
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

        # Find the last ToolMessage carrying a renderer output prefix
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
    def route_after_intent(state: SupervisorState) -> str:
        """Always go to supervisor after intent classification."""
        return "supervisor"

    def route_supervisor(state: SupervisorState) -> str:
        next_step = state.get("next", "FINISH")
        if next_step == "data_agent":
            return "data_agent"
        if next_step == "viz_agent":
            return "viz_agent"
        return END

    def route_entry(state: SupervisorState) -> str:
        """
        Entry point routing:
        - New human message with no intent set → classify intent first
        - Otherwise → go straight to supervisor
        """
        last = state["messages"][-1] if state["messages"] else None
        intent = state.get("intent", "")
        data_ready = state.get("data_ready", False)
        viz_ready = state.get("viz_ready", False)

        # New turn: last message is human and pipeline is idle
        if isinstance(last, HumanMessage) and not data_ready and not viz_ready:
            return "intent"
        return "supervisor"

    # ------------------------------------------------------------------ #
    # helpers                                                               #
    # ------------------------------------------------------------------ #
    def _build_text_response(messages: list[BaseMessage]) -> Optional[str]:
        """
        Extracts the last tool result and returns a structured response:
        - 'table://<json>'  for tabular data (rendered as a table in the UI)
        - 'csv://<path>'    when the user explicitly asked for CSV
        - plain text        for single-record or error responses
        """
        # Detect if the user asked for CSV
        user_text = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                user_text = msg.content.lower()

        wants_csv = any(kw in user_text for kw in ("csv", "comma separated", "comma-separated", "download csv"))

        for msg in reversed(messages):
            if not isinstance(msg, ToolMessage):
                continue
            try:
                payload = json.loads(msg.content)
            except (TypeError, json.JSONDecodeError):
                continue

            if isinstance(payload, dict) and "error" in payload:
                return f"Sorry, I could not retrieve the data: {payload['error']}"

            records: list[dict] = []
            if isinstance(payload, list):
                records = [r for r in payload if isinstance(r, dict)]
            elif isinstance(payload, dict):
                records = [payload]

            if not records:
                continue

            if wants_csv:
                return _write_csv(records)

            return _format_table(records)

        # Fallback: return the last AI message content
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return None


    def _format_table(records: list[dict]) -> str:
        """
        Returns a 'table://<json>' string carrying headers and rows.
        The UI renders this as a styled HTML table.
        Single-record responses are returned as plain key-value text.
        """
        if not records:
            return "No results found."

        if len(records) == 1:
            r = records[0]
            lines = [f"**{k}**: {v}" for k, v in r.items()]
            return "\n".join(lines)

        headers = list(records[0].keys())
        rows = [[str(r.get(h, "")) for h in headers] for r in records]
        payload = json.dumps({"headers": headers, "rows": rows, "count": len(records)})
        return f"table://{payload}"


    def _write_csv(records: list[dict]) -> str:
        """
        Writes records to a temp CSV file and returns a 'csv://<path>' string.
        The API layer registers the file and returns a download URL.
        """
        import csv
        import os
        import tempfile
        import uuid as _uuid

        if not records:
            return "No results found."

        headers = list(records[0].keys())
        path = os.path.join(tempfile.gettempdir(), f"{_uuid.uuid4()}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(records)

        logger.info("[data_agent] CSV written to %s (%d records)", path, len(records))
        return f"csv://{path}"

    # ------------------------------------------------------------------ #
    # graph assembly                                                        #
    # ------------------------------------------------------------------ #
    builder = StateGraph(SupervisorState)

    builder.add_node("intent",     intent_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("data_agent", data_agent_node)
    builder.add_node("viz_agent",  viz_agent_node)

    # Entry: classify intent on new turns, skip on subsequent routing steps
    builder.set_conditional_entry_point(route_entry)

    builder.add_edge("intent", "supervisor")
    builder.add_conditional_edges("supervisor", route_supervisor)
    builder.add_edge("data_agent", "supervisor")
    builder.add_edge("viz_agent",  "supervisor")

    return builder.compile(checkpointer=checkpointer)
