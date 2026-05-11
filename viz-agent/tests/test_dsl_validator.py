import pytest

from core.dsl.schema import Aggregation, Axis, Chart, Filter, VisualizationSpec
from core.dsl.validator import SpecValidationError, validate_spec


def _make_spec(**overrides) -> VisualizationSpec:
    defaults = dict(
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
    defaults.update(overrides)
    return VisualizationSpec(**defaults)


def test_valid_spec_passes():
    validate_spec(_make_spec())


def test_empty_charts_raises():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_spec(charts=[]))
    assert "At least one chart" in str(exc.value)


def test_same_x_y_field_raises():
    chart = Chart(
        type="bar",
        x=Axis(field="rating", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=None,
        title=None,
    )
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_spec(charts=[chart]))
    assert "same field" in str(exc.value)


def test_both_axes_measure_raises():
    chart = Chart(
        type="bar",
        x=Axis(field="price_single", type="measure"),
        y=Axis(field="price_double", type="measure"),
        aggregation=None,
        title=None,
    )
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_spec(charts=[chart]))
    assert "dimension or time" in str(exc.value)


def test_pie_without_aggregation_raises():
    chart = Chart(
        type="pie",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=None,
        title=None,
    )
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_spec(charts=[chart]))
    assert "aggregation" in str(exc.value)


def test_grid_layout_requires_two_charts():
    chart = Chart(
        type="bar",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=None,
        title=None,
    )
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_spec(charts=[chart], layout="grid"))
    assert "Grid layout" in str(exc.value)


def test_grid_layout_with_two_charts_passes():
    chart = Chart(
        type="bar",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=None,
        title=None,
    )
    validate_spec(_make_spec(charts=[chart, chart], layout="grid"))
