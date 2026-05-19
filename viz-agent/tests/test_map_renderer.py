"""Tests for the folium-based MapRenderer."""
import os

import pytest

from core.dsl.schema import MapSpec, VisualizationSpec
from core.renderer.map.map import MapRenderer

FILE_PREFIX = "file://"


def strip_prefix(result: str) -> str:
    assert result.startswith(FILE_PREFIX), f"Expected file:// prefix, got: {result[:40]}"
    return result[len(FILE_PREFIX):]


@pytest.fixture
def renderer():
    return MapRenderer()


@pytest.fixture
def sample_data():
    return [
        {"hotel_name": "St Ives Bay Resort",  "town": "St Ives",  "rating": 4.8,
         "market_segment": "Luxury",   "occupancy_rate": 0.93, "monthly_revenue": 215000,
         "available_rooms": 6, "latitude": 50.211,  "longitude": -5.480},
        {"hotel_name": "Penzance Palace",      "town": "Penzance", "rating": 4.7,
         "market_segment": "Luxury",   "occupancy_rate": 0.91, "monthly_revenue": 188000,
         "available_rooms": 3, "latitude": 50.1188, "longitude": -5.5376},
        {"hotel_name": "Seaview Hotel",        "town": "Newquay",  "rating": 4.5,
         "market_segment": "Leisure",  "occupancy_rate": 0.87, "monthly_revenue": 142000,
         "available_rooms": 5, "latitude": 50.4155, "longitude": -5.0737},
        {"hotel_name": "Padstow Quay Inn",     "town": "Padstow",  "rating": 4.5,
         "market_segment": "Foodie",   "occupancy_rate": 0.84, "monthly_revenue": 126000,
         "available_rooms": 5, "latitude": 50.541,  "longitude": -4.936},
        {"hotel_name": "Land's End Lodge",     "town": "Land's End","rating": 4.6,
         "market_segment": "Adventure","occupancy_rate": 0.74, "monthly_revenue": 97000,
         "available_rooms": 2, "latitude": 50.0657, "longitude": -5.7138},
    ]


def _make_spec(map_type="marker", color_field=None, size_field=None, intensity_field=None):
    return VisualizationSpec(
        map_spec=MapSpec(
            map_type=map_type,
            lat_field="latitude",
            lon_field="longitude",
            label_field="hotel_name",
            color_field=color_field,
            size_field=size_field,
            intensity_field=intensity_field,
            title="Cornwall Hotels Map",
        ),
        output="map",
    )


# ---- supports ----

def test_supports_map(renderer):
    assert renderer.supports("map") is True

def test_does_not_support_image(renderer):
    assert renderer.supports("image") is False

def test_does_not_support_excel(renderer):
    assert renderer.supports("excel") is False


# ---- marker map ----

def test_marker_map_returns_file_prefix(renderer, sample_data):
    result = renderer.render(_make_spec("marker"), sample_data)
    assert result.startswith(FILE_PREFIX)

def test_marker_map_creates_html_file(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("marker"), sample_data))
    assert path.endswith(".html")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 5000  # folium HTML is substantial
    os.remove(path)

def test_marker_map_html_contains_folium(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("marker"), sample_data))
    content = open(path, encoding="utf-8").read()
    assert "leaflet" in content.lower()
    os.remove(path)

def test_marker_map_html_contains_hotel_names(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("marker"), sample_data))
    content = open(path, encoding="utf-8").read()
    assert "St Ives Bay Resort" in content
    assert "Penzance Palace" in content
    os.remove(path)

def test_marker_map_with_color_field(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("marker", color_field="market_segment"), sample_data))
    content = open(path, encoding="utf-8").read()
    assert "market_segment" in content
    os.remove(path)

def test_marker_map_empty_data(renderer):
    path = strip_prefix(renderer.render(_make_spec("marker"), []))
    assert os.path.exists(path)
    os.remove(path)


# ---- bubble map ----

def test_bubble_map_creates_html_file(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("bubble", size_field="monthly_revenue"), sample_data))
    assert path.endswith(".html")
    assert os.path.exists(path)
    os.remove(path)

def test_bubble_map_html_contains_circle_marker(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("bubble", size_field="monthly_revenue"), sample_data))
    content = open(path, encoding="utf-8").read()
    assert "CircleMarker" in content or "circle" in content.lower()
    os.remove(path)

def test_bubble_map_without_size_field(renderer, sample_data):
    # Should still render with uniform size
    path = strip_prefix(renderer.render(_make_spec("bubble"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


# ---- heatmap ----

def test_heatmap_creates_html_file(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("heatmap", intensity_field="occupancy_rate"), sample_data))
    assert path.endswith(".html")
    assert os.path.exists(path)
    os.remove(path)

def test_heatmap_html_contains_heatmap_plugin(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("heatmap", intensity_field="occupancy_rate"), sample_data))
    content = open(path, encoding="utf-8").read()
    assert "HeatMap" in content or "heatmap" in content.lower()
    os.remove(path)

def test_heatmap_without_intensity_field(renderer, sample_data):
    path = strip_prefix(renderer.render(_make_spec("heatmap"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


# ---- default MapSpec ----

def test_default_map_spec_uses_cornwall_centre(renderer, sample_data):
    spec = VisualizationSpec(map_spec=MapSpec(), output="map")
    path = strip_prefix(renderer.render(spec, sample_data))
    assert os.path.exists(path)
    os.remove(path)
