"""
Analytix AI — LLM-Driven Analytics Engine.
Uses Groq LLM for intelligent KPI, chart, and dashboard generation.
Falls back to rule-based logic if LLM is unavailable.
Dashboard generation is deterministic (temperature=0) and cached by dataset hash.
"""
import hashlib
import pandas as pd
import numpy as np
import logging
from typing import Any
from models.schemas import (
    KPIItem, ChartConfig, ChartType, ColumnType,
    DashboardConfig,
)
from ai.llm_service import get_llm_service, GroqLLM
from ai.prompts import (
    ANALYST_SYSTEM, DATASET_ANALYSIS_PROMPT,
    KPI_GENERATION_PROMPT, CHART_GENERATION_PROMPT,
)
from utils.helpers import generate_id

logger = logging.getLogger(__name__)

# Cache: dataset hash → DashboardConfig (same data = same dashboard)
_dashboard_cache: dict[str, DashboardConfig] = {}


class AnalyticsEngine:
    """LLM-driven analytics engine. LLM decides what to show, Pandas executes."""

    def __init__(self):
        self.llm = get_llm_service()

    @staticmethod
    def _hash_dataframe(df: pd.DataFrame) -> str:
        """Create a stable hash of the dataframe content for caching."""
        # Hash columns + shape + first 100 rows of data for speed
        content = f"{list(df.columns)}|{df.shape}|{df.head(100).to_csv(index=False)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ─── Metadata Extraction ────────────────────────────
    def _build_metadata(self, df: pd.DataFrame, col_types: dict, filename: str = "") -> dict:
        """Build a comprehensive metadata dict for LLM prompts."""
        # Column info
        columns_info = []
        for col in df.columns:
            ct = col_types.get(col, ColumnType.TEXT)
            ct_str = ct.value if hasattr(ct, 'value') else str(ct)
            info = f"{col} ({ct_str})"
            if ct_str == "numeric":
                info += f" — min: {df[col].min():.2f}, max: {df[col].max():.2f}, mean: {df[col].mean():.2f}"
            elif ct_str == "categorical":
                uniq = df[col].nunique()
                top = df[col].value_counts().head(3).to_dict()
                top_str = ", ".join(f"{k}({v})" for k, v in top.items())
                info += f" — {uniq} unique, top: {top_str}"
            columns_info.append(info)

        # Numeric stats
        numeric_cols = [c for c, t in col_types.items()
                        if (hasattr(t, 'value') and t.value == "numeric") or str(t) == "numeric"]
        numeric_stats = ""
        if numeric_cols:
            desc = df[numeric_cols].describe().round(2)
            numeric_stats = desc.to_string()

        # Categorical stats
        cat_cols = [c for c, t in col_types.items()
                    if (hasattr(t, 'value') and t.value == "categorical") or str(t) == "categorical"]
        cat_stats_lines = []
        for col in cat_cols[:5]:
            vc = df[col].value_counts().head(5)
            cat_stats_lines.append(f"{col}: {dict(vc)}")
        categorical_stats = "\n".join(cat_stats_lines) if cat_stats_lines else "No categorical columns."

        # Sample rows
        sample = df.head(3).to_string(index=False)

        return {
            "filename": filename,
            "row_count": len(df),
            "col_count": len(df.columns),
            "columns_info": "\n".join(columns_info),
            "numeric_stats": numeric_stats,
            "categorical_stats": categorical_stats,
            "sample_rows": sample,
        }

    # ─── LLM: Dataset Analysis ──────────────────────────
    def analyze_dataset(self, df: pd.DataFrame, col_types: dict, filename: str = "") -> dict:
        """Use LLM to understand the dataset's business context."""
        meta = self._build_metadata(df, col_types, filename)

        if not isinstance(self.llm, GroqLLM):
            return {
                "purpose": f"Dataset from {filename}",
                "domain": "General",
                "target_variable": None,
                "important_columns": list(df.columns[:5]),
                "key_relationships": [],
                "dashboard_title": self._title_from_filename(filename),
            }

        try:
            prompt = DATASET_ANALYSIS_PROMPT.format(**meta)
            result = self.llm.generate_json(prompt, ANALYST_SYSTEM, temperature=0)
            return result
        except Exception as e:
            logger.error(f"LLM dataset analysis failed: {e}")
            return {
                "purpose": f"Dataset from {filename}",
                "domain": "General",
                "target_variable": None,
                "important_columns": list(df.columns[:5]),
                "key_relationships": [],
                "dashboard_title": self._title_from_filename(filename),
            }

    # ─── LLM: KPI Generation ─────────────────────────────
    def generate_kpis(self, df: pd.DataFrame, col_types: dict,
                      dataset_context: str = "") -> list[KPIItem]:
        """Use LLM to decide meaningful KPIs, then calculate with Pandas."""
        meta = self._build_metadata(df, col_types)

        if not isinstance(self.llm, GroqLLM):
            return self._fallback_kpis(df, col_types)

        try:
            prompt = KPI_GENERATION_PROMPT.format(
                dataset_context=dataset_context,
                columns_info=meta["columns_info"],
                numeric_stats=meta["numeric_stats"],
                categorical_stats=meta["categorical_stats"],
            )
            result = self.llm.generate_json(prompt, ANALYST_SYSTEM, temperature=0)
            kpi_specs = result.get("kpis", []) if isinstance(result, dict) else result

            kpis = []
            for spec in kpi_specs[:8]:  # Limit to 8 KPIs
                kpi = self._execute_kpi(df, spec)
                if kpi:
                    kpis.append(kpi)

            # Enforce exactly 4 or 8 KPIs
            if len(kpis) > 4:
                kpis = kpis[:8]  # Cap at 8
                # If between 5-7, trim to 4 (cleaner grid)
                if len(kpis) < 8:
                    kpis = kpis[:4]
            elif len(kpis) < 4:
                # Pad with fallback KPIs
                fallbacks = self._fallback_kpis(df, col_types)
                for fb in fallbacks:
                    if len(kpis) >= 4:
                        break
                    if fb.label not in [k.label for k in kpis]:
                        kpis.append(fb)

            return kpis if kpis else self._fallback_kpis(df, col_types)

        except Exception as e:
            logger.error(f"LLM KPI generation failed: {e}")
            return self._fallback_kpis(df, col_types)

    def _execute_kpi(self, df: pd.DataFrame, spec: dict) -> KPIItem | None:
        """Safely execute a KPI calculation based on LLM spec."""
        try:
            label = spec.get("label", "Metric")
            calc_type = spec.get("type", "count")
            column = spec.get("column", "")
            fmt = spec.get("format", "number")
            icon = spec.get("icon", "bar-chart")
            filter_col = spec.get("filter_column")
            filter_val = spec.get("filter_value")

            SAFE_AGGS = {"mean", "sum", "count", "median", "min", "max",
                         "unique_count", "percentage", "ratio", "nunique", "std"}

            if calc_type not in SAFE_AGGS and calc_type != "custom":
                calc_type = "count"

            value = None

            if calc_type == "percentage" and filter_col and filter_val is not None:
                if filter_col in df.columns:
                    # Robust matching: try multiple comparison strategies
                    filter_str = str(filter_val).strip()
                    col_series = df[filter_col]
                    # Try exact string match first
                    match_count = len(df[col_series.astype(str).str.strip() == filter_str])
                    # If no match, try numeric comparison (handles 1 vs 1.0 vs "1")
                    if match_count == 0:
                        try:
                            filter_num = float(filter_val)
                            match_count = len(df[col_series == filter_num])
                            if match_count == 0:
                                match_count = len(df[col_series == int(filter_num)])
                        except (ValueError, TypeError):
                            pass
                    value = round(match_count / len(df) * 100, 1) if len(df) > 0 else 0
                    fmt = "percent"

            elif calc_type == "ratio" and "|" in column:
                cols = column.split("|")
                if len(cols) == 2 and cols[0].strip() in df.columns and cols[1].strip() in df.columns:
                    val1 = df[cols[0].strip()].mean()
                    val2 = df[cols[1].strip()].mean()
                    value = round(float(val1 / val2), 2) if val2 != 0 else 0

            elif calc_type == "unique_count" or calc_type == "nunique":
                if column in df.columns:
                    value = int(df[column].nunique())
                    fmt = "integer"

            elif column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
                agg_map = {
                    "mean": df[column].mean,
                    "sum": df[column].sum,
                    "count": lambda: len(df[column].dropna()),
                    "median": df[column].median,
                    "min": df[column].min,
                    "max": df[column].max,
                    "std": df[column].std,
                }
                func = agg_map.get(calc_type, lambda: len(df))
                raw = func()
                value = round(float(raw), 2) if pd.notna(raw) else 0

            elif calc_type == "count":
                if filter_col and filter_val and filter_col in df.columns:
                    value = int(len(df[df[filter_col].astype(str) == str(filter_val)]))
                elif column in df.columns:
                    value = int(df[column].count())
                else:
                    value = len(df)
                fmt = "integer"

            if value is None:
                return None

            # Format display value
            if fmt == "percent":
                display = f"{value}%"
            elif fmt == "currency":
                display = f"${value:,.2f}"
            elif fmt == "integer":
                display = f"{int(value):,}"
            else:
                display = f"{value:,.2f}" if isinstance(value, float) else str(value)

            return KPIItem(
                id=generate_id(),
                label=label,
                value=display,
                format=fmt,
                icon=icon,
            )
        except Exception as e:
            logger.warning(f"KPI execution failed for {spec.get('label', '?')}: {e}")
            return None

    # ─── LLM: Chart Generation ──────────────────────────
    def suggest_charts(self, df: pd.DataFrame, col_types: dict,
                       dataset_context: str = "") -> list[ChartConfig]:
        """Use LLM to decide meaningful charts, then generate data with Pandas."""
        meta = self._build_metadata(df, col_types)

        if not isinstance(self.llm, GroqLLM):
            return self._fallback_charts(df, col_types)

        try:
            prompt = CHART_GENERATION_PROMPT.format(
                dataset_context=dataset_context,
                columns_info=meta["columns_info"],
            )
            result = self.llm.generate_json(prompt, ANALYST_SYSTEM, temperature=0)
            chart_specs = result.get("charts", []) if isinstance(result, dict) else result

            charts = []
            for spec in chart_specs[:8]:
                chart = self._execute_chart(df, col_types, spec)
                if chart:
                    charts.append(chart)

            return charts if charts else self._fallback_charts(df, col_types)

        except Exception as e:
            logger.error(f"LLM chart generation failed: {e}")
            return self._fallback_charts(df, col_types)

    def _execute_chart(self, df: pd.DataFrame, col_types: dict,
                       spec: dict) -> ChartConfig | None:
        """Safely generate chart data based on LLM spec."""
        try:
            title = spec.get("title", "Chart")
            chart_type_str = spec.get("chart_type", "bar")
            x_col = spec.get("x_column", "")
            y_col = spec.get("y_column", "count")
            agg = spec.get("aggregation", "mean")
            desc = spec.get("description", "")
            top_n = min(spec.get("top_n") or 15, 30)

            # Validate columns exist
            if x_col not in df.columns:
                return None

            # Map chart type
            type_map = {
                "bar": ChartType.BAR, "line": ChartType.LINE, "pie": ChartType.PIE,
                "histogram": ChartType.HISTOGRAM, "scatter": ChartType.SCATTER,
                "area": ChartType.AREA,
            }
            chart_type = type_map.get(chart_type_str, ChartType.BAR)

            # Generate data based on chart type and aggregation
            data = []

            if chart_type == ChartType.PIE:
                data = self._prepare_pie_data(df, x_col)

            elif chart_type == ChartType.HISTOGRAM:
                data = self._prepare_histogram(df, x_col)

            elif chart_type == ChartType.SCATTER:
                if y_col in df.columns and y_col != "count":
                    data = self._prepare_scatter(df, x_col, y_col)

            elif chart_type in (ChartType.LINE, ChartType.AREA):
                ct = col_types.get(x_col)
                ct_str = ct.value if hasattr(ct, 'value') else str(ct)
                if ct_str == "datetime" and y_col in df.columns:
                    data = self._prepare_time_series(df, x_col, y_col)
                elif y_col in df.columns and y_col != "count":
                    data = self._prepare_bar_data(df, x_col, y_col, agg, top_n)

            elif chart_type == ChartType.BAR:
                if y_col in df.columns and y_col != "count":
                    data = self._prepare_bar_data(df, x_col, y_col, agg, top_n)
                else:
                    # Value counts
                    vc = df[x_col].value_counts().head(top_n)
                    data = [{x_col: str(k), "count": int(v)} for k, v in vc.items()]
                    y_col = "count"

            if not data:
                return None

            return ChartConfig(
                id=generate_id(),
                title=title,
                chart_type=chart_type,
                x_column=x_col,
                y_column=y_col if y_col != "count" or chart_type == ChartType.HISTOGRAM else "count",
                data=data,
                description=desc,
                x_label=self._humanize(x_col),
                y_label=self._humanize(y_col) if y_col != "count" else "Count",
            )
        except Exception as e:
            logger.warning(f"Chart execution failed for {spec.get('title', '?')}: {e}")
            return None

    # ─── Filter Suggestions (rule-based, works fine) ─────
    def generate_filters(self, df: pd.DataFrame, col_types: dict[str, ColumnType]) -> list[dict[str, Any]]:
        """Generate filter configurations for dashboard controls."""
        filters = []

        dt_cols = [c for c, t in col_types.items() if t == ColumnType.DATETIME and c in df.columns]
        for col in dt_cols[:1]:
            min_date = df[col].min()
            max_date = df[col].max()
            if pd.notna(min_date) and pd.notna(max_date):
                filters.append({
                    "id": generate_id(), "column": col,
                    "label": self._humanize(col), "type": "date_range",
                    "min": str(min_date.date()) if hasattr(min_date, "date") else str(min_date),
                    "max": str(max_date.date()) if hasattr(max_date, "date") else str(max_date),
                })

        cat_cols = [c for c, t in col_types.items() if t == ColumnType.CATEGORICAL and c in df.columns]
        for col in cat_cols[:3]:
            options = sorted(df[col].dropna().unique().tolist())
            if len(options) <= 30:
                filters.append({
                    "id": generate_id(), "column": col,
                    "label": self._humanize(col), "type": "select",
                    "options": [str(o) for o in options],
                })

        return filters

    # ─── Dashboard Config ────────────────────────────────
    def generate_dashboard(self, df: pd.DataFrame, col_types: dict[str, ColumnType],
                           dataset_id: str, filename: str = "") -> DashboardConfig:
        """Generate a complete LLM-driven dashboard. Deterministic + cached."""
        global _dashboard_cache

        # Check cache: same data → same dashboard (different dataset_id is fine)
        df_hash = self._hash_dataframe(df)
        if df_hash in _dashboard_cache:
            logger.info(f"Dashboard cache hit for hash {df_hash}")
            cached = _dashboard_cache[df_hash]
            # Return a copy with the new dataset_id
            return DashboardConfig(
                dataset_id=dataset_id,
                title=cached.title,
                kpis=cached.kpis,
                charts=cached.charts,
                filters=cached.filters,
            )

        # Step 1: LLM analyzes the dataset (temperature=0 for determinism)
        analysis = self.analyze_dataset(df, col_types, filename)
        dataset_context = (
            f"Purpose: {analysis.get('purpose', 'Unknown')}\n"
            f"Domain: {analysis.get('domain', 'General')}\n"
            f"Target variable: {analysis.get('target_variable', 'None')}\n"
            f"Important columns: {', '.join(analysis.get('important_columns', []))}\n"
            f"Key relationships: {'; '.join(analysis.get('key_relationships', []))}"
        )

        # Step 2: LLM-driven KPIs (temperature=0)
        kpis = self.generate_kpis(df, col_types, dataset_context)

        # Step 3: LLM-driven charts (temperature=0)
        charts = self.suggest_charts(df, col_types, dataset_context)

        # Step 4: Rule-based filters (always reliable)
        filters = self.generate_filters(df, col_types)

        # Title from LLM analysis or filename
        title = analysis.get("dashboard_title") or self._title_from_filename(filename)

        dashboard = DashboardConfig(
            dataset_id=dataset_id,
            title=title,
            kpis=kpis,
            charts=charts,
            filters=filters,
        )

        # Cache for future uploads of the same data
        _dashboard_cache[df_hash] = dashboard
        logger.info(f"Dashboard cached with hash {df_hash}")

        return dashboard

    # ─── Data Prep Helpers ───────────────────────────────
    def _prepare_time_series(self, df: pd.DataFrame, dt_col: str, num_col: str,
                              max_points: int = 50) -> list[dict]:
        try:
            temp = df[[dt_col, num_col]].dropna().copy()
            if temp.empty:
                return []
            temp[dt_col] = pd.to_datetime(temp[dt_col], errors="coerce")
            temp = temp.dropna()
            if len(temp) > max_points:
                temp = temp.set_index(dt_col).resample("M").mean().reset_index()
            temp[dt_col] = temp[dt_col].dt.strftime("%Y-%m-%d")
            temp[num_col] = temp[num_col].round(2)
            return temp.head(max_points).to_dict(orient="records")
        except Exception:
            return []

    def _prepare_bar_data(self, df: pd.DataFrame, cat_col: str, num_col: str,
                           agg: str = "mean", top_n: int = 15) -> list[dict]:
        try:
            SAFE_AGGS = {"mean", "sum", "count", "median", "min", "max"}
            agg = agg if agg in SAFE_AGGS else "mean"
            grouped = df.groupby(cat_col)[num_col].agg(agg).sort_values(ascending=False).head(top_n)
            return [{cat_col: str(k), num_col: round(float(v), 2)} for k, v in grouped.items()]
        except Exception:
            return []

    def _prepare_histogram(self, df: pd.DataFrame, num_col: str, bins: int = 20) -> list[dict]:
        try:
            series = pd.to_numeric(df[num_col], errors='coerce').dropna()
            if series.empty or len(series) < 2:
                return []
            n_bins = max(2, min(bins, len(series.unique())))
            counts, bin_edges = np.histogram(series.values, bins=n_bins)
            return [
                {num_col: f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}", "count": int(counts[i])}
                for i in range(len(counts))
            ]
        except Exception:
            return []

    def _prepare_pie_data(self, df: pd.DataFrame, cat_col: str) -> list[dict]:
        try:
            vc = df[cat_col].value_counts().head(8)
            return [{"name": str(k), "value": int(v)} for k, v in vc.items()]
        except Exception:
            return []

    def _prepare_scatter(self, df: pd.DataFrame, col_x: str, col_y: str,
                          max_points: int = 200) -> list[dict]:
        try:
            temp = df[[col_x, col_y]].copy()
            temp[col_x] = pd.to_numeric(temp[col_x], errors='coerce')
            temp[col_y] = pd.to_numeric(temp[col_y], errors='coerce')
            temp = temp.dropna()
            if temp.empty:
                return []
            if len(temp) > max_points:
                temp = temp.sample(max_points, random_state=42)
            return [
                {col_x: round(float(r[col_x]), 4), col_y: round(float(r[col_y]), 4)}
                for _, r in temp.iterrows()
            ]
        except Exception:
            return []

    # ─── Fallback (rule-based) ───────────────────────────
    def _fallback_kpis(self, df: pd.DataFrame, col_types: dict) -> list[KPIItem]:
        """Generate basic KPIs when LLM is unavailable."""
        kpis = [
            KPIItem(id=generate_id(), label="Total Records", value=f"{len(df):,}", format="integer", icon="database"),
            KPIItem(id=generate_id(), label="Total Columns", value=str(len(df.columns)), format="integer", icon="columns"),
        ]
        numeric_cols = [c for c, t in col_types.items()
                        if (hasattr(t, 'value') and t.value == "numeric") or str(t) == "numeric"]
        for col in numeric_cols[:3]:
            mean_val = df[col].mean()
            if pd.notna(mean_val):
                kpis.append(KPIItem(
                    id=generate_id(), label=f"Avg {self._humanize(col)}",
                    value=f"{round(float(mean_val), 2):,}", format="number", icon="trending-up",
                ))
        return kpis

    def _fallback_charts(self, df: pd.DataFrame, col_types: dict) -> list[ChartConfig]:
        """Generate basic charts when LLM is unavailable."""
        charts = []
        numeric_cols = [c for c, t in col_types.items()
                        if (hasattr(t, 'value') and t.value == "numeric") and c in df.columns]
        cat_cols = [c for c, t in col_types.items()
                    if (hasattr(t, 'value') and t.value == "categorical") and c in df.columns]

        if cat_cols and numeric_cols:
            data = self._prepare_bar_data(df, cat_cols[0], numeric_cols[0])
            if data:
                charts.append(ChartConfig(
                    id=generate_id(),
                    title=f"{self._humanize(numeric_cols[0])} by {self._humanize(cat_cols[0])}",
                    chart_type=ChartType.BAR, x_column=cat_cols[0], y_column=numeric_cols[0],
                    data=data, description="Bar chart comparison",
                ))

        for col in numeric_cols[:2]:
            data = self._prepare_histogram(df, col)
            if data:
                charts.append(ChartConfig(
                    id=generate_id(),
                    title=f"Distribution of {self._humanize(col)}",
                    chart_type=ChartType.HISTOGRAM, x_column=col, y_column="count",
                    data=data, description="Frequency distribution",
                ))

        return charts

    @staticmethod
    def _humanize(col_name: str) -> str:
        return col_name.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _title_from_filename(filename: str) -> str:
        if filename:
            name = filename.rsplit(".", 1)[0]
            name = name.replace("_", " ").replace("-", " ").strip().title()
            return f"{name} — Analytics Dashboard"
        return "Analytics Dashboard"
