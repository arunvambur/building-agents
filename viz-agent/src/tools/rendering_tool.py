from core.dsl.validator import SpecValidationError, validate_spec
from core.plugin.interfaces import ToolPlugin
from core.renderer.registry import RendererRegistry


class RenderingTools(ToolPlugin):
    """
    Tool plugin for the viz_agent.
    Provides tools for validating a VisualizationSpec and dispatching to the correct renderer.
    """

    name = "rendering_tools"

    def __init__(self, renderer_registry: RendererRegistry):
        self._renderer_registry = renderer_registry

    def get_tools(self) -> list:
        from langchain_core.tools import tool
        from core.dsl.schema import VisualizationSpec

        renderer_registry = self._renderer_registry

        @tool
        def render_visualization(spec_dict: dict, data: dict) -> str:
            """
            Validates a VisualizationSpec and renders it using the appropriate renderer.
            Args:
                spec_dict: A dict matching the VisualizationSpec schema.
                data: The raw data payload to visualize.
            Returns:
                A URI or file path pointing to the rendered output.
            """
            try:
                spec = VisualizationSpec(**spec_dict)
                validate_spec(spec)
                renderer = renderer_registry.get(spec.output)
                return renderer.render(spec, data)
            except SpecValidationError as e:
                return f"Validation error: {e}"
            except ValueError as e:
                return f"Renderer error: {e}"
            except Exception as e:
                return f"Unexpected error during rendering: {e}"

        return [render_visualization]
