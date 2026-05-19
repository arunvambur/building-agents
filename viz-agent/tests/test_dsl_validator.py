import pytest

from core.dsl.schema import Aggregation, Axis, Chart, Filter, MapSpec, VisualizationSpec
from core.dsl.validator import SpecValidationError, validate_spec


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_chart_spec(**overrides) -> VisualizationSpec:
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


def _make_map_spec(**overrides) -> VisualizationSpec:
    defaults = dict(
        map_spec=MapSpec(
            map_type="marker",
            lat_field="latitude",
            lon_field="longitude",
            label_field="hotel_name",
        ),
        output="map",
    )
    defaults.update(overrides)
    return VisualizationSpec(**defaults)


# ── chart validation ──────────────────────────────────────────────────────────

def test_valid_chart_spec_passes():
    validate_spec(_make_chart_spec())


def test_empty_charts_raises():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_chart_spec(charts=[]))
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
        validate_spec(_make_chart_spec(charts=[chart]))
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
        validate_spec(_make_chart_spec(charts=[chart]))
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
        validate_spec(_make_chart_spec(charts=[chart]))
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
        validate_spec(_make_chart_spec(charts=[chart], layout="grid"))
    assert "Grid layout" in str(exc.value)


def test_grid_layout_with_two_charts_passes():
    chart = Chart(
        type="bar",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=None,
        title=None,
    )
    validate_spec(_make_chart_spec(charts=[chart, chart], layout="grid"))


# ── map validation ────────────────────────────────────────────────────────────

def test_valid_marker_map_spec_passes():
    validate_spec(_make_map_spec())


def test_valid_bubble_map_spec_passes():
    validate_spec(_make_map_spec(
        map_spec=MapSpec(
            map_type="bubble",
            lat_field="latitude",
            lon_field="longitude",
            label_field="hotel_name",
            size_field="monthly_revenue",
        )
    ))


def test_valid_heatmap_spec_passes():
    validate_spec(_make_map_spec(
        map_spec=MapSpec(
            map_type="heatmap",
            lat_field="latitude",
            lon_field="longitude",
            label_field="hotel_name",
            intensity_field="occupancy_rate",
        )
    ))


def test_map_output_without_map_spec_raises():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(VisualizationSpec(output="map"))
    assert "map_spec" in str(exc.value)


def test_bubble_map_without_size_field_raises():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_map_spec(
            map_spec=MapSpec(
                map_type="bubble",
                lat_field="latitude",
                lon_field="longitude",
                label_field="hotel_name",
                # size_field intentionally omitted
            )
        ))
    assert "size_field" in str(exc.value)


def test_heatmap_without_intensity_or_size_field_raises():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(_make_map_spec(
            map_spec=MapSpec(
                map_type="heatmap",
                lat_field="latitude",
                lon_field="longitude",
                label_field="hotel_name",
                # intensity_field and size_field intentionally omitted
            )
        ))
    assert "intensity_field" in str(exc.value)


def test_map_spec_skips_chart_validation():
    """Map output must not trigger chart validation even when charts is None."""
    spec = VisualizationSpec(
        map_spec=MapSpec(
            lat_field="latitude",
            lon_field="longitude",
            label_field="hotel_name",
        ),
        output="map",
    )
    # Should not raise — charts is None but output is map
    validate_spec(spec)
