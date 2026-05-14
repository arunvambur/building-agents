import os

import pytest

from core.dsl.schema import Aggregation, Axis, Chart, Filter, VisualizationSpec
from core.renderer.pdf.pdf import PDFRenderer

FILE_PREFIX = "file://"


def strip_prefix(result: str) -> str:
    assert result.startswith(FILE_PREFIX)
    return result[len(FILE_PREFIX):]


@pytest.fixture
def renderer():
    return PDFRenderer()


@pytest.fixture
def sample_data():
    return [
        {"town": "St Ives",  "rating": 4.8, "price_single": 140.0, "available_rooms": 6},
        {"town": "Newquay",  "rating": 4.5, "price_single": 120.0, "available_rooms": 5},
        {"town": "Falmouth", "rating": 4.2, "price_single": 95.0,  "available_rooms": 2},
        {"town": "Penzance", "rating": 4.7, "price_single": 130.0, "available_rooms": 3},
    ]


@pytest.fixture
def bar_spec():
    return VisualizationSpec(
        charts=[Chart(
            type="bar",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="rating", type="measure"),
            aggregation=Aggregation(field="rating", op="avg"),
            title="Avg Rating by Town",
        )],
        output="pdf",
    )


def test_supports_pdf(renderer):
    assert renderer.supports("pdf") is True


def test_does_not_support_excel(renderer):
    assert renderer.supports("excel") is False


def test_render_returns_file_prefix(renderer, bar_spec, sample_data):
    result = renderer.render(bar_spec, sample_data)
    assert result.startswith(FILE_PREFIX)


def test_render_creates_pdf_file(renderer, bar_spec, sample_data):
    path = strip_prefix(renderer.render(bar_spec, sample_data))
    assert path.endswith(".pdf")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000
    os.remove(path)


def test_render_with_empty_data(renderer, bar_spec):
    path = strip_prefix(renderer.render(bar_spec, []))
    assert os.path.exists(path)
    os.remove(path)


def test_render_line_chart(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[Chart(
            type="line",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="price_single", type="measure"),
            title="Price Trend",
        )],
        output="pdf",
    )
    path = strip_prefix(renderer.render(spec, sample_data))
    assert os.path.exists(path)
    os.remove(path)


def test_render_with_filters(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[Chart(
            type="bar",
            x=Axis(field="town", type="dimension"),
            y=Axis(field="rating", type="measure"),
            title="Filtered Ratings",
        )],
        filters=[Filter(field="rating", op=">", value="4.3")],
        output="pdf",
    )
    path = strip_prefix(renderer.render(spec, sample_data))
    assert os.path.exists(path)
    os.remove(path)


def test_render_multi_chart(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(type="bar", x=Axis(field="town", type="dimension"),
                  y=Axis(field="rating", type="measure"), title="Ratings"),
            Chart(type="line", x=Axis(field="town", type="dimension"),
                  y=Axis(field="price_single", type="measure"), title="Prices"),
        ],
        layout="grid",
        output="pdf",
    )
    path = strip_prefix(renderer.render(spec, sample_data))
    assert os.path.exists(path)
    os.remove(path)
