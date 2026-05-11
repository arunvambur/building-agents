from typing import Any, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from core.plugin.interfaces import GuardrailPlugin


class GuardrailDecision(BaseModel):
    is_viz_related: bool = Field(
        ..., description="True if the query is related to data visualization, charts, or data querying."
    )
    reason: str = Field(..., description="Brief reason for the decision.")


class VizGuardrailPlugin(GuardrailPlugin):

    def __init__(self, llm: Any):
        self.guardrail = llm.with_structured_output(GuardrailDecision)

    def validate(self, state: dict) -> Tuple[bool, Optional[AIMessage]]:
        messages = state.get("messages", [])
        if not messages:
            return True, None

        last = messages[-1]
        if not isinstance(last, HumanMessage):
            return True, None

        result: GuardrailDecision = self.guardrail.invoke([
            SystemMessage(
                content=(
                    "Classify whether the user query is related to data visualization, "
                    "charts, graphs, dashboards, data querying, or data rendering. "
                    "Return is_viz_related=True if it is, False otherwise."
                )
            ),
            HumanMessage(content=last.content),
        ])

        if result.is_viz_related:
            return True, None

        return False, AIMessage(content="I can only answer visualization and data-related questions.")
