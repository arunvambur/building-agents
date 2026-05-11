from abc import ABC, abstractmethod

from core.dsl.schema import VisualizationSpec


class Renderer(ABC):

    name: str

    @abstractmethod
    def supports(self, format: str) -> bool:
        """Return True if this renderer handles the given output format."""

    @abstractmethod
    def render(self, spec: VisualizationSpec, data: any) -> str:
        """
        Render the visualization spec with the provided data.
        Returns a URI or file path pointing to the rendered output.
        """
