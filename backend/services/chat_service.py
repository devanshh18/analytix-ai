"""
Analytix AI — Action-Driven Chat Service.
EXECUTION-FIRST: Think → Execute → Respond with actual results.
"""
import logging
import pandas as pd
import numpy as np
from typing import Any, Optional
from models.schemas import ChatResponse, ChartConfig, ChartType
from ai.llm_service import get_llm_service, GroqLLM
from ai.prompts import CHAT_SYSTEM, CHAT_RESPONSE_PROMPT
from utils.helpers import generate_id

logger = logging.getLogger(__name__)


class ChatService:
    """Action-driven chat: LLM decides intent, Pandas executes, returns results."""

    def __init__(self):
        self.llm = get_llm_service()

    def process_message(self, message: str, df: pd.DataFrame,
                        col_types: dict, current_charts: list[dict] = None,
                        conversation_history: list[dict] = None) -> ChatResponse:
        """Process a user message with execution-first approach."""

        if isinstance(self.llm, GroqLLM):
            try:
                return self._llm_execute(message, df, col_types,
                                         current_charts, conversation_history or [])
            except Exception as e:
                import traceback
                error_str = str(e)
                logger.error(f"LLM chat failed: {e}\n{traceback.format_exc()}")
                if "429" in error_str or "rate_limit" in error_str or "Rate limit exceeded" in error_str:
                    return ChatResponse(
                        reply=f"⚠️ AI rate limit reached. {error_str}",
                        response_type="text",
                        action_type="text",
                    )

        return self._fallback_execute(message, df, col_types)

    def _build_metadata(self, df: pd.DataFrame, col_types: dict) -> str:
        """Build compact metadata for LLM."""
        lines = [f"Rows: {len(df)}, Columns: {len(df.columns)}"]
        for col in df.columns:
            ct = col_types.get(col)
            ct_str = ct.value if hasattr(ct, 'value') else str(ct)
            if ct_str == "numeric":
                lines.append(f"  {col} (numeric): min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")
            elif ct_str == "categorical":
                uniq = df[col].nunique()
                top3 = list(df[col].value_counts().head(3).index)
                lines.append(f"  {col} (categorical): {uniq} unique, top: {top3}")
            else:
                lines.append(f"  {col} ({ct_str})")
        return "\n".join(lines)

    def _build_history_str(self, history: list[dict]) -> str:
        """Build conversation history string for prompt."""
        if not history:
            return "No previous messages."
        lines = []
        for msg in history[-10:]:  # Last 10 messages for full context
            role = msg.get("role", "user")
            content = msg.get("content", "")[:500]  # Keep more content for follow-ups
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _llm_execute(self, message: str, df: pd.DataFrame, col_types: dict,
                     current_charts: list[dict] = None,
                     history: list[dict] = None) -> ChatResponse:
        """LLM analyzes intent → Backend executes → Returns actual results."""
        metadata = self._build_metadata(df, col_types)
        history_str = self._build_history_str(history or [])

        prompt = CHAT_RESPONSE_PROMPT.format(
            question=message,
            history=history_str,
        )
        system = CHAT_SYSTEM.format(metadata=metadata)

        result = self.llm.generate_json(prompt, system, max_tokens=4096)

        response_type = result.get("response_type", "text")
        reply = result.get("reply", "Here are the results.")
        operation = result.get("operation") or {}
        chart_spec = result.get("chart_spec") or {}
        kpi_spec = result.get("kpi_value") or {}

        # ─── Execute based on response_type ──────────────
        if response_type == "kpi":
            return self._execute_kpi(df, col_types, reply, kpi_spec, operation)

        elif response_type == "chart":
            return self._execute_chart(df, col_types, reply, chart_spec)

        elif response_type == "table":
            return self._execute_table(df, col_types, reply, operation)

        else:
            return ChatResponse(reply=reply, response_type="text", action_type="text")

    # ─── KPI Execution ───────────────────────────────────
    def _execute_kpi(self, df: pd.DataFrame, col_types: dict,
                     reply: str, kpi_spec: dict, operation: dict) -> ChatResponse:
        """Calculate a KPI value and return it."""
        label = kpi_spec.get("label", "Metric")
        fmt = kpi_spec.get("format", "number")
        column = operation.get("column") or kpi_spec.get("column")
        op_type = operation.get("type", "aggregate")
        agg = operation.get("aggregation", "mean")

        value = None

        if column:
            column = self._match_column(column, df.columns.tolist()) or column

        # Calculate rate (e.g., churn rate = mean of binary column)
        if op_type == "calculate_rate" and column and column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                raw = df[column].mean()
                value = f"{round(raw * 100, 1)}%" if raw <= 1 else f"{round(raw, 2)}"
                fmt = "percent"

        # Standard aggregation
        elif column and column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            SAFE_AGGS = {"mean": df[column].mean, "sum": df[column].sum,
                         "count": df[column].count, "median": df[column].median,
                         "min": df[column].min, "max": df[column].max,
                         "std": df[column].std}
            func = SAFE_AGGS.get(agg, df[column].mean)
            raw = float(func())
            if fmt == "percent":
                value = f"{round(raw * 100, 1)}%"
            elif fmt == "currency":
                value = f"${raw:,.2f}"
            elif fmt == "integer":
                value = f"{int(raw):,}"
            else:
                value = f"{raw:,.2f}"

        # Count-based
        elif column and column in df.columns:
            value = f"{df[column].nunique():,}"
            label = label or f"Unique {self._humanize(column)}"

        # Fallback: try to use the LLM-provided value
        if value is None:
            value = kpi_spec.get("value", "N/A")

        kpi_result = {"label": label, "value": value, "format": fmt}

        return ChatResponse(
            reply=reply,
            response_type="kpi",
            kpi_result=kpi_result,
            action_type="text",
        )

    # ─── Chart Execution ─────────────────────────────────
    def _execute_chart(self, df: pd.DataFrame, col_types: dict,
                       reply: str, chart_spec: dict) -> ChatResponse:
        """Generate chart data based on LLM spec and return for rendering."""
        chart_type_str = chart_spec.get("chart_type", "bar")
        title = chart_spec.get("title", "Chart")
        x_col = chart_spec.get("x_column", "")
        y_col = chart_spec.get("y_column", "count")
        agg = chart_spec.get("aggregation", "mean")
        top_n = min(int(chart_spec.get("top_n", 15) or 15), 30)

        # Validate x column
        x_col = self._match_column(x_col, df.columns.tolist()) or x_col
        if x_col not in df.columns:
            return ChatResponse(reply=f"Column '{x_col}' not found.", response_type="text", action_type="text")

        # Validate y column
        if y_col != "count" and y_col:
            y_col = self._match_column(y_col, df.columns.tolist()) or y_col

        type_map = {
            "bar": "bar", "line": "line", "pie": "pie",
            "histogram": "histogram", "scatter": "scatter", "area": "area",
        }
        chart_type = type_map.get(chart_type_str, "bar")

        # Generate actual chart data
        data = []

        if chart_type == "pie":
            vc = df[x_col].value_counts().head(8)
            data = [{"name": str(k), "value": int(v)} for k, v in vc.items()]

        elif chart_type == "histogram":
            series = df[x_col].dropna()
            if pd.api.types.is_numeric_dtype(series) and len(series) > 0:
                counts, edges = np.histogram(series, bins=min(20, len(series.unique())))
                data = [{x_col: f"{edges[i]:.1f}-{edges[i+1]:.1f}", "count": int(counts[i])}
                        for i in range(len(counts))]
            else:
                vc = series.value_counts().head(20)
                data = [{x_col: str(k), "count": int(v)} for k, v in vc.items()]

        elif chart_type == "scatter" and y_col in df.columns:
            temp = df[[x_col, y_col]].dropna()
            if len(temp) > 200:
                temp = temp.sample(200, random_state=42)
            data = [{x_col: round(float(r[x_col]), 4), y_col: round(float(r[y_col]), 4)}
                    for _, r in temp.iterrows()]

        elif y_col in df.columns and y_col != "count":
            # Bar/line with aggregation
            SAFE_AGGS = {"mean", "sum", "count", "median", "min", "max"}
            agg = agg if agg in SAFE_AGGS else "mean"
            try:
                grouped = df.groupby(x_col)[y_col].agg(agg).sort_values(ascending=False).head(top_n)
                data = [{x_col: str(k), y_col: round(float(v), 2)} for k, v in grouped.items()]
            except Exception:
                vc = df[x_col].value_counts().head(top_n)
                data = [{x_col: str(k), "count": int(v)} for k, v in vc.items()]
                y_col = "count"
        else:
            # Value counts fallback
            vc = df[x_col].value_counts().head(top_n)
            data = [{x_col: str(k), "count": int(v)} for k, v in vc.items()]
            y_col = "count"

        if not data:
            return ChatResponse(reply="Couldn't generate chart data.", response_type="text", action_type="text")

        chart_data = {
            "chart_type": chart_type,
            "title": title,
            "x_column": x_col,
            "y_column": y_col,
            "data": data,
        }

        # Also create a ChartConfig for dashboard integration
        type_enum_map = {
            "bar": ChartType.BAR, "line": ChartType.LINE, "pie": ChartType.PIE,
            "histogram": ChartType.HISTOGRAM, "scatter": ChartType.SCATTER, "area": ChartType.AREA,
        }
        new_chart = ChartConfig(
            id=generate_id(),
            title=title,
            chart_type=type_enum_map.get(chart_type, ChartType.BAR),
            x_column=x_col,
            y_column=y_col,
            data=data,
            description=reply,
        )

        return ChatResponse(
            reply=reply,
            response_type="chart",
            chart_data=chart_data,
            new_chart=new_chart,
            action_type="new_chart",
        )

    # ─── Table Execution ─────────────────────────────────
    def _execute_table(self, df: pd.DataFrame, col_types: dict,
                       reply: str, operation: dict) -> ChatResponse:
        """Execute a data operation and return table results."""
        op_type = operation.get("type", "describe")
        column = operation.get("column")
        column2 = operation.get("column2")
        value = operation.get("value")
        agg = operation.get("aggregation", "mean")
        top_n = min(int(operation.get("top_n", 20) or 20), 50)

        if column:
            column = self._match_column(column, df.columns.tolist()) or column
        if column2:
            column2 = self._match_column(column2, df.columns.tolist()) or column2

        data = None

        try:
            if op_type == "missing_values":
                missing = df.isnull().sum()
                missing_pct = (missing / len(df) * 100).round(1)
                data = [
                    {"Column": col, "Missing": int(missing[col]), "% Missing": float(missing_pct[col])}
                    for col in df.columns if missing[col] > 0
                ]
                if not data:
                    return ChatResponse(
                        reply="No missing values found in this dataset.",
                        response_type="text", action_type="text",
                    )

            elif op_type == "describe" and column and column in df.columns:
                if pd.api.types.is_numeric_dtype(df[column]):
                    desc = df[column].describe().round(2)
                    data = [{"Statistic": k, "Value": round(float(v), 4)} for k, v in desc.items()]
                else:
                    vc = df[column].value_counts().head(top_n)
                    data = [{column: str(k), "Count": int(v)} for k, v in vc.items()]

            elif op_type == "value_counts" and column and column in df.columns:
                vc = df[column].value_counts().head(top_n)
                data = [{column: str(k), "Count": int(v)} for k, v in vc.items()]

            elif op_type == "filter" and column and column in df.columns and value:
                filtered = df[df[column].astype(str).str.lower() == str(value).lower()]
                data = self._sanitize(filtered.head(top_n).to_dict(orient="records"))
                reply = f"Found {len(filtered):,} records where {self._humanize(column)} = '{value}'"

            elif op_type in ("aggregate", "group_by") and column and column2:
                if column in df.columns and column2 in df.columns:
                    SAFE_AGGS = {"mean", "sum", "count", "median", "min", "max"}
                    agg = agg if agg in SAFE_AGGS else "mean"
                    grouped = df.groupby(column)[column2].agg(agg).sort_values(ascending=False).head(top_n)
                    data = [{column: str(k), f"{agg}({column2})": round(float(v), 2)} for k, v in grouped.items()]

            elif op_type == "sort" and column and column in df.columns:
                sorted_df = df.sort_values(by=column, ascending=False).head(top_n)
                data = self._sanitize(sorted_df.to_dict(orient="records"))

            elif op_type == "correlation":
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if len(numeric_cols) >= 2:
                    corr = df[numeric_cols].corr()
                    pairs = []
                    for i, c1 in enumerate(numeric_cols):
                        for j, c2 in enumerate(numeric_cols):
                            if i < j:
                                pairs.append({"Column 1": c1, "Column 2": c2,
                                             "Correlation": round(float(corr.loc[c1, c2]), 3)})
                    pairs.sort(key=lambda x: abs(x["Correlation"]), reverse=True)
                    data = pairs[:top_n]

            elif op_type == "describe" and not column:
                desc = df.describe().round(2)
                data = self._sanitize(desc.reset_index().to_dict(orient="records"))

        except Exception as e:
            logger.warning(f"Table operation failed: {e}")

        if data is None:
            # Fallback: show summary
            desc = df.describe().round(2)
            data = self._sanitize(desc.reset_index().to_dict(orient="records"))
            reply = reply or "Here are the summary statistics:"

        return ChatResponse(
            reply=reply,
            response_type="table",
            data_result=self._sanitize(data),
            action_type="data_table",
        )

    # ─── Fallback (no LLM) ───────────────────────────────
    def _fallback_execute(self, message: str, df: pd.DataFrame, col_types: dict) -> ChatResponse:
        """Rule-based fallback when LLM is unavailable."""
        msg = message.lower().strip()

        if any(w in msg for w in ["missing", "null", "empty"]):
            missing = df.isnull().sum()
            data = [{"Column": c, "Missing": int(missing[c]), "% Missing": round(float(missing[c]/len(df)*100), 1)}
                    for c in df.columns if missing[c] > 0]
            if data:
                return ChatResponse(reply=f"Found missing values in {len(data)} columns:",
                                    response_type="table", data_result=data, action_type="data_table")
            return ChatResponse(reply="No missing values found.", response_type="text", action_type="text")

        if any(w in msg for w in ["summary", "describe", "statistics"]):
            desc = df.describe().round(2)
            data = self._sanitize(desc.reset_index().to_dict(orient="records"))
            return ChatResponse(reply="Summary statistics:", response_type="table",
                                data_result=data, action_type="data_table")

        if "correlation" in msg:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr()
                pairs = []
                for i, c1 in enumerate(numeric_cols):
                    for j, c2 in enumerate(numeric_cols):
                        if i < j:
                            pairs.append({"Column 1": c1, "Column 2": c2,
                                         "Correlation": round(float(corr.loc[c1, c2]), 3)})
                pairs.sort(key=lambda x: abs(x["Correlation"]), reverse=True)
                return ChatResponse(reply="Correlation analysis:", response_type="table",
                                    data_result=pairs[:15], action_type="data_table")

        columns = ", ".join(df.columns.tolist())
        return ChatResponse(
            reply=f"Try: 'Show summary statistics', 'Show missing values', 'Give correlation analysis'\n\nColumns: {columns}",
            response_type="text", action_type="text",
        )

    # ─── Helpers ─────────────────────────────────────────
    def _match_column(self, hint: str, columns: list[str]) -> Optional[str]:
        if not hint:
            return None
        hint_lower = hint.lower().strip()
        for col in columns:
            if col.lower() == hint_lower:
                return col
        for col in columns:
            if hint_lower in col.lower() or col.lower() in hint_lower:
                return col
        hint_words = set(hint_lower.replace("_", " ").split())
        for col in columns:
            col_words = set(col.lower().replace("_", " ").split())
            if hint_words & col_words:
                return col
        return None

    def _sanitize(self, data: list[dict]) -> list[dict]:
        sanitized = []
        for row in data:
            clean = {}
            for k, v in row.items():
                if isinstance(v, (np.integer,)):
                    clean[k] = int(v)
                elif isinstance(v, (np.floating,)):
                    clean[k] = round(float(v), 4) if not np.isnan(v) else None
                elif isinstance(v, pd.Timestamp):
                    clean[k] = str(v)
                elif isinstance(v, (np.bool_,)):
                    clean[k] = bool(v)
                else:
                    clean[k] = v
            sanitized.append(clean)
        return sanitized

    @staticmethod
    def _humanize(col_name: str) -> str:
        return col_name.replace("_", " ").replace("-", " ").title()
