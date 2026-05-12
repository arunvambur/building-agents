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
        def render_visualization(spec_dict: dict, data: list) -> str:
            """
            Validates a VisualizationSpec and renders it using the appropriate renderer.
            ALWAYS call this tool to produce the final output — never skip it.
            Args:
                spec_dict: A dict matching the VisualizationSpec schema. Must include:
                    - charts: list of chart dicts, each with type, x (field+type), y (field+type),
                      aggregation (optional), title (optional).
                    - output: 'image' for inline chart PNG, 'excel' for downloadable spreadsheet.
                    - filters: optional list of filter dicts.
                    - layout: optional 'single', 'grid', or 'dashboard'.
                data: The raw list of data records (list of dicts) from the data agent.
            Returns:
                For 'image': a base64-encoded PNG string prefixed with 'data:image/png;base64,'.
                For 'excel': a file path prefixed with 'file://'.
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
