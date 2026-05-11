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
    type: Literal["bar", "line", "scatter", "pie"]
    x: Axis
    y: Axis
    aggregation: Optional[Aggregation] = None
    title: Optional[str] = None


class Filter(BaseModel):
    field: str
    op: Literal["=", ">", "<", "in"]
    value: str


class VisualizationSpec(BaseModel):
    charts: List[Chart]
    filters: Optional[List[Filter]] = None
    layout: Optional[Literal["single", "grid", "dashboard"]] = None
    output: Literal["image", "excel", "tableau"]
