from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from core.plugin.guardrail import GuardrailDecision, VizGuardrailPlugin


def _make_guardrail(is_viz_related: bool) -> VizGuardrailPlugin:
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = GuardrailDecision(
        is_viz_related=is_viz_related,
        reason="test",
    )
    return VizGuardrailPlugin(mock_llm)


# ---- Fast-pass keyword tests (LLM never called) ----

def test_bar_chart_keyword_fast_pass():
    guardrail = _make_guardrail(is_viz_related=False)  # LLM would block, but fast-pass wins
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Show me a bar chart")]})
    assert allowed is True
    assert msg is None


def test_excel_keyword_fast_pass():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Generate an Excel report of all hotels with pricing")]})
    assert allowed is True
    assert msg is None


def test_hotel_keyword_fast_pass():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Which hotels in St Ives have rooms?")]})
    assert allowed is True
    assert msg is None


def test_ratings_keyword_fast_pass():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Show hotel ratings by town as image")]})
    assert allowed is True
    assert msg is None


# ---- LLM fallback tests ----

def test_llm_allows_viz_related_query():
    guardrail = _make_guardrail(is_viz_related=True)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Something ambiguous but viz related")]})
    assert allowed is True
    assert msg is None


def test_llm_blocks_unrelated_query():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="What is the weather in London?")]})
    assert allowed is False
    assert isinstance(msg, AIMessage)
    assert "visualization" in msg.content.lower() or "hotel" in msg.content.lower()


# ---- Edge cases ----

def test_non_human_message_always_allowed():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [AIMessage(content="some response")]})
    assert allowed is True
    assert msg is None


def test_empty_messages_allowed():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": []})
    assert allowed is True
    assert msg is None
