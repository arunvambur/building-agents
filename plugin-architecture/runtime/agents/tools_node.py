from langchain_core.messages import ToolMessage
import json


class ToolsNode:

    def __init__(self, tools):

        self.tools = {

            t.name: t for t in tools

        }


    def __call__(self, state):

        last_message = state["messages"][-1]

        tool_calls = getattr(last_message, "tool_calls", [])

        results = []

        for call in tool_calls:

            tool = self.tools.get(call["name"])

            if not tool:
                continue

            try:

                result = tool.invoke(call["args"])

            except Exception as e:

                result = {"error": str(e)}

            results.append(

                ToolMessage(

                    content=json.dumps(result),

                    name=call["name"],

                    tool_call_id=call["id"]

                )

            )

        return {

            "messages": results

        }