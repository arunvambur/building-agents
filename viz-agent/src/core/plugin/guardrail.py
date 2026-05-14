import re
from typing import Any, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from core.plugin.interfaces import GuardrailPlugin


# Fast-pass keywords — if any match, skip the LLM call entirely and allow.
# Covers the core vocabulary of this application.
_ALLOW_PATTERNS = re.compile(
    r"\b("
    r"chart|graph|plot|bar|line|scatter|pie|histogram|dashboard|visuali[sz]|"
    r"excel|spreadsheet|report|export|download|file|xlsx|"
    r"hotel|hotels|room|rooms|price|pricing|rating|ratings|town|towns|"
    r"data|dataset|query|fetch|show|list|find|get|generate|create|display|"
    r"cornwall|newquay|falmouth|penzance|padstow|st\s+ives|bude|hayle|camborne"
    r")\b",
    re.IGNORECASE,
)

_BLOCK_MESSAGE = (
    "I can only answer questions about hotel data, visualizations, charts, "
    "and Excel reports. Please ask something related to those topics."
)


class GuardrailDecision(BaseModel):
    is_viz_related: bool = Field(
        ...,
        description=(
            "True if the query is related to: hotels, rooms, pricing, ratings, towns, "
            "data visualization, charts, graphs, Excel reports, data querying, or data rendering. "
            "Be PERMISSIVE — only return False for completely unrelated topics like weather, "
            "cooking, sports, politics, etc."
        ),
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

        content = last.content.strip()

        # Fast-pass: keyword match → allow immediately without LLM call
        if _ALLOW_PATTERNS.search(content):
            return True, None

        # Fallback: ask the LLM for ambiguous queries
        result: GuardrailDecision = self.guardrail.invoke([
            SystemMessage(
                content=(
                    "You are a permissive content filter for a hotel data visualization assistant. "
                    "Allow any query related to: hotels, rooms, pricing, availability, ratings, towns, "
                    "charts, graphs, bar charts, line charts, pie charts, scatter plots, dashboards, "
                    "Excel files, spreadsheets, reports, data queries, or data visualization. "
                    "Only block queries that are COMPLETELY unrelated to hotels or data visualization "
                    "(e.g. weather forecasts, recipes, sports scores, political news). "
                    "When in doubt, ALLOW the query."
                )
            ),
            HumanMessage(content=content),
        ])

        if result.is_viz_related:
            return True, None

        return False, AIMessage(content=_BLOCK_MESSAGE)

    async def avalidate(self, state: dict) -> Tuple[bool, Optional[AIMessage]]:
        messages = state.get("messages", [])
        if not messages:
            return True, None

        last = messages[-1]
        if not isinstance(last, HumanMessage):
            return True, None

        content = last.content.strip()

        # Fast-pass: no LLM call needed
        if _ALLOW_PATTERNS.search(content):
            return True, None

        # Async LLM call — does not block the event loop
        result: GuardrailDecision = await self.guardrail.ainvoke([
            SystemMessage(
                content=(
                    "You are a permissive content filter for a hotel data visualization assistant. "
                    "Allow any query related to: hotels, rooms, pricing, availability, ratings, towns, "
                    "charts, graphs, bar charts, line charts, pie charts, scatter plots, dashboards, "
                    "Excel files, spreadsheets, reports, data queries, or data visualization. "
                    "Only block queries that are COMPLETELY unrelated to hotels or data visualization "
                    "(e.g. weather forecasts, recipes, sports scores, political news). "
                    "When in doubt, ALLOW the query."
                )
            ),
            HumanMessage(content=content),
        ])

        if result.is_viz_related:
            return True, None

        return False, AIMessage(content=_BLOCK_MESSAGE)

