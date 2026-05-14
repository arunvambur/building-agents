from core.dsl.schema import VisualizationSpec
from core.renderer.base import Renderer


class TableauRenderer(Renderer):
    """
    Tableau renderer — not yet implemented.

    Requires:
      - tableauhyperapi  (Hyper file creation)
      - tableauserverclient  (REST API publish)
      - Tableau Server / Tableau Cloud credentials

    Register this renderer only after the above dependencies are available
    and the TODO methods below are implemented.
    """

    name = "tableau"

    def supports(self, format: str) -> bool:
        return format.lower() == "tableau"

    def render(self, spec: VisualizationSpec, data: any) -> str:
        raise NotImplementedError(
            "TableauRenderer is not yet implemented. "
            "Install tableauhyperapi and tableauserverclient, configure "
            "Tableau Server credentials, and implement the publish methods."
        )
