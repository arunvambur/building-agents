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
        {"town": "St Ives", "rating": 4.8, "price_single": 140.0, "available_rooms": 6},
        {"town": "Newquay", "rating": 4.5, "price_single": 120.0, "available_rooms": 5},
        {"town": "Falmouth", "rating": 4.2, "price_single": 95.0, "available_rooms": 2},
        {"town": "Penzance", "rating": 4.7, "price_single": 130.0, "available_rooms": 3},
    ]


def _make_spec(chart_type, output="image", aggregation=None):
    return VisualizationSpec(
        charts=[
            Chart(
                type=chart_type,
                x=Axis(field="town", type="dimension"),
                y=Axis(field="rating", type="measure"),
                aggregation=aggregation,
                title=f"{chart_type.title()} Chart",
            )
        ],
        filters=None,
        layout="single",
        output=output,
    )


def test_supports_image(renderer):
    assert renderer.supports("image") is True


def test_does_not_support_excel(renderer):
    assert renderer.supports("excel") is False


def test_render_returns_base64_prefix(renderer, sample_data):
    result = renderer.render(_make_spec("bar"), sample_data)
    assert result.startswith(IMAGE_PREFIX)


def test_render_base64_is_valid_png(renderer, sample_data):
    result = renderer.render(_make_spec("bar"), sample_data)
    b64 = result[len(IMAGE_PREFIX):]
    raw = base64.b64decode(b64)
    # PNG magic bytes
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_bar_chart(renderer, sample_data):
    result = renderer.render(_make_spec("bar"), sample_data)
    assert result.startswith(IMAGE_PREFIX)
    assert len(result) > 1000  # non-trivial image


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


def test_render_with_empty_data(renderer):
    result = renderer.render(_make_spec("bar"), [])
    assert result.startswith(IMAGE_PREFIX)


def test_render_multi_chart_grid(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(type="bar", x=Axis(field="town", type="dimension"),
                  y=Axis(field="rating", type="measure"), title="Ratings"),
            Chart(type="line", x=Axis(field="town", type="dimension"),
                  y=Axis(field="price_single", type="measure"), title="Prices"),
        ],
        filters=None,
        layout="grid",
        output="image",
    )
    result = renderer.render(spec, sample_data)
    assert result.startswith(IMAGE_PREFIX)
