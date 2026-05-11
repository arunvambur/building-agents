import base64
import io
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from core.dsl.schema import Chart, VisualizationSpec
from core.renderer.base import Renderer

# Use non-interactive backend — no display required
matplotlib.use("Agg")

# Colour palette for chart series
_PALETTE = [
    "#4f6ef7", "#f97316", "#22c55e", "#a855f7",
    "#ec4899", "#14b8a6", "#eab308", "#ef4444",
]


class ImageRenderer(Renderer):

    name = "image"

    def supports(self, format: str) -> bool:
        return format.lower() == "image"

    def render(self, spec: VisualizationSpec, data: Any) -> str:
        """
        Renders a VisualizationSpec to a base64-encoded PNG string,
        prefixed with 'data:image/png;base64,' for API detection.
        """
        rows: list[dict] = data if isinstance(data, list) else []
        n = len(spec.charts)

        if n == 1:
            fig, axes = plt.subplots(1, 1, figsize=(9, 5))
            axes = [axes]
        else:
            cols = 2
            grid_rows = (n + 1) // cols
            fig, axes = plt.subplots(grid_rows, cols, figsize=(14, 5 * grid_rows))
            axes = axes.flatten().tolist()

        self._apply_theme(fig)

        for i, chart_spec in enumerate(spec.charts):
            self._draw_chart(axes[i], chart_spec, rows)

        # Hide unused axes in grid layouts
        for j in range(n, len(axes)):
            axes[j].set_visible(False)

        fig.tight_layout(pad=2.5)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)

        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"


    # ---- internals ----

    def _apply_theme(self, fig: plt.Figure) -> None:
        fig.patch.set_facecolor("#111827")  # gray-900

    def _draw_chart(self, ax: plt.Axes, chart_spec: Chart, rows: list[dict]) -> None:
        ax.set_facecolor("#1f2937")  # gray-800
        for spine in ax.spines.values():
            spine.set_edgecolor("#374151")

        ax.tick_params(colors="#9ca3af", labelsize=9)
        ax.xaxis.label.set_color("#9ca3af")
        ax.yaxis.label.set_color("#9ca3af")

        if chart_spec.title:
            ax.set_title(chart_spec.title, color="#f3f4f6", fontsize=11, pad=10)

        x_field = chart_spec.x.field
        y_field = chart_spec.y.field

        if not rows:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", color="#6b7280")
            return

        # Extract and aggregate data
        x_vals, y_vals = self._aggregate(rows, chart_spec)

        chart_type = chart_spec.type

        if chart_type == "bar":
            self._draw_bar(ax, x_vals, y_vals, x_field, y_field)
        elif chart_type == "line":
            self._draw_line(ax, x_vals, y_vals, x_field, y_field)
        elif chart_type == "scatter":
            self._draw_scatter(ax, x_vals, y_vals, x_field, y_field)
        elif chart_type == "pie":
            self._draw_pie(ax, x_vals, y_vals)

    def _aggregate(self, rows: list[dict], chart_spec: Chart):
        """Group by x field and apply aggregation op to y field."""
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        agg = chart_spec.aggregation

        if not agg:
            x_vals = [str(r.get(x_field, "")) for r in rows]
            y_vals = [self._to_float(r.get(y_field, 0)) for r in rows]
            return x_vals, y_vals

        # Group
        groups: dict[str, list[float]] = {}
        for r in rows:
            key = str(r.get(x_field, ""))
            val = self._to_float(r.get(y_field, 0))
            groups.setdefault(key, []).append(val)

        op = agg.op
        x_vals = list(groups.keys())
        y_vals = []
        for vals in groups.values():
            if op == "sum":
                y_vals.append(sum(vals))
            elif op == "avg":
                y_vals.append(sum(vals) / len(vals))
            elif op == "count":
                y_vals.append(float(len(vals)))
            elif op == "min":
                y_vals.append(min(vals))
            elif op == "max":
                y_vals.append(max(vals))

        return x_vals, y_vals

    def _to_float(self, val: Any) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def _draw_bar(self, ax, x_vals, y_vals, x_label, y_label):
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        bars = ax.bar(x_vals, y_vals, color=colors, width=0.6, zorder=2)
        ax.set_xlabel(x_label, labelpad=8)
        ax.set_ylabel(y_label, labelpad=8)
        ax.yaxis.grid(True, color="#374151", linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        # Value labels on bars
        for bar, val in zip(bars, y_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(y_vals) * 0.01,
                f"{val:.1f}",
                ha="center", va="bottom", color="#e5e7eb", fontsize=8,
            )
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    def _draw_line(self, ax, x_vals, y_vals, x_label, y_label):
        ax.plot(x_vals, y_vals, color=_PALETTE[0], linewidth=2, marker="o",
                markersize=5, markerfacecolor=_PALETTE[1], zorder=2)
        ax.fill_between(range(len(x_vals)), y_vals, alpha=0.15, color=_PALETTE[0])
        ax.set_xticks(range(len(x_vals)))
        ax.set_xticklabels(x_vals, rotation=30, ha="right")
        ax.set_xlabel(x_label, labelpad=8)
        ax.set_ylabel(y_label, labelpad=8)
        ax.yaxis.grid(True, color="#374151", linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_scatter(self, ax, x_vals, y_vals, x_label, y_label):
        # x may be categorical — convert to numeric index if needed
        try:
            x_numeric = [float(v) for v in x_vals]
            ax.set_xlabel(x_label, labelpad=8)
        except ValueError:
            x_numeric = list(range(len(x_vals)))
            ax.set_xticks(x_numeric)
            ax.set_xticklabels(x_vals, rotation=30, ha="right")
            ax.set_xlabel(x_label, labelpad=8)

        ax.scatter(x_numeric, y_vals, color=_PALETTE[0], s=60, zorder=2, alpha=0.85)
        ax.set_ylabel(y_label, labelpad=8)
        ax.yaxis.grid(True, color="#374151", linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_pie(self, ax, x_vals, y_vals):
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        wedges, texts, autotexts = ax.pie(
            y_vals,
            labels=x_vals,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.8,
            wedgeprops={"linewidth": 1, "edgecolor": "#111827"},
        )
        for t in texts:
            t.set_color("#d1d5db")
            t.set_fontsize(9)
        for at in autotexts:
            at.set_color("#111827")
            at.set_fontsize(8)
            at.set_fontweight("bold")
