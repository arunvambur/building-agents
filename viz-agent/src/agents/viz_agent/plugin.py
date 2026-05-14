import logging
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agents.viz_agent.prompt import VIZ_AGENT_SYSTEM_PROMPT
from core.plugin.interfaces import AgentPlugin
from core.tools_node import ToolsNode

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class VizAgentPlugin(AgentPlugin):
    name = "viz_agent"

    def build_graph(self, llm, tools: list, checkpointer=None):
        tool_names = [t.name for t in tools]
        logger.info("[viz_agent] building graph — tools: %s", tool_names)
        llm_with_tools = llm.bind_tools(tools)

        def llm_node(state: AgentState) -> dict:
            messages = state["messages"]
            if not any(m.type == "system" for m in messages):
                messages = [SystemMessage(content=VIZ_AGENT_SYSTEM_PROMPT)] + messages
            logger.debug("[viz_agent:llm] invoking LLM — %d messages", len(messages))
            response = llm_with_tools.invoke(messages)
            tool_calls = getattr(response, "tool_calls", [])
            if tool_calls:
                logger.info("[viz_agent:llm] tool calls requested: %s", [tc["name"] for tc in tool_calls])
                for tc in tool_calls:
                    args_preview = str(tc.get("args", {}))[:200]
                    logger.debug("[viz_agent:llm] tool call args (%s): %s", tc["name"], args_preview)
            else:
                logger.warning("[viz_agent:llm] no tool calls made — LLM responded with text instead of calling render_visualization")
                logger.debug("[viz_agent:llm] response content: %r", getattr(response, "content", "")[:200])
            return {"messages": [response]}

        def route(state: AgentState) -> str:
            last = state["messages"][-1]
            has_tools = bool(getattr(last, "tool_calls", None))
            logger.debug("[viz_agent:route] → %s", "tools" if has_tools else "END")
            return "tools" if has_tools else END

        builder = StateGraph(AgentState)
        builder.add_node("llm", llm_node)
        builder.add_node("tools", ToolsNode(tools))
        builder.add_conditional_edges("llm", route)
        builder.add_edge("tools", "llm")
        builder.set_entry_point("llm")

        return builder.compile(checkpointer=checkpointer)
