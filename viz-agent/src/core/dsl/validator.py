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
    """
    errors: List[str] = []

    if not spec.charts:
        errors.append("At least one chart is required.")

    for i, chart in enumerate(spec.charts):
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

    if spec.layout == "grid" and len(spec.charts) < 2:
        errors.append("Grid layout requires at least 2 charts.")

    if spec.layout == "dashboard" and len(spec.charts) < 2:
        errors.append("Dashboard layout requires at least 2 charts.")

    if errors:
        raise SpecValidationError(errors)
