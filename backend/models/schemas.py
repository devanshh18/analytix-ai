"""
Analytix AI — Pydantic schemas for request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# ─── Enums ───────────────────────────────────────────────
class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    HISTOGRAM = "histogram"
    SCATTER = "scatter"
    AREA = "area"


class ColumnType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


# ─── Column Metadata ────────────────────────────────────
class ColumnInfo(BaseModel):
    name: str
    dtype: str
    col_type: ColumnType
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    sample_values: list[Any] = []


# ─── Upload ──────────────────────────────────────────────
class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    column_info: list[ColumnInfo]
    preview: list[dict[str, Any]]
    message: str = "Dataset uploaded and processed successfully"


# ─── KPI ─────────────────────────────────────────────────
class KPIItem(BaseModel):
    id: str
    label: str
    value: Any
    format: str = "number"  # number, currency, percent, text
    icon: str = "bar-chart"
    change: Optional[float] = None
    change_label: Optional[str] = None


# ─── Chart Config ────────────────────────────────────────
class ChartConfig(BaseModel):
    id: str
    title: str
    chart_type: ChartType
    x_column: str
    y_column: Optional[str] = None
    y_columns: Optional[list[str]] = None
    color_column: Optional[str] = None
    data: list[dict[str, Any]]
    description: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None


# ─── Dashboard Config ───────────────────────────────────
class DashboardConfig(BaseModel):
    dataset_id: str
    title: str
    kpis: list[KPIItem]
    charts: list[ChartConfig]
    filters: list[dict[str, Any]] = []
    insights: list[str] = []


# ─── Insight ─────────────────────────────────────────────
class InsightItem(BaseModel):
    id: str
    category: str  # trend, anomaly, comparison, summary
    title: str
    description: str
    importance: str = "medium"  # low, medium, high
    related_columns: list[str] = []


# ─── Chat ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    dataset_id: str
    message: str
    conversation_history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    reply: str
    response_type: str = "text"  # text, chart, table, kpi
    chart_update: Optional[ChartConfig] = None
    new_chart: Optional[ChartConfig] = None
    data_result: Optional[list[dict[str, Any]]] = None
    chart_data: Optional[dict[str, Any]] = None  # Inline chart for chat rendering
    kpi_result: Optional[dict[str, Any]] = None  # {label, value, format}
    insight: Optional[str] = None
    action_type: str = "text"  # legacy compat: text, chart_update, new_chart, data_table, insight


# ─── Export ──────────────────────────────────────────────
class ExportRequest(BaseModel):
    dataset_id: str
    format: str = "pdf"  # pdf, pptx, png
    include_insights: bool = True
    include_charts: bool = True
