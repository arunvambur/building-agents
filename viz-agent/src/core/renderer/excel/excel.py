import os
import tempfile
import uuid
from typing import Any

import openpyxl
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from core.dsl.schema import Chart, VisualizationSpec
from core.renderer.base import Renderer


class ExcelRenderer(Renderer):

    name = "excel"

    def supports(self, format: str) -> bool:
        return format.lower() == "excel"

    def render(self, spec: VisualizationSpec, data: Any) -> str:
        """
        Renders a VisualizationSpec to an Excel workbook (.xlsx).
        Each chart in the spec gets its own worksheet.
        Returns the file path of the generated workbook.
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # remove default empty sheet

        rows: list[dict] = data if isinstance(data, list) else []

        for i, chart_spec in enumerate(spec.charts):
            sheet_title = chart_spec.title or f"Chart {i + 1}"
            ws = wb.create_sheet(title=sheet_title[:31])  # Excel sheet name limit
            self._write_data_sheet(ws, rows, chart_spec)
            self._add_chart(ws, rows, chart_spec)

        if spec.filters:
            self._write_filters_sheet(wb, spec)

        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.xlsx")
        wb.save(output_path)
        return output_path

    # ---- internals ----

    def _write_data_sheet(self, ws, rows: list[dict], chart_spec: Chart) -> None:
        """Write the raw data table into the worksheet with a styled header row."""
        if not rows:
            ws.append(["No data available"])
            return

        headers = list(rows[0].keys())
        header_row = ws.append(headers) or ws[1]

        # Style header
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for row in rows:
            ws.append([row.get(h) for h in headers])

        # Auto-size columns
        for col_idx, header in enumerate(headers, start=1):
            col_letter = get_column_letter(col_idx)
            max_len = max(len(str(header)), *(len(str(r.get(header, ""))) for r in rows))
            ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    def _add_chart(self, ws, rows: list[dict], chart_spec: Chart) -> None:
        """Create and embed an Excel chart based on the spec."""
        if not rows:
            return

        headers = list(rows[0].keys())
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field

        if x_field not in headers or y_field not in headers:
            return

        x_col = headers.index(x_field) + 1
        y_col = headers.index(y_field) + 1
        data_rows = len(rows)

        chart = self._build_chart(chart_spec, ws, x_col, y_col, data_rows)
        if chart is None:
            return

        chart.title = chart_spec.title or f"{y_field} by {x_field}"
        chart.style = 10
        chart.width = 20
        chart.height = 12

        # Place chart below the data table
        anchor_row = data_rows + 4
        ws.add_chart(chart, f"A{anchor_row}")

    def _build_chart(self, chart_spec: Chart, ws, x_col: int, y_col: int, data_rows: int):
        """Instantiate the correct openpyxl chart type."""
        data_ref = Reference(ws, min_col=y_col, min_row=1, max_row=data_rows + 1)
        cats_ref = Reference(ws, min_col=x_col, min_row=2, max_row=data_rows + 1)

        chart_type = chart_spec.type

        if chart_type == "bar":
            chart = BarChart()
            chart.type = "col"
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            return chart

        if chart_type == "line":
            chart = LineChart()
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            return chart

        if chart_type == "pie":
            chart = PieChart()
            chart.add_data(data_ref, titles_from_data=True)
            chart.dataLabels = None
            chart.set_categories(cats_ref)
            return chart

        if chart_type == "scatter":
            # Scatter uses BarChart in column mode as a fallback — openpyxl ScatterChart
            # requires numeric x-axis which may not always be available
            from openpyxl.chart import ScatterChart, Series
            chart = ScatterChart()
            x_ref = Reference(ws, min_col=x_col, min_row=2, max_row=data_rows + 1)
            y_ref = Reference(ws, min_col=y_col, min_row=1, max_row=data_rows + 1)
            series = Series(y_ref, x_ref, title_from_data=True)
            chart.series.append(series)
            return chart

        return None

    def _write_filters_sheet(self, wb: openpyxl.Workbook, spec: VisualizationSpec) -> None:
        """Write applied filters to a dedicated summary sheet."""
        ws = wb.create_sheet(title="Filters Applied")
        ws.append(["Field", "Operator", "Value"])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for f in spec.filters:
            ws.append([f.field, f.op, f.value])
