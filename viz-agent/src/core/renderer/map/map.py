import logging
import os
import tempfile
import uuid
from typing import Any

import folium
from folium.plugins import HeatMap, MarkerCluster

from core.dsl.schema import MapSpec, VisualizationSpec
from core.renderer.base import Renderer

logger = logging.getLogger(__name__)

# Colour palette for categorical marker colouring
_CATEGORY_COLOURS = [
    "blue", "red", "green", "purple", "orange",
    "darkred", "lightred", "beige", "darkblue", "darkgreen",
    "cadetblue", "darkpurple", "white", "pink", "lightblue",
]

# Cornwall centre coordinates
_CORNWALL_LAT = 50.35
_CORNWALL_LON = -4.95
_DEFAULT_ZOOM = 9


class MapRenderer(Renderer):

    name = "map"

    def supports(self, format: str) -> bool:
        return format.lower() == "map"

    def render(self, spec: VisualizationSpec, data: Any) -> str:
        """
        Renders a geographic map using folium.
        Returns a 'file://<path>' string pointing to a self-contained HTML file.
        Supports three map types:
          - marker  : one marker per record, colour-coded by a categorical field
          - bubble  : circle markers sized by a numeric field
          - heatmap : intensity layer based on a numeric field
        """
        rows: list[dict] = data if isinstance(data, list) else []
        map_spec: MapSpec = spec.map_spec or MapSpec()

        title = map_spec.title or "Cornwall Hotels Map"
        logger.info("[map_renderer] rendering %s map — %d records", map_spec.map_type, len(rows))

        # Centre map on data centroid or Cornwall default
        centre_lat, centre_lon = self._centroid(rows, map_spec)

        fmap = folium.Map(
            location=[centre_lat, centre_lon],
            zoom_start=_DEFAULT_ZOOM,
            tiles="OpenStreetMap",
        )

        # Title overlay
        self._add_title(fmap, title)

        if map_spec.map_type == "marker":
            self._add_markers(fmap, rows, map_spec)
        elif map_spec.map_type == "bubble":
            self._add_bubbles(fmap, rows, map_spec)
        elif map_spec.map_type == "heatmap":
            self._add_heatmap(fmap, rows, map_spec)

        # Fit bounds to all markers
        if rows:
            lats = [self._val(r, map_spec.lat_field) for r in rows if self._val(r, map_spec.lat_field)]
            lons = [self._val(r, map_spec.lon_field) for r in rows if self._val(r, map_spec.lon_field)]
            if lats and lons:
                fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.html")
        fmap.save(output_path)
        logger.info("[map_renderer] saved to %s", output_path)
        return f"file://{output_path}"

    # ---- map type builders ----

    def _add_markers(self, fmap: folium.Map, rows: list[dict], spec: MapSpec) -> None:
        """Clustered markers, colour-coded by a categorical field."""
        cluster = MarkerCluster(name="Hotels").add_to(fmap)

        # Build colour map for the categorical field
        colour_map: dict[str, str] = {}
        if spec.color_field:
            categories = list(dict.fromkeys(
                str(r.get(spec.color_field, "")) for r in rows
            ))
            colour_map = {
                cat: _CATEGORY_COLOURS[i % len(_CATEGORY_COLOURS)]
                for i, cat in enumerate(categories)
            }

        for r in rows:
            lat = self._val(r, spec.lat_field)
            lon = self._val(r, spec.lon_field)
            if lat is None or lon is None:
                continue

            label = str(r.get(spec.label_field, ""))
            colour = colour_map.get(str(r.get(spec.color_field, "")), "blue") if spec.color_field else "blue"
            popup_html = self._build_popup(r, label)

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=label,
                icon=folium.Icon(color=colour, icon="home", prefix="fa"),
            ).add_to(cluster)

        # Legend for colour field
        if spec.color_field and colour_map:
            self._add_legend(fmap, spec.color_field, colour_map)

    def _add_bubbles(self, fmap: folium.Map, rows: list[dict], spec: MapSpec) -> None:
        """Circle markers sized by a numeric field."""
        size_field = spec.size_field or spec.intensity_field
        values = [self._val(r, size_field) for r in rows if size_field and self._val(r, size_field) is not None]
        max_val = max(values) if values else 1
        min_val = min(values) if values else 0
        val_range = max_val - min_val or 1

        for r in rows:
            lat = self._val(r, spec.lat_field)
            lon = self._val(r, spec.lon_field)
            if lat is None or lon is None:
                continue

            label = str(r.get(spec.label_field, ""))
            raw_size = self._val(r, size_field) if size_field else None
            # Scale radius between 8 and 40 pixels
            radius = 8 + 32 * ((raw_size - min_val) / val_range) if raw_size is not None else 15
            popup_html = self._build_popup(r, label)

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color="#4f6ef7",
                fill=True,
                fill_color="#4f6ef7",
                fill_opacity=0.65,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"{label}" + (f" — {size_field}: {raw_size}" if raw_size is not None else ""),
            ).add_to(fmap)

    def _add_heatmap(self, fmap: folium.Map, rows: list[dict], spec: MapSpec) -> None:
        """Heatmap layer with intensity from a numeric field."""
        intensity_field = spec.intensity_field or spec.size_field

        heat_data = []
        for r in rows:
            lat = self._val(r, spec.lat_field)
            lon = self._val(r, spec.lon_field)
            if lat is None or lon is None:
                continue
            intensity = self._val(r, intensity_field) if intensity_field else 1.0
            heat_data.append([lat, lon, intensity or 1.0])

        if heat_data:
            HeatMap(
                heat_data,
                name="Heatmap",
                min_opacity=0.3,
                radius=35,
                blur=20,
                gradient={"0.4": "blue", "0.65": "lime", "1": "red"},
            ).add_to(fmap)

        # Also add subtle markers so locations are visible when zoomed in
        for r in rows:
            lat = self._val(r, spec.lat_field)
            lon = self._val(r, spec.lon_field)
            if lat is None or lon is None:
                continue
            label = str(r.get(spec.label_field, ""))
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="white",
                fill=True,
                fill_color="white",
                fill_opacity=0.8,
                tooltip=label,
            ).add_to(fmap)

        folium.LayerControl().add_to(fmap)

    # ---- helpers ----

    def _centroid(self, rows: list[dict], spec: MapSpec) -> tuple[float, float]:
        lats = [self._val(r, spec.lat_field) for r in rows]
        lons = [self._val(r, spec.lon_field) for r in rows]
        lats = [v for v in lats if v is not None]
        lons = [v for v in lons if v is not None]
        if lats and lons:
            return sum(lats) / len(lats), sum(lons) / len(lons)
        return _CORNWALL_LAT, _CORNWALL_LON

    def _val(self, row: dict, field: str | None) -> float | None:
        if not field:
            return None
        v = row.get(field)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _build_popup(self, row: dict, label: str) -> str:
        """Builds a styled HTML popup showing all record fields."""
        rows_html = "".join(
            f"<tr><td style='padding:2px 6px;color:#64748b;font-size:11px'>{k}</td>"
            f"<td style='padding:2px 6px;font-weight:600;font-size:11px'>{v}</td></tr>"
            for k, v in row.items()
            if k not in ("latitude", "longitude")
        )
        return (
            f"<div style='font-family:Inter,sans-serif;min-width:200px'>"
            f"<div style='background:#4f6ef7;color:white;padding:6px 10px;"
            f"border-radius:6px 6px 0 0;font-weight:700;font-size:13px'>{label}</div>"
            f"<table style='border-collapse:collapse;width:100%'>{rows_html}</table>"
            f"</div>"
        )

    def _add_title(self, fmap: folium.Map, title: str) -> None:
        title_html = (
            f"<div style='position:fixed;top:12px;left:50%;transform:translateX(-50%);"
            f"z-index:1000;background:white;padding:8px 18px;border-radius:8px;"
            f"box-shadow:0 2px 8px rgba(0,0,0,0.15);font-family:Inter,sans-serif;"
            f"font-size:14px;font-weight:700;color:#1e293b'>{title}</div>"
        )
        fmap.get_root().html.add_child(folium.Element(title_html))

    def _add_legend(self, fmap: folium.Map, field: str, colour_map: dict[str, str]) -> None:
        items = "".join(
            f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0'>"
            f"<div style='width:12px;height:12px;border-radius:50%;background:{colour}'></div>"
            f"<span style='font-size:12px'>{cat}</span></div>"
            for cat, colour in colour_map.items()
        )
        legend_html = (
            f"<div style='position:fixed;bottom:30px;right:12px;z-index:1000;"
            f"background:white;padding:10px 14px;border-radius:8px;"
            f"box-shadow:0 2px 8px rgba(0,0,0,0.15);font-family:Inter,sans-serif'>"
            f"<div style='font-weight:700;font-size:12px;margin-bottom:6px;color:#1e293b'>"
            f"{field}</div>{items}</div>"
        )
        fmap.get_root().html.add_child(folium.Element(legend_html))
