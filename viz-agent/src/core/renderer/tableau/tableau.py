# core/plugins/outputs/tableau.py

import uuid
from core.renderer.base import Renderer


class TableauPlugin(Renderer):

    name = "tableau"

    def export(self, charts, spec, data):

        hyper_path = self._create_hyper(data)
        datasource_id = self._publish_datasource(hyper_path)

        template_path = self._resolve_template(spec)

        xml = self._load_template(template_path)
        xml = self._bind_fields(xml, spec)

        workbook_path = self._write_temp(xml)

        workbook_id = self._publish_workbook(workbook_path, datasource_id)

        return f"tableau://{workbook_id}"

    # ---- internals ----

    def _create_hyper(self, data):
        path = f"/tmp/{uuid.uuid4()}.hyper"
        # TODO: implement Hyper creation
        return path

    def _publish_datasource(self, hyper_path):
        # REST API call
        return "datasource-id"

    def _resolve_template(self, spec):
        chart_type = spec["charts"][0]["type"]

        if chart_type == "bar":
            return "templates/bar.twb"
        if chart_type == "line":
            return "templates/line.twb"

        return "templates/dashboard.twb"

    def _load_template(self, path):
        with open(path, "r") as f:
            return f.read()

    def _bind_fields(self, xml, spec):
        chart = spec["charts"][0]

        x = chart["x"]["field"]
        y = chart["y"]["field"]

        xml = xml.replace("<<X_FIELD>>", x)
        xml = xml.replace("<<Y_FIELD>>", y)

        return xml

    def _write_temp(self, xml):
        path = f"/tmp/{uuid.uuid4()}.twb"
        with open(path, "w") as f:
            f.write(xml)
        return path

    def _publish_workbook(self, path, datasource_id):
        # REST API call
        return "workbook-id"