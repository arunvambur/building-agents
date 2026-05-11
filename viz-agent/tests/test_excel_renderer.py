import os

import pytest

from core.dsl.schema import Aggregation, Axis, Chart, Filter, VisualizationSpec
from core.renderer.excel.excel import ExcelRenderer


@pytest.fixture
def renderer():
    return ExcelRenderer()


@pytest.fixture
def sample_data():
    return [
        {"town": "St Ives", "rating": 4.8, "price_single": 140.0, "available_rooms": 6},
        {"town": "Newquay", "rating": 4.5, "price_single": 120.0, "available_rooms": 5},
        {"town": "Falmouth", "rating": 4.2, "price_single": 95.0, "available_rooms": 2},
    ]


@pytest.fixture
def bar_spec():
    return VisualizationSpec(
        charts=[
            Chart(
                type="bar",
                x=Axis(field="town", type="dimension"),
                y=Axis(field="rating", type="measure"),
                aggregation=Aggregation(field="rating", op="avg"),
                title="Avg Rating by Town",
            )
        ],
        filters=None,
        layout="single",
        output="excel",
    )


def test_supports_excel(renderer):
    assert renderer.supports("excel") is True


def test_does_not_support_tableau(renderer):
    assert renderer.supports("tableau") is False


def test_render_returns_file_path(renderer, bar_spec, sample_data):
    path = renderer.render(bar_spec, sample_data)
    assert path.endswith(".xlsx")
    assert os.path.exists(path)
    os.remove(path)


def test_render_creates_correct_sheet_name(renderer, bar_spec, sample_data):
    import openpyxl
    path = renderer.render(bar_spec, sample_data)
    wb = openpyxl.load_workbook(path)
    assert "Avg Rating by Town" in wb.sheetnames
    os.remove(path)


def test_render_with_filters_creates_filter_sheet(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(
                type="bar",
                x=Axis(field="town", type="dimension"),
                y=Axis(field="rating", type="measure"),
                aggregation=None,
                title="Filtered Chart",
            )
        ],
        filters=[Filter(field="rating", op=">", value="4.0")],
        layout="single",
        output="excel",
    )
    import openpyxl
    path = renderer.render(spec, sample_data)
    wb = openpyxl.load_workbook(path)
    assert "Filters Applied" in wb.sheetnames
    os.remove(path)


def test_render_with_empty_data(renderer, bar_spec):
    path = renderer.render(bar_spec, [])
    assert os.path.exists(path)
    os.remove(path)


def test_render_line_chart(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(
                type="line",
                x=Axis(field="town", type="dimension"),
                y=Axis(field="price_single", type="measure"),
                aggregation=None,
                title="Price Trend",
            )
        ],
        filters=None,
        layout="single",
        output="excel",
    )
    path = renderer.render(spec, sample_data)
    assert os.path.exists(path)
    os.remove(path)


def test_render_pie_chart(renderer, sample_data):
    spec = VisualizationSpec(
        charts=[
            Chart(
                type="pie",
                x=Axis(field="town", type="dimension"),
                y=Axis(field="available_rooms", type="measure"),
                aggregation=Aggregation(field="available_rooms", op="sum"),
                title="Room Distribution",
            )
        ],
        filters=None,
        layout="single",
        output="excel",
    )
    path = renderer.render(spec, sample_data)
    assert os.path.exists(path)
    os.remove(path)
