import pytest

from core.renderer.registry import RendererRegistry
from core.renderer.base import Renderer
from core.dsl.schema import VisualizationSpec


class _MockRenderer(Renderer):
    name = "mock"

    def supports(self, format: str) -> bool:
        return format == "mock"

    def render(self, spec: VisualizationSpec, data) -> str:
        return "mock://output"


def test_registered_renderer_is_resolved():
    registry = RendererRegistry()
    registry.register(_MockRenderer())
    renderer = registry.get("mock")
    assert renderer.name == "mock"


def test_unknown_format_raises():
    registry = RendererRegistry()
    registry.register(_MockRenderer())
    with pytest.raises(ValueError, match="No renderer registered for format 'pdf'"):
        registry.get("pdf")


def test_multiple_renderers_resolve_correctly():
    class _AnotherRenderer(Renderer):
        name = "another"

        def supports(self, format: str) -> bool:
            return format == "another"

        def render(self, spec, data) -> str:
            return "another://output"

    registry = RendererRegistry()
    registry.register(_MockRenderer())
    registry.register(_AnotherRenderer())

    assert registry.get("mock").name == "mock"
    assert registry.get("another").name == "another"
