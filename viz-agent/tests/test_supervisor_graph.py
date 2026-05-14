"""
Tests for agents/supervisor/graph.py — orchestration logic, routing, and fallback injection.
"""
import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.supervisor.graph import build_supervisor_graph
from core.renderer.registry import RendererRegistry


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

class _FakeRenderer:
    name = "image"

    def supports(self, fmt: str) -> bool:
        return fmt in {"image", "excel"}

    def render(self, spec, data) -> str:
        if spec.output == "excel":
            return "file:///tmp/fake.xlsx"
        return "data:image/png;base64,fake"


def _registry() -> RendererRegistry:
    r = RendererRegistry()
    r.register(_FakeRenderer())
    return r


def _fake_data_graph(extra_messages=None):
    """Data agent that returns a ToolMessage with JSON rows."""
    rows = [{"town": "St Ives", "rating": 4.8}]

    def _invoke(state):
        msgs = list(state["messages"])
        tool_call_id = "tc-001"
        msgs.append(AIMessage(
            content="",
            tool_calls=[{"name": "list_all_hotels_with_offers", "args": {}, "id": tool_call_id}],
        ))
        msgs.append(ToolMessage(
            content=json.dumps(rows),
            name="list_all_hotels_with_offers",
            tool_call_id=tool_call_id,
        ))
        if extra_messages:
            msgs.extend(extra_messages)
        return {"messages": msgs}

    return _invoke


def _fake_viz_graph(output: str = "data:image/png;base64,fake"):
    """Viz agent that returns a ToolMessage with a renderer output."""
    def _invoke(state):
        msgs = list(state["messages"])
        tool_call_id = "tc-002"
        msgs.append(AIMessage(
            content="",
            tool_calls=[{"name": "render_visualization", "args": {}, "id": tool_call_id}],
        ))
        msgs.append(ToolMessage(
            content=output,
            name="render_visualization",
            tool_call_id=tool_call_id,
        ))
        msgs.append(AIMessage(content=output))
        return {"messages": msgs}

    return _invoke


class _FakeGraph:
    def __init__(self, fn):
        self._fn = fn

    def invoke(self, state):
        return self._fn(state)


class _FailingGraph:
    def invoke(self, state):
        raise RuntimeError("model unavailable")


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

def test_routes_to_data_agent_first():
    """Supervisor must call data_agent before viz_agent."""
    call_order = []

    def data_fn(state):
        call_order.append("data")
        return {"messages": list(state["messages"]) + [AIMessage(content="done")]}

    def viz_fn(state):
        call_order.append("viz")
        return {"messages": list(state["messages"]) + [AIMessage(content="data:image/png;base64,x")]}

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(data_fn),
        viz_agent_graph=_FakeGraph(viz_fn),
    )
    graph.invoke({"messages": [HumanMessage(content="show a chart")]})
    assert call_order == ["data", "viz"]


def test_pipeline_flags_reset_on_new_human_message():
    """A second human message in the same thread must re-run the full pipeline."""
    call_counts = {"data": 0, "viz": 0}

    def data_fn(state):
        call_counts["data"] += 1
        return {"messages": list(state["messages"]) + [AIMessage(content="done")]}

    def viz_fn(state):
        call_counts["viz"] += 1
        return {"messages": list(state["messages"]) + [AIMessage(content="data:image/png;base64,x")]}

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(data_fn),
        viz_agent_graph=_FakeGraph(viz_fn),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "reset-test"}}

    graph.invoke({"messages": [HumanMessage(content="first query")]}, config=config)
    graph.invoke({"messages": [HumanMessage(content="second query")]}, config=config)

    assert call_counts["data"] == 2
    assert call_counts["viz"] == 2


# ---------------------------------------------------------------------------
# Renderer output detection
# ---------------------------------------------------------------------------

def test_image_output_promoted_to_final_ai_message():
    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(_fake_data_graph()),
        viz_agent_graph=_FakeGraph(_fake_viz_graph("data:image/png;base64,abc123")),
    )
    result = graph.invoke({"messages": [HumanMessage(content="show a bar chart")]})
    assert result["messages"][-1].content == "data:image/png;base64,abc123"


def test_file_output_promoted_to_final_ai_message():
    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(_fake_data_graph()),
        viz_agent_graph=_FakeGraph(_fake_viz_graph("file:///tmp/report.xlsx")),
    )
    result = graph.invoke({"messages": [HumanMessage(content="generate excel")]})
    assert result["messages"][-1].content == "file:///tmp/report.xlsx"


def test_no_renderer_output_returns_last_message_as_is():
    """When viz agent produces no renderer output, the last message is returned unchanged."""
    def viz_fn(state):
        return {"messages": list(state["messages"]) + [AIMessage(content="I could not render that.")]}

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(_fake_data_graph()),
        viz_agent_graph=_FakeGraph(viz_fn),
    )
    result = graph.invoke({"messages": [HumanMessage(content="show a chart")]})
    assert result["messages"][-1].content == "I could not render that."


# ---------------------------------------------------------------------------
# Fallback injection
# ---------------------------------------------------------------------------

def test_fallback_data_injected_when_data_agent_returns_no_tool_messages():
    """When data_agent returns no ToolMessages, default_data_loader rows are injected."""
    fallback_rows = [{"town": "Newquay", "rating": 4.2}]

    def data_fn(state):
        # Returns only an AIMessage — no ToolMessage
        return {"messages": list(state["messages"]) + [AIMessage(content="No data found")]}

    captured = {}

    def viz_fn(state):
        # Capture what the viz agent received
        captured["messages"] = state["messages"]
        return {"messages": list(state["messages"]) + [AIMessage(content="data:image/png;base64,ok")]}

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(data_fn),
        viz_agent_graph=_FakeGraph(viz_fn),
        default_data_loader=lambda: fallback_rows,
    )
    graph.invoke({"messages": [HumanMessage(content="show a chart")]})

    tool_msgs = [m for m in captured["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert json.loads(tool_msgs[0].content) == fallback_rows


def test_fallback_not_injected_when_tool_data_present():
    """When data_agent returns ToolMessages, default_data_loader must NOT be called."""
    loader_called = []

    def data_fn(state):
        return _fake_data_graph()(state)

    captured = {}

    def viz_fn(state):
        captured["messages"] = state["messages"]
        return {"messages": list(state["messages"]) + [AIMessage(content="data:image/png;base64,ok")]}

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(data_fn),
        viz_agent_graph=_FakeGraph(viz_fn),
        default_data_loader=lambda: loader_called.append(True) or [],
    )
    graph.invoke({"messages": [HumanMessage(content="show a chart")]})
    assert loader_called == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_data_agent_error_propagates():
    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FailingGraph(),
        viz_agent_graph=_FakeGraph(_fake_viz_graph()),
    )
    with pytest.raises(RuntimeError, match="model unavailable"):
        graph.invoke({"messages": [HumanMessage(content="show a chart")]})


def test_viz_agent_error_propagates():
    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FakeGraph(_fake_data_graph()),
        viz_agent_graph=_FailingGraph(),
    )
    with pytest.raises(RuntimeError, match="model unavailable"):
        graph.invoke({"messages": [HumanMessage(content="show a chart")]})
