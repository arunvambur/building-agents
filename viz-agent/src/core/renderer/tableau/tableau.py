import uuid

from core.dsl.schema import VisualizationSpec
from core.renderer.base import Renderer


class TableauRenderer(Renderer):

    name = "tableau"

    def supports(self, format: str) -> bool:
        return format.lower() == "tableau"

    def render(self, spec: VisualizationSpec, data: any) -> str:
        """
        Renders a VisualizationSpec to a Tableau workbook and returns a tableau:// URI.
        """
        hyper_path = self._create_hyper(data)
        datasource_id = self._publish_datasource(hyper_path)

        template_path = self._resolve_template(spec)
        xml = self._load_template(template_path)
        xml = self._bind_fields(xml, spec)

        workbook_path = self._write_temp(xml)
        workbook_id = self._publish_workbook(workbook_path, datasource_id)

        return f"tableau://{workbook_id}"

    # ---- internals ----

    def _create_hyper(self, data) -> str:
        path = f"/tmp/{uuid.uuid4()}.hyper"
        # TODO: implement Hyper file creation using tableauhyperapi
        return path

    def _publish_datasource(self, hyper_path: str) -> str:
        # TODO: implement Tableau REST API datasource publish
        return "datasource-id"

    def _resolve_template(self, spec: VisualizationSpec) -> str:
        chart_type = spec.charts[0].type if spec.charts else "dashboard"
        templates = {
            "bar": "templates/bar.twb",
            "line": "templates/line.twb",
            "scatter": "templates/scatter.twb",
            "pie": "templates/pie.twb",
        }
        return templates.get(chart_type, "templates/dashboard.twb")

    def _load_template(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def _bind_fields(self, xml: str, spec: VisualizationSpec) -> str:
        chart = spec.charts[0]
        xml = xml.replace("<<X_FIELD>>", chart.x.field)
        xml = xml.replace("<<Y_FIELD>>", chart.y.field)
        if spec.filters:
            filter_str = ", ".join(f"{f.field} {f.op} {f.value}" for f in spec.filters)
            xml = xml.replace("<<FILTERS>>", filter_str)
        return xml

    def _write_temp(self, xml: str) -> str:
        path = f"/tmp/{uuid.uuid4()}.twb"
        with open(path, "w") as f:
            f.write(xml)
        return path

    def _publish_workbook(self, path: str, datasource_id: str) -> str:
        # TODO: implement Tableau REST API workbook publish
        return "workbook-id"
