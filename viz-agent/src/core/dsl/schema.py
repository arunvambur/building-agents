# core/dsl/schema.py

from typing import List, Literal, Optional

from pydantic import BaseModel


class Aggregation(BaseModel):
    field: str
    op: Literal["sum", "avg", "count", "min", "max"]


class Axis(BaseModel):
    field: str
    type: Literal["dimension", "measure", "time"]


class Chart(BaseModel):
    type: Literal[
        # Original
        "bar", "line", "scatter", "pie",
        # High value
        "horizontal_bar", "stacked_bar", "area", "donut", "grouped_bar", "histogram",
        # Medium value
        "heatmap", "bubble", "waterfall", "gauge",
    ]
    x: Axis
    y: Axis
    y2: Optional[Axis] = None
    aggregation: Optional[Aggregation] = None
    title: Optional[str] = None


class MapSpec(BaseModel):
    """
    Specification for a geographic map visualization.
    All field names reference columns in the data records.
    """
    map_type: Literal["marker", "bubble", "heatmap"] = "marker"
    lat_field: str = "latitude"
    lon_field: str = "longitude"
    label_field: str = "hotel_name"          # text shown in marker popup / tooltip
    color_field: Optional[str] = None        # categorical field → distinct marker colours
    size_field: Optional[str] = None         # numeric field → bubble radius (bubble maps)
    intensity_field: Optional[str] = None    # numeric field → heatmap intensity
    title: Optional[str] = None


class Filter(BaseModel):
    field: str
    op: Literal["=", ">", "<", "in"]
    value: str


class VisualizationSpec(BaseModel):
    # Standard chart spec — used for all non-map outputs
    charts: Optional[List[Chart]] = None
    # Map spec — used when output == "map"
    map_spec: Optional[MapSpec] = None
    filters: Optional[List[Filter]] = None
    layout: Optional[Literal["single", "grid", "dashboard"]] = None
    output: Literal["image", "excel", "pdf", "ppt", "map", "tableau"]
