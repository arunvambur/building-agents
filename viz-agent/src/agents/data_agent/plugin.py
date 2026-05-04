import json

from langchain.messages import SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from runtime.agents.tools_node import ToolsNode
from runtime.core.interfaces import AgentPlugin

class DataAgentPlugin(AgentPlugin):
    name = "data_intelligent_agent"

    def build_graph(self, llm, tools, checkpointer=None):
        llm_with_tools = llm.bind_tools(tools)

        def llm_node(state):

            system_message = SystemMessage(content="Travel assistant")

            # IMPORTANT: preserve conversation history
            messages = state["messages"]

            # prepend system message only once
            if not any(m.type == "system" for m in messages):
                messages = [system_message] + messages

            response = llm_with_tools.invoke(messages)

            return {"messages": [response]}

        def route(state):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder = StateGraph(dict)
        builder.add_node("llm", llm_node)
        builder.add_node("tools", ToolsNode(tools))

        builder.add_conditional_edges("llm", route)
        builder.add_edge("tools", "llm")
        builder.set_entry_point("llm")

        return builder.compile()