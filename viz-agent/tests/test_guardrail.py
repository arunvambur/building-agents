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


def test_viz_related_query_is_allowed():
    guardrail = _make_guardrail(is_viz_related=True)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="Show me a bar chart")]})
    assert allowed is True
    assert msg is None


def test_non_viz_query_is_blocked():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [HumanMessage(content="What is the weather?")]})
    assert allowed is False
    assert isinstance(msg, AIMessage)
    assert "visualization" in msg.content.lower()


def test_non_human_message_is_always_allowed():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": [AIMessage(content="some response")]})
    assert allowed is True
    assert msg is None


def test_empty_messages_is_allowed():
    guardrail = _make_guardrail(is_viz_related=False)
    allowed, msg = guardrail.validate({"messages": []})
    assert allowed is True
    assert msg is None
