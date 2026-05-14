import base64

import pytest

from core.dsl.schema import Aggregation, Axis, Chart, VisualizationSpec
from core.renderer.image.image import ImageRenderer

IMAGE_PREFIX = "data:image/png;base64,"


@pytest.fixture
def renderer():
    return ImageRenderer()


@pytest.fixture
def sample_data():
    return [
        {"town": "St Ives",  "rating": 4.8, "price_single": 140.0, "price_double": 210.0, "available_rooms": 6},
        {"town": "Newquay",  "rating": 4.5, "price_single": 120.0, "price_double": 180.0, "available_rooms": 5},
        {"town": "Falmouth", "rating": 4.2, "price_single": 95.0,  "price_double": 150.0, "available_rooms": 2},
        {"town": "Penzance", "rating": 4.7, "price_single": 130.0, "price_double": 200.0, "available_rooms": 3},
    ]


def _make_spec(chart_type, output="image", aggregation=None, y2_field=None):
    chart = Chart(
        type=chart_type,
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        y2=Axis(field=y2_field, type="measure") if y2_field else None,
        aggregation=aggregation,
        title=f"{chart_type.replace('_', ' ').title()} Chart",
    )
    return VisualizationSpec(charts=[chart], output=output)


def _is_valid_png(b64: str) -> bool:
    raw = base64.b64decode(b64)
    return raw[:8] == b"\x89PNG\r\n\x1a\n"


# ---- supports ----

def test_supports_image(renderer):
    assert renderer.supports("image") is True

def test_does_not_support_excel(renderer):
    assert renderer.supports("excel") is False


# ---- original chart types ----

def test_render_bar_chart(renderer, sample_data):
    result = renderer.render(_make_spec("bar"), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert _is_valid_png(result[len(IMAGE_PREFIX):])

def test_render_line_chart(renderer, sample_data):
    result = renderer.render(_make_spec("line"), sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_scatter_chart(renderer, sample_data):
    result = renderer.render(_make_spec("scatter"), sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_pie_chart(renderer, sample_data):
    spec = _make_spec("pie", aggregation=Aggregation(field="rating", op="avg"))
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)


# ---- new chart types ----

def test_render_horizontal_bar(renderer, sample_data):
    result = renderer.render(_make_spec("horizontal_bar"), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert _is_valid_png(result[len(IMAGE_PREFIX):])

def test_render_stacked_bar(renderer, sample_data):
    spec = _make_spec("stacked_bar", y2_field="price_single")
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_stacked_bar_no_y2(renderer, sample_data):
    # Should still render with just y field
    result = renderer.render(_make_spec("stacked_bar"), sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_grouped_bar(renderer, sample_data):
    spec = _make_spec("grouped_bar", y2_field="price_single")
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_area_chart(renderer, sample_data):
    result = renderer.render(_make_spec("area"), sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_area_chart_with_y2(renderer, sample_data):
    spec = _make_spec("area", y2_field="price_single")
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_donut_chart(renderer, sample_data):
    spec = _make_spec("donut", aggregation=Aggregation(field="available_rooms", op="sum"))
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_histogram(renderer, sample_data):
    result = renderer.render(_make_spec("histogram"), sample_data)
    assert result.startswith(IMAGE_PREFIX)

def test_render_histogram_empty_data(renderer):
    result = renderer.render(_make_spec("histogram"), [])
    assert result.startswith(IMAGE_PREFIX)


# ---- edge cases ----

def test_render_with_empty_data(renderer):
    result = renderer.render(_make_spec("bar"), [])
    assert result.startswith(IMAGE_PREFIX)

def test_render_multi_chart_grid(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(type="bar",  x=Axis(field="town", type="dimension"), y=Axis(field="rating", type="measure"), title="Ratings"),
            Chart(type="line", x=Axis(field="town", type="dimension"), y=Axis(field="price_single", type="measure"), title="Prices"),
            Chart(type="donut", x=Axis(field="town", type="dimension"), y=Axis(field="available_rooms", type="measure"),
                  aggregation=Aggregation(field="available_rooms", op="sum"), title="Rooms"),
            Chart(type="horizontal_bar", x=Axis(field="town", type="dimension"), y=Axis(field="rating", type="measure"), title="H-Bar"),
        ],
        layout="grid",
        output="image",
    )
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert _is_valid_png(result[len(IMAGE_PREFIX):])
