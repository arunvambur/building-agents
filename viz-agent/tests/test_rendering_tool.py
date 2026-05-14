"""
Tests for tools/rendering_tool.py — RenderingTools plugin and render_visualization tool.
"""
from unittest.mock import MagicMock

import pytest

from core.dsl.schema import VisualizationSpec
from core.renderer.registry import RendererRegistry
from tools.rendering_tool import RenderingTools


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

class _FakeRenderer:
    name = "image"

    def supports(self, fmt: str) -> bool:
        return fmt == "image"

    def render(self, spec: VisualizationSpec, data) -> str:
        return "data:image/png;base64,fake"


class _FailingRenderer:
    name = "image"

    def supports(self, fmt: str) -> bool:
        return fmt == "image"

    def render(self, spec, data) -> str:
        raise RuntimeError("render exploded")


def _make_registry(renderer=None) -> RendererRegistry:
    registry = RendererRegistry()
    registry.register(renderer or _FakeRenderer())
    return registry


def _get_tool(registry: RendererRegistry):
    plugin = RenderingTools(registry)
    tools = plugin.get_tools()
    assert len(tools) == 1
    return tools[0]


_VALID_SPEC = {
    "charts": [
        {
            "type": "bar",
            "x": {"field": "town", "type": "dimension"},
            "y": {"field": "rating", "type": "measure"},
            "aggregation": {"field": "rating", "op": "avg"},
            "title": "Ratings by Town",
        }
    ],
    "output": "image",
}

_HOTEL_DATA = [
    {"town": "St Ives", "rating": 4.8},
    {"town": "Newquay", "rating": 4.5},
]


# ---------------------------------------------------------------------------
# Plugin interface
# ---------------------------------------------------------------------------

def test_plugin_name():
    plugin = RenderingTools(_make_registry())
    assert plugin.name == "rendering_tools"


def test_get_tools_returns_one_tool():
    plugin = RenderingTools(_make_registry())
    tools = plugin.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "render_visualization"


# ---------------------------------------------------------------------------
# Successful render
# ---------------------------------------------------------------------------

def test_render_visualization_returns_image_prefix():
    tool = _get_tool(_make_registry())
    result = tool.invoke({"spec_dict": _VALID_SPEC, "data": _HOTEL_DATA})
    assert result == "data:image/png;base64,fake"


def test_render_visualization_with_empty_data():
    tool = _get_tool(_make_registry())
    result = tool.invoke({"spec_dict": _VALID_SPEC, "data": []})
    # Should still return a renderer result (empty chart), not raise
    assert result.startswith("data:image/png;base64,")


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_render_visualization_invalid_spec_returns_error_string():
    tool = _get_tool(_make_registry())
    bad_spec = {
        "charts": [
            {
                "type": "bar",
                "x": {"field": "town", "type": "dimension"},
                "y": {"field": "town", "type": "dimension"},  # same field as x — invalid
                "title": "Bad",
            }
        ],
        "output": "image",
    }
    result = tool.invoke({"spec_dict": bad_spec, "data": _HOTEL_DATA})
    assert "error" in result.lower() or "validation" in result.lower()


def test_render_visualization_missing_required_field_returns_error_string():
    tool = _get_tool(_make_registry())
    # Missing 'output' key
    bad_spec = {
        "charts": [
            {
                "type": "bar",
                "x": {"field": "town", "type": "dimension"},
                "y": {"field": "rating", "type": "measure"},
            }
        ],
    }
    result = tool.invoke({"spec_dict": bad_spec, "data": _HOTEL_DATA})
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_visualization_unknown_format_returns_error_string():
    tool = _get_tool(_make_registry())
    bad_spec = dict(_VALID_SPEC)
    bad_spec = {**_VALID_SPEC, "output": "tableau"}
    result = tool.invoke({"spec_dict": bad_spec, "data": _HOTEL_DATA})
    assert "error" in result.lower() or "renderer" in result.lower()


# ---------------------------------------------------------------------------
# Renderer runtime errors
# ---------------------------------------------------------------------------

def test_render_visualization_renderer_exception_returns_error_string():
    tool = _get_tool(_make_registry(_FailingRenderer()))
    result = tool.invoke({"spec_dict": _VALID_SPEC, "data": _HOTEL_DATA})
    assert "error" in result.lower() or "render" in result.lower()


# ---------------------------------------------------------------------------
# Multiple chart types pass through
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("chart_type", ["bar", "line", "pie", "scatter"])
def test_render_visualization_various_chart_types(chart_type):
    tool = _get_tool(_make_registry())
    spec = {
        "charts": [
            {
                "type": chart_type,
                "x": {"field": "town", "type": "dimension"},
                "y": {"field": "rating", "type": "measure"},
                "aggregation": {"field": "rating", "op": "avg"},
                "title": f"{chart_type} chart",
            }
        ],
        "output": "image",
    }
    result = tool.invoke({"spec_dict": spec, "data": _HOTEL_DATA})
    assert result.startswith("data:image/png;base64,")
