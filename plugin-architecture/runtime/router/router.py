from langchain.messages import HumanMessage, SystemMessage
from runtime.core.interfaces import RouterPlugin


class LLMRouter(RouterPlugin):

    def __init__(self, llm, schema):
        self.router = llm.with_structured_output(schema)

    def route(self, state):
        last = state["messages"][-1]

        if not isinstance(last, HumanMessage):
            return "travel_info_agent"

        response = self.router.invoke([
            SystemMessage(content="Route travel vs booking"),
            HumanMessage(content=last.content)
        ])

        return response.agent.value
