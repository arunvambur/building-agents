from core.renderer.base import Renderer


class RendererRegistry:
    """
    Holds all registered Renderer implementations.
    Resolves the correct renderer by output format at runtime.
    """

    def __init__(self):
        self._renderers: list[Renderer] = []

    def register(self, renderer: Renderer) -> None:
        self._renderers.append(renderer)

    def get(self, format: str) -> Renderer:
        for renderer in self._renderers:
            if renderer.supports(format):
                return renderer
        raise ValueError(
            f"No renderer registered for format '{format}'. "
            f"Registered formats: {[r.name for r in self._renderers]}"
        )
