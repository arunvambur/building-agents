import json

from langchain_core.messages import ToolMessage


class ToolsNode:
    """Executes tool calls from the last LLM message and returns ToolMessages."""

    def __init__(self, tools: list):
        self.tools = {t.name: t for t in tools}

    def __call__(self, state: dict) -> dict:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        results = []
        for call in tool_calls:
            tool = self.tools.get(call["name"])
            if not tool:
                results.append(
                    ToolMessage(
                        content=json.dumps({"error": f"Unknown tool: {call['name']}"}),
                        name=call["name"],
                        tool_call_id=call["id"],
                    )
                )
                continue

            try:
                result = tool.invoke(call["args"])
            except Exception as e:
                result = {"error": str(e)}

            results.append(
                ToolMessage(
                    content=json.dumps(result) if not isinstance(result, str) else result,
                    name=call["name"],
                    tool_call_id=call["id"],
                )
            )

        return {"messages": results}
