from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class GuardrailDecision(BaseModel):
    is_travel: bool = Field(...)
    reason: str = Field(...)


class TravelGuardrailPlugin:

    def __init__(self, llm):
        self.guardrail = llm.with_structured_output(GuardrailDecision)

    def validate(self, state):
        messages = state.get("messages", [])
        last = messages[-1]

        if not isinstance(last, HumanMessage):
            return True, None

        result = self.guardrail.invoke([
            SystemMessage(content="Classify if travel-related"),
            HumanMessage(content=last.content)
        ])

        if result.is_travel:
            return True, None

        return False, "I can only answer travel-related questions."