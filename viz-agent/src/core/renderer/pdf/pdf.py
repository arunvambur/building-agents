import io
import logging
import os
import tempfile
import uuid
from datetime import date
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.dsl.schema import Chart, VisualizationSpec
from core.renderer.base import Renderer
from core.renderer.image.image import ImageRenderer

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

# Brand colours — kept in sync with image.py subtle palette
_BRAND_BLUE  = colors.HexColor("#7b9ccc")
_DARK_BG     = colors.HexColor("#1a1f2e")
_LIGHT_GRAY  = colors.HexColor("#f0f2f5")
_MID_GRAY    = colors.HexColor("#7a8499")
_BORDER      = colors.HexColor("#d1d5db")


class PDFRenderer(Renderer):

    name = "pdf"

    def __init__(self):
        self._image_renderer = ImageRenderer()

    def supports(self, format: str) -> bool:
        return format.lower() == "pdf"

    def render(self, spec: VisualizationSpec, data: Any) -> str:
        """
        Renders a VisualizationSpec to a PDF file.
        Each chart is rendered as a PNG via matplotlib and embedded in the PDF.
        A data table is appended after each chart.
        Returns a 'file://<path>' string.
        """
        rows: list[dict] = data if isinstance(data, list) else []
        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.pdf")

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "VizTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=_BRAND_BLUE,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "VizSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=_MID_GRAY,
            spaceAfter=16,
        )
        section_style = ParagraphStyle(
            "SectionHead",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=_DARK_BG,
            spaceBefore=12,
            spaceAfter=6,
        )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        story = []

        # Cover header
        story.append(Paragraph("Viz Agent — Visualization Report", title_style))
        story.append(Paragraph(
            f"Generated {date.today().strftime('%d %b %Y')} &nbsp;|&nbsp; "
            f"{len(spec.charts)} chart(s) &nbsp;|&nbsp; {len(rows)} records",
            subtitle_style,
        ))
        story.append(Spacer(1, 0.4 * cm))

        for i, chart_spec in enumerate(spec.charts):
            chart_title = chart_spec.title or f"Chart {i + 1}"
            story.append(Paragraph(chart_title, section_style))

            # Render chart to PNG bytes via matplotlib
            chart_img_bytes = self._render_chart_to_bytes(chart_spec, rows)
            img = Image(io.BytesIO(chart_img_bytes), width=15 * cm, height=9 * cm)
            story.append(img)
            story.append(Spacer(1, 0.5 * cm))

            # Data table
            if rows:
                story.append(Paragraph("Data", section_style))
                story.append(self._build_table(rows))
                story.append(Spacer(1, 0.5 * cm))

            # Filters summary
            if spec.filters:
                filter_text = "  |  ".join(
                    f"{f.field} {f.op} {f.value}" for f in spec.filters
                )
                story.append(Paragraph(f"Filters applied: {filter_text}", subtitle_style))

            if i < len(spec.charts) - 1:
                story.append(PageBreak())

        doc.build(story)
        logger.info("[pdf_renderer] written to %s", output_path)
        return f"file://{output_path}"

    # ---- internals ----

    def _render_chart_to_bytes(self, chart_spec: Chart, rows: list[dict]) -> bytes:
        """Render a single chart to PNG bytes using the ImageRenderer internals."""
        fig, ax = plt.subplots(1, 1, figsize=(9, 5))
        self._image_renderer._apply_theme(fig)
        self._image_renderer._draw_chart(ax, chart_spec, rows)
        fig.tight_layout(pad=2.0)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def _build_table(self, rows: list[dict]) -> Table:
        if not rows:
            return Table([["No data"]])

        headers = list(rows[0].keys())
        table_data = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]

        col_width = 15 * cm / max(len(headers), 1)
        col_widths = [col_width] * len(headers)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]))
        return table
