from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agents.viz_agent.prompt import VIZ_AGENT_SYSTEM_PROMPT
from core.plugin.interfaces import AgentPlugin
from core.tools_node import ToolsNode


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class VizAgentPlugin(AgentPlugin):
    name = "viz_agent"

    def build_graph(self, llm, tools: list, checkpointer=None):
        llm_with_tools = llm.bind_tools(tools)

        def llm_node(state: AgentState) -> dict:
            messages = state["messages"]
            if not any(m.type == "system" for m in messages):
                messages = [SystemMessage(content=VIZ_AGENT_SYSTEM_PROMPT)] + messages
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def route(state: AgentState) -> str:
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder = StateGraph(AgentState)
        builder.add_node("llm", llm_node)
        builder.add_node("tools", ToolsNode(tools))
        builder.add_conditional_edges("llm", route)
        builder.add_edge("tools", "llm")
        builder.set_entry_point("llm")

        return builder.compile(checkpointer=checkpointer)
