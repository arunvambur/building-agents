"""
Tests for medium-value dashboard chart types:
heatmap, bubble, waterfall, gauge
"""
import base64
import os

import pytest

from core.dsl.schema import Aggregation, Axis, Chart, VisualizationSpec
from core.renderer.excel.excel import ExcelRenderer
from core.renderer.image.image import ImageRenderer

IMAGE_PREFIX = "data:image/png;base64,"
FILE_PREFIX = "file://"


def strip_file(result: str) -> str:
    assert result.startswith(FILE_PREFIX)
    return result[len(FILE_PREFIX):]


def is_valid_png(b64: str) -> bool:
    return base64.b64decode(b64)[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def img():
    return ImageRenderer()


@pytest.fixture
def xls():
    return ExcelRenderer()


@pytest.fixture
def sample_data():
    return [
        {"town": "St Ives",  "rating": 4.8, "price_single": 140.0, "price_double": 210.0, "available_rooms": 6},
        {"town": "Newquay",  "rating": 4.5, "price_single": 120.0, "price_double": 180.0, "available_rooms": 5},
        {"town": "Falmouth", "rating": 4.2, "price_single": 95.0,  "price_double": 150.0, "available_rooms": 2},
        {"town": "Penzance", "rating": 4.7, "price_single": 130.0, "price_double": 200.0, "available_rooms": 3},
        {"town": "Bude",     "rating": 4.4, "price_single": 115.0, "price_double": 175.0, "available_rooms": 7},
    ]


# ============================================================
# HEATMAP
# ============================================================

def _heatmap_spec(output="image"):
    return VisualizationSpec(
        charts=[Chart(
            type="heatmap",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="rating", type="measure"),
            y2=Axis(field="price_single", type="measure"),
            title="Rating Heatmap",
        )],
        output=output,
    )


def test_heatmap_image_returns_png(img, sample_data):
    result = img.render(_heatmap_spec(), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert is_valid_png(result[len(IMAGE_PREFIX):])


def test_heatmap_image_no_y2(img, sample_data):
    spec = VisualizationSpec(
        charts=[Chart(type="heatmap", x=Axis(field="town", type="dimension"),
                      y=Axis(field="rating", type="measure"), title="Heatmap")],
        output="image",
    )
    result = img.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)


def test_heatmap_image_empty_data(img):
    result = img.render(_heatmap_spec(), [])
    assert result.startswith(IMAGE_PREFIX)


def test_heatmap_excel_creates_file(xls, sample_data):
    path = strip_file(xls.render(_heatmap_spec("excel"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


# ============================================================
# BUBBLE
# ============================================================

def _bubble_spec(output="image"):
    return VisualizationSpec(
        charts=[Chart(
            type="bubble",
            x=Axis(field="price_single", type="measure"),
            y=Axis(field="rating", type="measure"),
            y2=Axis(field="available_rooms", type="measure"),
            title="Price vs Rating (bubble=rooms)",
        )],
        output=output,
    )


def test_bubble_image_returns_png(img, sample_data):
    result = img.render(_bubble_spec(), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert is_valid_png(result[len(IMAGE_PREFIX):])


def test_bubble_image_no_size_field(img, sample_data):
    spec = VisualizationSpec(
        charts=[Chart(type="bubble", x=Axis(field="price_single", type="measure"),
                      y=Axis(field="rating", type="measure"), title="Bubble")],
        output="image",
    )
    result = img.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)


def test_bubble_excel_creates_file(xls, sample_data):
    path = strip_file(xls.render(_bubble_spec("excel"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


# ============================================================
# WATERFALL
# ============================================================

def _waterfall_spec(output="image"):
    return VisualizationSpec(
        charts=[Chart(
            type="waterfall",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="price_single", type="measure"),
            title="Price Waterfall",
        )],
        output=output,
    )


def test_waterfall_image_returns_png(img, sample_data):
    result = img.render(_waterfall_spec(), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert is_valid_png(result[len(IMAGE_PREFIX):])


def test_waterfall_image_mixed_values(img):
    data = [
        {"town": "Start",    "price_single": 100.0},
        {"town": "Increase", "price_single": 30.0},
        {"town": "Decrease", "price_single": -20.0},
        {"town": "End",      "price_single": 15.0},
    ]
    result = img.render(_waterfall_spec(), data)
    assert result.startswith(IMAGE_PREFIX)


def test_waterfall_excel_creates_file(xls, sample_data):
    path = strip_file(xls.render(_waterfall_spec("excel"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


# ============================================================
# GAUGE
# ============================================================

def _gauge_spec(output="image"):
    return VisualizationSpec(
        charts=[Chart(
            type="gauge",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="rating", type="measure"),
            aggregation=Aggregation(field="rating", op="avg"),
            title="Avg Rating Gauge",
        )],
        output=output,
    )


def test_gauge_image_returns_png(img, sample_data):
    result = img.render(_gauge_spec(), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert is_valid_png(result[len(IMAGE_PREFIX):])


def test_gauge_image_empty_data(img):
    # Gauge should render with value=0 when no data
    result = img.render(_gauge_spec(), [])
    assert result.startswith(IMAGE_PREFIX)


def test_gauge_excel_creates_file(xls, sample_data):
    # Gauge has no native Excel chart — produces data table only
    path = strip_file(xls.render(_gauge_spec("excel"), sample_data))
    assert os.path.exists(path)
    os.remove(path)


def test_gauge_no_aggregation(img, sample_data):
    spec = VisualizationSpec(
        charts=[Chart(type="gauge", x=Axis(field="town", type="dimension"),
                      y=Axis(field="rating", type="measure"), title="Gauge")],
        output="image",
    )
    result = img.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)


# ============================================================
# MULTI-CHART GRID with medium types
# ============================================================

def test_mixed_medium_chart_grid(img, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(type="heatmap", x=Axis(field="town", type="dimension"),
                  y=Axis(field="rating", type="measure"),
                  y2=Axis(field="price_single", type="measure"), title="Heatmap"),
            Chart(type="bubble", x=Axis(field="price_single", type="measure"),
                  y=Axis(field="rating", type="measure"),
                  y2=Axis(field="available_rooms", type="measure"), title="Bubble"),
            Chart(type="waterfall", x=Axis(field="town", type="dimension"),
                  y=Axis(field="price_single", type="measure"), title="Waterfall"),
            Chart(type="gauge", x=Axis(field="town", type="dimension"),
                  y=Axis(field="rating", type="measure"),
                  aggregation=Aggregation(field="rating", op="avg"), title="Gauge"),
        ],
        layout="grid",
        output="image",
    )
    result = img.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert is_valid_png(result[len(IMAGE_PREFIX):])
