from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.supervisor.fallback import build_fallback_spec
from agents.supervisor.graph import build_supervisor_graph
from core.renderer.registry import RendererRegistry


class _FakeRenderer:
    name = "image"

    def __init__(self):
        self.spec = None
        self.data = None

    def supports(self, format: str) -> bool:
        return format in {"image", "excel"}

    def render(self, spec, data) -> str:
        self.spec = spec
        self.data = data
        if spec.output == "excel":
            return "file:///tmp/fake.xlsx"
        return "data:image/png;base64,fake"


class _FakeGraph:
    def __init__(self, response):
        self._response = response

    def invoke(self, state):
        return self._response(state)


class _FailingGraph:
    def invoke(self, state):
        raise RuntimeError("model unavailable")


def test_fallback_spec_for_ratings_by_town_bar_chart():
    spec = build_fallback_spec(
        "Show me a bar chart of hotel ratings by town",
        [{"town": "St Ives", "rating": 4.8}],
    )

    chart = spec.charts[0]
    assert spec.output == "image"
    assert chart.type == "bar"
    assert chart.x.field == "town"
    assert chart.y.field == "rating"
    assert chart.aggregation.op == "avg"


def test_supervisor_renders_fallback_when_viz_agent_returns_empty_message():
    rows = [
        {"hotel_name": "St Ives Bay Resort", "town": "St Ives", "rating": 4.8},
        {"hotel_name": "Seaview Hotel", "town": "Newquay", "rating": 4.5},
    ]

    renderer = _FakeRenderer()
    renderer_registry = RendererRegistry()
    renderer_registry.register(renderer)

    data_agent_graph = _FakeGraph(
        lambda state: {"messages": list(state["messages"]) + [AIMessage(content="No rows found")]}
    )
    viz_agent_graph = _FakeGraph(
        lambda state: {"messages": list(state["messages"]) + [AIMessage(content="")]}
    )

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=data_agent_graph,
        viz_agent_graph=viz_agent_graph,
        renderer_registry=renderer_registry,
        default_data_loader=lambda: rows,
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="Show me a bar chart of hotel ratings by town")]}
    )

    assert result["messages"][-1].content == "data:image/png;base64,fake"
    assert renderer.data == rows
    assert renderer.spec.charts[0].x.field == "town"
    assert renderer.spec.charts[0].y.field == "rating"


def test_supervisor_renders_fallback_when_model_graph_fails():
    rows = [{"hotel_name": "St Ives Bay Resort", "town": "St Ives", "rating": 4.8}]

    renderer = _FakeRenderer()
    renderer_registry = RendererRegistry()
    renderer_registry.register(renderer)

    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=_FailingGraph(),
        viz_agent_graph=_FailingGraph(),
        renderer_registry=renderer_registry,
        default_data_loader=lambda: rows,
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="Show me a bar chart of hotel ratings by town")]}
    )

    assert result["messages"][-1].content == "data:image/png;base64,fake"
    assert renderer.data == rows


def test_supervisor_resets_ready_flags_for_new_human_turn_with_same_thread():
    rows = [{"hotel_name": "St Ives Bay Resort", "town": "St Ives", "rating": 4.8}]

    renderer_registry = RendererRegistry()
    renderer_registry.register(_FakeRenderer())

    data_agent_graph = _FakeGraph(
        lambda state: {"messages": list(state["messages"]) + [AIMessage(content="No rows found")]}
    )
    viz_agent_graph = _FakeGraph(
        lambda state: {"messages": list(state["messages"]) + [AIMessage(content="")]}
    )
    graph = build_supervisor_graph(
        llm=None,
        data_agent_graph=data_agent_graph,
        viz_agent_graph=viz_agent_graph,
        checkpointer=InMemorySaver(),
        renderer_registry=renderer_registry,
        default_data_loader=lambda: rows,
    )
    config = {"configurable": {"thread_id": "same-thread"}}

    first = graph.invoke(
        {"messages": [HumanMessage(content="Show me a bar chart of hotel ratings by town")]},
        config=config,
    )
    second = graph.invoke(
        {"messages": [HumanMessage(content="Generate an Excel report of all hotels with pricing")]},
        config=config,
    )

    assert first["messages"][-1].content == "data:image/png;base64,fake"
    assert second["messages"][-1].content == "file:///tmp/fake.xlsx"
