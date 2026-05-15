"""
Intent classification for the supervisor.

Classifies user messages into one of three intents:
  - "data"  : user wants data queried and returned as text (no chart/file)
  - "viz"   : user wants a visualization, chart, or file output
  - "both"  : user wants data AND a visualization

Uses a two-layer approach:
  1. Keyword fast-classifier — no LLM call, covers the common cases
  2. LLM structured-output fallback — for ambiguous queries
"""

import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    data = "data"
    viz  = "viz"
    both = "both"


class IntentOutput(BaseModel):
    intent: IntentType = Field(
        ...,
        description=(
            "Classify the user query:\n"
            "  'data' — user wants to query, list, find, or summarize hotel data as text "
            "(e.g. 'which hotels have rooms?', 'what is the cheapest hotel?', 'list all hotels').\n"
            "  'viz'  — user wants a chart, graph, image, Excel file, PDF, or PowerPoint "
            "(e.g. 'show me a bar chart', 'generate an Excel report', 'create a pie chart').\n"
            "  'both' — user wants data AND a visualization in the same request "
            "(e.g. 'list hotels and show a chart', 'find hotels in St Ives and plot ratings')."
        ),
    )
    reason: str = Field(..., description="One-sentence reason for the classification.")


# ---- keyword patterns ----

_VIZ_PATTERN = re.compile(
    r"\b("
    r"chart|graph|plot|bar|line|scatter|pie|donut|histogram|heatmap|bubble|waterfall|gauge|"
    r"visuali[sz]e?|dashboard|image|png|picture|diagram|"
    r"excel|spreadsheet|xlsx|pdf|powerpoint|pptx|presentation|slides|report|export|download|"
    r"csv|comma.separated"
    r")\b",
    re.IGNORECASE,
)

_CSV_PATTERN = re.compile(
    r"\b(csv|comma[ -]separated|download\s+csv|as\s+csv)\b",
    re.IGNORECASE,
)

_DATA_PATTERN = re.compile(
    r"\b("
    r"list|find|show|get|fetch|query|search|which|what|who|where|how many|"
    r"tell me|give me|display|summarize|describe|compare|cheapest|expensive|"
    r"available|availability|book|rooms|hotel|hotels|price|pricing|rating|ratings|"
    r"town|towns|cornwall|newquay|falmouth|penzance|padstow|st\s+ives|bude|hayle|camborne"
    r")\b",
    re.IGNORECASE,
)

_BOTH_PATTERN = re.compile(
    r"("
    r"\b(?:list|find|show|get|fetch|query|search|display|give me|return)\b"
    r".*\b(?:and|also|plus|with)\b"
    r".*\b(?:chart|graph|plot|visuali[sz]e?|excel|spreadsheet|xlsx|pdf|powerpoint|pptx|report|export)\b"
    r"|"
    r"\b(?:chart|graph|plot|visuali[sz]e?|excel|spreadsheet|xlsx|pdf|powerpoint|pptx|report|export)\b"
    r".*\b(?:and|also|plus|with)\b"
    r".*\b(?:list|table|data|rows|records|hotels?)\b"
    r")",
    re.IGNORECASE,
)


def classify_intent_fast(text: str) -> IntentType | None:
    """
    Keyword-based fast classifier. Returns None if ambiguous (needs LLM).
    """
    if _CSV_PATTERN.search(text):
        return IntentType.data

    has_viz  = bool(_VIZ_PATTERN.search(text))
    has_data = bool(_DATA_PATTERN.search(text))

    if has_viz and has_data:
        return IntentType.both if _BOTH_PATTERN.search(text) else IntentType.viz
    if has_viz:
        return IntentType.viz
    if has_data:
        return IntentType.data
    return None  # ambiguous — fall through to LLM


def build_intent_classifier(llm: Any):
    """Returns a callable that classifies intent using the LLM."""
    classifier = llm.with_structured_output(IntentOutput)

    def classify(text: str) -> IntentType:
        fast = classify_intent_fast(text)
        if fast is not None:
            logger.debug("[intent] fast-classified as '%s': %r", fast.value, text[:60])
            return fast

        logger.debug("[intent] LLM classifying: %r", text[:60])
        result: IntentOutput = classifier.invoke(text)
        logger.info("[intent] LLM classified as '%s' (%s)", result.intent.value, result.reason)
        return result.intent

    return classify
