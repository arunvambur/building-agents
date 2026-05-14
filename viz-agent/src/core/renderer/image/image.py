import base64
import io
import math
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Wedge

from core.dsl.schema import Chart, VisualizationSpec
from core.renderer.base import Renderer

matplotlib.use("Agg")

_PALETTE = [
    "#7b9ccc", "#e8a87c", "#82b89a", "#b39dcc",
    "#d4899e", "#6db3b0", "#c9b96e", "#c47f7f",
]

_BG_DARK    = "#1a1f2e"
_BG_PANEL   = "#232938"
_GRID_COLOR = "#2e3548"
_TICK_COLOR = "#7a8499"
_LABEL_COLOR = "#7a8499"
_TITLE_COLOR = "#c8cdd8"
_TEXT_COLOR  = "#b0b8c8"


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

        for j in range(n, len(axes)):
            axes[j].set_visible(False)

        fig.tight_layout(pad=2.5)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)

        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    # ---- theme ----

    def _apply_theme(self, fig: plt.Figure) -> None:
        fig.patch.set_facecolor(_BG_DARK)

    def _style_axes(self, ax: plt.Axes, title: str = "") -> None:
        ax.set_facecolor(_BG_PANEL)
        for spine in ax.spines.values():
            spine.set_edgecolor(_GRID_COLOR)
        ax.tick_params(colors=_TICK_COLOR, labelsize=9)
        ax.xaxis.label.set_color(_LABEL_COLOR)
        ax.yaxis.label.set_color(_LABEL_COLOR)
        if title:
            ax.set_title(title, color=_TITLE_COLOR, fontsize=11, pad=10)

    # ---- dispatch ----

    def _draw_chart(self, ax: plt.Axes, chart_spec: Chart, rows: list[dict]) -> None:
        self._style_axes(ax, chart_spec.title or "")

        # Gauge can render without data (shows 0)
        if not rows and chart_spec.type != "gauge":
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", color=_TICK_COLOR)
            return

        dispatch = {
            "bar":            self._draw_bar,
            "horizontal_bar": self._draw_horizontal_bar,
            "stacked_bar":    self._draw_stacked_bar,
            "grouped_bar":    self._draw_grouped_bar,
            "line":           self._draw_line,
            "area":           self._draw_area,
            "scatter":        self._draw_scatter,
            "pie":            self._draw_pie,
            "donut":          self._draw_donut,
            "histogram":      self._draw_histogram,
            "heatmap":        self._draw_heatmap,
            "bubble":         self._draw_bubble,
            "waterfall":      self._draw_waterfall,
            "gauge":          self._draw_gauge,
        }
        fn = dispatch.get(chart_spec.type)
        if fn:
            fn(ax, chart_spec, rows)

    # ---- aggregation helpers ----

    def _aggregate(self, rows: list[dict], chart_spec: Chart):
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        agg = chart_spec.aggregation

        if not agg:
            return (
                [str(r.get(x_field, "")) for r in rows],
                [self._to_float(r.get(y_field, 0)) for r in rows],
            )

        groups: dict[str, list[float]] = {}
        for r in rows:
            groups.setdefault(str(r.get(x_field, "")), []).append(
                self._to_float(r.get(y_field, 0))
            )
        x_vals = list(groups.keys())
        y_vals = [self._apply_op(agg.op, v) for v in groups.values()]
        return x_vals, y_vals

    def _aggregate_field(self, rows: list[dict], x_field: str, y_field: str, op: str):
        groups: dict[str, list[float]] = {}
        for r in rows:
            groups.setdefault(str(r.get(x_field, "")), []).append(
                self._to_float(r.get(y_field, 0))
            )
        return list(groups.keys()), [self._apply_op(op, v) for v in groups.values()]

    def _apply_op(self, op: str, vals: list[float]) -> float:
        if op == "sum":   return sum(vals)
        if op == "avg":   return sum(vals) / len(vals) if vals else 0
        if op == "count": return float(len(vals))
        if op == "min":   return min(vals)
        if op == "max":   return max(vals)
        return 0.0

    def _to_float(self, val: Any) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    # ---- original chart types ----

    def _draw_bar(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        bars = ax.bar(x_vals, y_vals, color=colors, width=0.6, zorder=2)
        ax.set_xlabel(chart_spec.x.field, labelpad=8)
        ax.set_ylabel(chart_spec.y.field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        max_y = max(y_vals) if y_vals else 1
        for bar, val in zip(bars, y_vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_y * 0.01,
                    f"{val:.1f}", ha="center", va="bottom", color=_TEXT_COLOR, fontsize=8)
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    def _draw_horizontal_bar(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        bars = ax.barh(x_vals, y_vals, color=colors, height=0.6, zorder=2)
        ax.set_xlabel(chart_spec.y.field, labelpad=8)
        ax.set_ylabel(chart_spec.x.field, labelpad=8)
        ax.xaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        max_x = max(y_vals) if y_vals else 1
        for bar, val in zip(bars, y_vals):
            ax.text(bar.get_width() + max_x * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", ha="left", va="center", color=_TEXT_COLOR, fontsize=8)

    def _draw_stacked_bar(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        y2_field = chart_spec.y2.field if chart_spec.y2 else None
        x_vals, y_vals = self._aggregate_field(rows, x_field, y_field, "avg")
        ax.bar(x_vals, y_vals, color=_PALETTE[0], width=0.6, label=y_field, zorder=2)
        if y2_field:
            _, y2_vals = self._aggregate_field(rows, x_field, y2_field, "avg")
            ax.bar(x_vals, y2_vals, bottom=y_vals, color=_PALETTE[1],
                   width=0.6, label=y2_field, zorder=2)
            ax.legend(facecolor=_BG_PANEL, labelcolor=_TEXT_COLOR, fontsize=8)
        ax.set_xlabel(x_field, labelpad=8)
        ax.set_ylabel("Value", labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    def _draw_grouped_bar(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        y2_field = chart_spec.y2.field if chart_spec.y2 else None
        x_vals, y_vals = self._aggregate_field(rows, x_field, y_field, "avg")
        x_idx = np.arange(len(x_vals))
        width = 0.35
        ax.bar(x_idx - width / 2, y_vals, width, color=_PALETTE[0], label=y_field, zorder=2)
        if y2_field:
            _, y2_vals = self._aggregate_field(rows, x_field, y2_field, "avg")
            ax.bar(x_idx + width / 2, y2_vals, width, color=_PALETTE[1], label=y2_field, zorder=2)
            ax.legend(facecolor=_BG_PANEL, labelcolor=_TEXT_COLOR, fontsize=8)
        ax.set_xticks(x_idx)
        ax.set_xticklabels(x_vals, rotation=30, ha="right")
        ax.set_xlabel(x_field, labelpad=8)
        ax.set_ylabel("Value", labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_line(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        ax.plot(range(len(x_vals)), y_vals, color=_PALETTE[0], linewidth=2,
                marker="o", markersize=5, markerfacecolor=_PALETTE[1], zorder=2)
        ax.set_xticks(range(len(x_vals)))
        ax.set_xticklabels(x_vals, rotation=30, ha="right")
        ax.set_xlabel(chart_spec.x.field, labelpad=8)
        ax.set_ylabel(chart_spec.y.field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_area(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        x_idx = range(len(x_vals))
        ax.plot(x_idx, y_vals, color=_PALETTE[0], linewidth=2, marker="o", markersize=4, zorder=3)
        ax.fill_between(x_idx, y_vals, alpha=0.35, color=_PALETTE[0], zorder=2)
        if chart_spec.y2:
            _, y2_vals = self._aggregate_field(rows, chart_spec.x.field, chart_spec.y2.field, "avg")
            ax.plot(x_idx, y2_vals, color=_PALETTE[1], linewidth=2,
                    marker="o", markersize=4, zorder=3, label=chart_spec.y2.field)
            ax.fill_between(x_idx, y2_vals, alpha=0.25, color=_PALETTE[1], zorder=2)
            ax.legend(facecolor=_BG_PANEL, labelcolor=_TEXT_COLOR, fontsize=8)
        ax.set_xticks(range(len(x_vals)))
        ax.set_xticklabels(x_vals, rotation=30, ha="right")
        ax.set_xlabel(chart_spec.x.field, labelpad=8)
        ax.set_ylabel(chart_spec.y.field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_scatter(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        try:
            x_numeric = [float(r.get(x_field, 0)) for r in rows]
            ax.set_xlabel(x_field, labelpad=8)
        except (TypeError, ValueError):
            x_numeric = list(range(len(rows)))
            ax.set_xticks(x_numeric)
            ax.set_xticklabels([str(r.get(x_field, "")) for r in rows], rotation=30, ha="right")
            ax.set_xlabel(x_field, labelpad=8)
        y_numeric = [self._to_float(r.get(y_field, 0)) for r in rows]
        ax.scatter(x_numeric, y_numeric, color=_PALETTE[0], s=60, zorder=2, alpha=0.85)
        ax.set_ylabel(y_field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

    def _draw_pie(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        wedges, texts, autotexts = ax.pie(
            y_vals, labels=x_vals, colors=colors, autopct="%1.1f%%",
            startangle=140, pctdistance=0.8,
            wedgeprops={"linewidth": 1, "edgecolor": _BG_DARK},
        )
        for t in texts:
            t.set_color(_TICK_COLOR); t.set_fontsize(9)
        for at in autotexts:
            at.set_color(_BG_DARK); at.set_fontsize(8); at.set_fontweight("bold")

    def _draw_donut(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        x_vals, y_vals = self._aggregate(rows, chart_spec)
        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(x_vals))]
        wedges, texts, autotexts = ax.pie(
            y_vals, labels=x_vals, colors=colors, autopct="%1.1f%%",
            startangle=140, pctdistance=0.82,
            wedgeprops={"linewidth": 1, "edgecolor": _BG_DARK, "width": 0.55},
        )
        for t in texts:
            t.set_color(_TICK_COLOR); t.set_fontsize(9)
        for at in autotexts:
            at.set_color(_BG_DARK); at.set_fontsize(8); at.set_fontweight("bold")
        total = sum(y_vals)
        ax.text(0, 0, f"{total:.1f}\ntotal", ha="center", va="center",
                color=_TEXT_COLOR, fontsize=10, fontweight="bold")

    def _draw_histogram(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        y_field = chart_spec.y.field
        values = [self._to_float(r.get(y_field, 0)) for r in rows if r.get(y_field) is not None]
        if not values:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", color=_TICK_COLOR)
            return
        n_bins = min(max(5, len(values) // 2), 20)
        ax.hist(values, bins=n_bins, color=_PALETTE[0], edgecolor=_BG_DARK, linewidth=0.8, zorder=2)
        ax.set_xlabel(y_field, labelpad=8)
        ax.set_ylabel("Count", labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        mean_val = sum(values) / len(values)
        ax.axvline(mean_val, color=_PALETTE[1], linewidth=1.5, linestyle="--", zorder=3)
        ax.text(mean_val, ax.get_ylim()[1] * 0.95, f" mean={mean_val:.1f}",
                color=_PALETTE[1], fontsize=8, va="top")

    # ---- medium value chart types ----

    def _draw_heatmap(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        """
        Heatmap: x=row dimension, y2=column dimension, y=value intensity.
        Falls back to a single-column heatmap when y2 is absent.
        """
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        col_field = chart_spec.y2.field if chart_spec.y2 else y_field

        row_keys = list(dict.fromkeys(str(r.get(x_field, "")) for r in rows))
        col_keys = list(dict.fromkeys(str(r.get(col_field, "")) for r in rows))

        matrix = np.zeros((len(row_keys), len(col_keys)))
        row_idx = {k: i for i, k in enumerate(row_keys)}
        col_idx = {k: i for i, k in enumerate(col_keys)}

        for r in rows:
            ri = row_idx.get(str(r.get(x_field, "")))
            ci = col_idx.get(str(r.get(col_field, "")))
            if ri is not None and ci is not None:
                matrix[ri][ci] = self._to_float(r.get(y_field, 0))

        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(col_keys)))
        ax.set_xticklabels(col_keys, rotation=30, ha="right", color=_TICK_COLOR, fontsize=8)
        ax.set_yticks(range(len(row_keys)))
        ax.set_yticklabels(row_keys, color=_TICK_COLOR, fontsize=8)
        ax.set_xlabel(col_field, labelpad=8)
        ax.set_ylabel(x_field, labelpad=8)

        # Annotate each cell
        vmax = matrix.max() if matrix.max() > 0 else 1
        for ri in range(len(row_keys)):
            for ci in range(len(col_keys)):
                val = matrix[ri][ci]
                text_color = "black" if val > vmax * 0.6 else "white"
                ax.text(ci, ri, f"{val:.1f}", ha="center", va="center",
                        color=text_color, fontsize=8, fontweight="bold")

        cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
        cbar.ax.yaxis.set_tick_params(color=_TICK_COLOR)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=_TICK_COLOR)

    def _draw_bubble(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        """
        Bubble chart: x=measure, y=measure, bubble size=y2 measure (e.g. available_rooms).
        Falls back to uniform size when y2 is absent.
        """
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field
        size_field = chart_spec.y2.field if chart_spec.y2 else None

        x_vals = [self._to_float(r.get(x_field, 0)) for r in rows]
        y_vals = [self._to_float(r.get(y_field, 0)) for r in rows]
        labels = [str(r.get(x_field, "")) for r in rows]

        if size_field:
            raw_sizes = [self._to_float(r.get(size_field, 1)) for r in rows]
            max_s = max(raw_sizes) if max(raw_sizes) > 0 else 1
            sizes = [300 * (s / max_s) + 80 for s in raw_sizes]
        else:
            sizes = [200] * len(rows)

        colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(rows))]
        ax.scatter(x_vals, y_vals, s=sizes, c=colors, alpha=0.8, zorder=2,
                   edgecolors=_BG_DARK, linewidths=0.8)

        for xi, yi, label in zip(x_vals, y_vals, labels):
            ax.annotate(label, (xi, yi), textcoords="offset points", xytext=(0, 6),
                        ha="center", color=_TEXT_COLOR, fontsize=7)

        ax.set_xlabel(x_field, labelpad=8)
        ax.set_ylabel(y_field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.xaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)

        if size_field:
            ax.text(0.98, 0.02, f"Bubble size = {size_field}", transform=ax.transAxes,
                    ha="right", va="bottom", color=_TICK_COLOR, fontsize=7, style="italic")

    def _draw_waterfall(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        """
        Waterfall chart: shows cumulative effect of sequential positive/negative values.
        x=category labels, y=incremental values.
        """
        x_field = chart_spec.x.field
        y_field = chart_spec.y.field

        labels = [str(r.get(x_field, "")) for r in rows]
        values = [self._to_float(r.get(y_field, 0)) for r in rows]

        running = 0.0
        bottoms, bar_colors = [], []
        for v in values:
            bottoms.append(running if v >= 0 else running + v)
            bar_colors.append(_PALETTE[2] if v >= 0 else _PALETTE[7])
            running += v

        abs_vals = [abs(v) for v in values]
        bars = ax.bar(labels, abs_vals, bottom=bottoms, color=bar_colors,
                      width=0.6, zorder=2, edgecolor=_BG_DARK, linewidth=0.5)

        # Connector lines
        cumulative = 0.0
        for i, v in enumerate(values[:-1]):
            cumulative += v
            ax.plot([i + 0.3, i + 0.7], [cumulative, cumulative],
                    color=_TICK_COLOR, linewidth=0.8, linestyle="--", zorder=3)

        # Value labels
        max_abs = max(abs_vals, default=1)
        for bar, val in zip(bars, values):
            y_pos = bar.get_y() + bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos + max_abs * 0.01,
                    f"{val:+.1f}", ha="center", va="bottom", color=_TEXT_COLOR, fontsize=8)

        ax.set_xlabel(x_field, labelpad=8)
        ax.set_ylabel(y_field, labelpad=8)
        ax.yaxis.grid(True, color=_GRID_COLOR, linestyle="--", linewidth=0.6, zorder=1)
        ax.set_axisbelow(True)
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        ax.legend(handles=[
            Patch(color=_PALETTE[2], label="Increase"),
            Patch(color=_PALETTE[7], label="Decrease"),
        ], facecolor=_BG_PANEL, labelcolor=_TEXT_COLOR, fontsize=8)

    def _draw_gauge(self, ax, chart_spec: Chart, rows: list[dict]) -> None:
        """
        Gauge / KPI card: semicircular gauge showing a single aggregated metric.
        Colour zones: red (0-33%), yellow (33-66%), green (66-100%).
        """
        y_field = chart_spec.y.field
        agg = chart_spec.aggregation

        values = [self._to_float(r.get(y_field, 0)) for r in rows if r.get(y_field) is not None]

        if not values:
            value = 0.0
            max_val = 10.0
        else:
            value = self._apply_op(agg.op, values) if agg else values[0]
            raw_max = max(values) * 1.2 if max(values) > 0 else 10
            magnitude = 10 ** math.floor(math.log10(raw_max)) if raw_max > 0 else 1
            max_val = math.ceil(raw_max / magnitude) * magnitude

        fraction = min(max(value / max_val, 0), 1)

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.3, 1.3)
        ax.set_aspect("equal")
        ax.axis("off")

        # Background arc
        ax.add_patch(Wedge((0, 0), 1.0, 180, 0, width=0.3, facecolor=_GRID_COLOR, zorder=1))

        # Colour zones
        for start, end, color in [(180, 120, _PALETTE[7]), (120, 60, _PALETTE[6]), (60, 0, _PALETTE[2])]:
            ax.add_patch(Wedge((0, 0), 1.0, end, start, width=0.3,
                               facecolor=color, alpha=0.35, zorder=2))

        # Value arc
        needle_end = 180 - fraction * 180
        ax.add_patch(Wedge((0, 0), 1.0, needle_end, 180, width=0.3,
                           facecolor=_PALETTE[0], zorder=3))

        # Inner circle (donut hole)
        ax.add_patch(plt.Circle((0, 0), 0.7, color=_BG_PANEL, zorder=4))

        # Needle
        angle_rad = np.radians(needle_end)
        ax.annotate("", xy=(0.65 * np.cos(angle_rad), 0.65 * np.sin(angle_rad)),
                    xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=_TEXT_COLOR, lw=1.5), zorder=5)

        # Pivot dot
        ax.add_patch(plt.Circle((0, 0), 0.05, color=_TEXT_COLOR, zorder=6))

        # Labels
        ax.text(0, -0.05, f"{value:.1f}", ha="center", va="center",
                color=_TEXT_COLOR, fontsize=18, fontweight="bold", zorder=7)
        ax.text(0, -0.2, y_field, ha="center", va="center",
                color=_TICK_COLOR, fontsize=9, zorder=7)
        ax.text(-1.1, -0.05, "0", ha="center", color=_TICK_COLOR, fontsize=8)
        ax.text(1.1, -0.05, f"{max_val:.0f}", ha="center", color=_TICK_COLOR, fontsize=8)
