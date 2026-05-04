# core/dsl/schema.py

from pydantic import BaseModel
from typing import List, Optional, Literal

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
    aggregation: Optional[Aggregation]
    title: Optional[str]

class Filter(BaseModel):
    field: str
    op: Literal["=", ">", "<", "in"]
    value: str

class VisualizationSpec(BaseModel):
    charts: List[Chart]
    filters: Optional[List[Filter]]
    layout: Optional[Literal["single", "grid", "dashboard"]]
    output: Literal["pdf", "excel", "tableau"]