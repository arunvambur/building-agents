from typing import List

from core.dsl.schema import VisualizationSpec


class SpecValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"VisualizationSpec validation failed: {'; '.join(errors)}")


def validate_spec(spec: VisualizationSpec) -> None:
    """
    Validates a VisualizationSpec beyond Pydantic field-level checks.
    Raises SpecValidationError if any semantic rules are violated.

    Map specs (output='map') are validated separately via MapSpec — chart
    validation is skipped entirely for map output.
    """
    # Map output uses map_spec, not charts — skip chart validation
    if spec.output == "map":
        _validate_map_spec(spec)
        return

    errors: List[str] = []

    if not spec.charts:
        errors.append("At least one chart is required.")

    for i, chart in enumerate(spec.charts or []):
        prefix = f"Chart[{i}]"

        if chart.x.field == chart.y.field:
            errors.append(f"{prefix}: x and y axes cannot reference the same field.")

        if chart.x.type == "measure" and chart.y.type == "measure":
            errors.append(
                f"{prefix}: at least one axis must be a dimension or time field "
                f"(both are currently 'measure')."
            )

        if chart.type == "pie":
            if chart.aggregation is None:
                errors.append(f"{prefix}: pie charts require an aggregation.")
            if chart.x.type != "dimension":
                errors.append(f"{prefix}: pie chart x-axis must be a dimension.")

    if spec.layout == "grid" and len(spec.charts or []) < 2:
        errors.append("Grid layout requires at least 2 charts.")

    if spec.layout == "dashboard" and len(spec.charts or []) < 2:
        errors.append("Dashboard layout requires at least 2 charts.")

    if errors:
        raise SpecValidationError(errors)


def _validate_map_spec(spec: VisualizationSpec) -> None:
    """Validates a map VisualizationSpec."""
    errors: List[str] = []

    if spec.map_spec is None:
        errors.append("Map output requires a map_spec.")
    else:
        ms = spec.map_spec
        if not ms.lat_field:
            errors.append("map_spec.lat_field is required.")
        if not ms.lon_field:
            errors.append("map_spec.lon_field is required.")
        if not ms.label_field:
            errors.append("map_spec.label_field is required.")
        if ms.map_type == "bubble" and not ms.size_field:
            errors.append("map_spec.size_field is required for bubble maps.")
        if ms.map_type == "heatmap" and not ms.intensity_field and not ms.size_field:
            errors.append(
                "map_spec.intensity_field (or size_field) is required for heatmap maps."
            )

    if errors:
        raise SpecValidationError(errors)
