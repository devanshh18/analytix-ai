"""
Analytix AI — LLM-Driven Insight Generator.
Uses Groq LLM for business-meaningful insights with rule-based fallback.
"""
import pandas as pd
import numpy as np
import logging
from typing import Any
from models.schemas import InsightItem, ColumnType
from ai.llm_service import get_llm_service, GroqLLM
from ai.prompts import ANALYST_SYSTEM, INSIGHT_GENERATION_PROMPT, CHART_EXPLANATION_PROMPT
from utils.helpers import generate_id

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generates business insights — LLM-driven with rule-based fallback."""

    def __init__(self):
        self.llm = get_llm_service()

    def generate_insights(self, df: pd.DataFrame, col_types: dict,
                          dataset_context: str = "") -> list[InsightItem]:
        """Generate comprehensive insights for the dataset."""
        if isinstance(self.llm, GroqLLM):
            try:
                return self._llm_insights(df, col_types, dataset_context)
            except Exception as e:
                logger.error(f"LLM insight generation failed: {e}")

        # Fallback to rule-based
        return self._rule_based_insights(df, col_types)

    def _llm_insights(self, df: pd.DataFrame, col_types: dict,
                      dataset_context: str) -> list[InsightItem]:
        """Generate insights using Groq LLM."""
        # Build stats for the prompt
        numeric_cols = [c for c, t in col_types.items()
                        if (hasattr(t, 'value') and t.value == "numeric") and c in df.columns]
        cat_cols = [c for c, t in col_types.items()
                    if (hasattr(t, 'value') and t.value == "categorical") and c in df.columns]

        numeric_stats = ""
        if numeric_cols:
            desc = df[numeric_cols].describe().round(2)
            numeric_stats = desc.to_string()

        # Correlations
        correlations = "Not enough numeric columns."
        if len(numeric_cols) >= 2:
            try:
                corr = df[numeric_cols].corr()
                pairs = []
                for i, c1 in enumerate(numeric_cols):
                    for j, c2 in enumerate(numeric_cols):
                        if i < j and abs(corr.loc[c1, c2]) > 0.3:
                            pairs.append(f"{c1} ↔ {c2}: {corr.loc[c1, c2]:.2f}")
                correlations = "\n".join(pairs[:8]) if pairs else "No strong correlations found."
            except Exception:
                pass

        # Categorical stats
        cat_lines = []
        for col in cat_cols[:5]:
            vc = df[col].value_counts().head(5)
            cat_lines.append(f"{col}: {dict(vc)}")
        categorical_stats = "\n".join(cat_lines) if cat_lines else "No categorical columns."

        prompt = INSIGHT_GENERATION_PROMPT.format(
            dataset_context=dataset_context or "General dataset",
            numeric_stats=numeric_stats,
            correlations=correlations,
            categorical_stats=categorical_stats,
        )

        result = self.llm.generate_json(prompt, ANALYST_SYSTEM)
        insight_list = result.get("insights", []) if isinstance(result, dict) else result

        insights = []
        for item in insight_list[:8]:
            insights.append(InsightItem(
                id=generate_id(),
                category=item.get("category", "summary"),
                title=item.get("title", "Insight"),
                description=item.get("description", ""),
                importance=item.get("importance", "medium"),
                related_columns=item.get("related_columns", []),
            ))

        return insights if insights else self._rule_based_insights(df, col_types)

    def explain_chart(self, chart_config: dict, df: pd.DataFrame) -> str:
        """Generate LLM-powered chart explanation."""
        title = chart_config.get("title", "Chart")
        chart_type = chart_config.get("chart_type", "chart")
        data = chart_config.get("data", [])
        x_col = chart_config.get("x_column", "")
        y_col = chart_config.get("y_column", "")

        if not data:
            return f"This {chart_type} chart shows {title}."

        # Summarize data for prompt
        data_summary = str(data[:5]) if len(data) > 5 else str(data)

        if isinstance(self.llm, GroqLLM):
            try:
                prompt = CHART_EXPLANATION_PROMPT.format(
                    chart_title=title,
                    chart_type=chart_type,
                    x_label=x_col,
                    y_label=y_col,
                    data_summary=data_summary,
                )
                return self.llm.generate(prompt, "You are a business analyst. Explain charts simply.")
            except Exception as e:
                logger.warning(f"LLM chart explanation failed: {e}")

        # Rule-based fallback
        return self._rule_based_chart_explanation(chart_config, data)

    def _rule_based_chart_explanation(self, chart_config: dict, data: list[dict]) -> str:
        """Rule-based chart explanation fallback."""
        title = chart_config.get("title", "Chart")
        chart_type = chart_config.get("chart_type", "chart")
        y_col = chart_config.get("y_column", "")

        if chart_type == "bar" and data:
            top = max(data, key=lambda d: d.get(y_col, 0)) if y_col in data[0] else data[0]
            x_col = chart_config.get("x_column", "")
            return (
                f"This bar chart compares {title}. "
                f"The highest value is '{top.get(x_col, 'N/A')}' "
                f"with {top.get(y_col, 0):,.2f}. There are {len(data)} categories."
            )
        elif chart_type == "pie" and data:
            total = sum(d.get("value", 0) for d in data)
            if total > 0:
                top = max(data, key=lambda d: d.get("value", 0))
                pct = top.get("value", 0) / total * 100
                return f"'{top.get('name', 'N/A')}' is the largest at {pct:.1f}% of total."

        return f"This {chart_type} chart visualizes {title}."

    # ─── Rule-Based Fallback ─────────────────────────────
    def _rule_based_insights(self, df: pd.DataFrame, col_types: dict) -> list[InsightItem]:
        """Generate basic statistical insights without LLM."""
        insights = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        # Summary
        insights.append(InsightItem(
            id=generate_id(), category="summary", title="Dataset Overview",
            description=(
                f"This dataset contains {len(df):,} records across {len(df.columns)} columns. "
                f"There are {len(numeric_cols)} numeric and {len(cat_cols)} categorical columns. "
                f"Data completeness is {(1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100:.1f}%."
            ),
            importance="high", related_columns=[],
        ))

        # Correlations
        if len(numeric_cols) >= 2:
            try:
                corr = df[numeric_cols].corr()
                for i, c1 in enumerate(numeric_cols):
                    for j, c2 in enumerate(numeric_cols):
                        if i < j and abs(corr.loc[c1, c2]) > 0.5:
                            r = corr.loc[c1, c2]
                            insights.append(InsightItem(
                                id=generate_id(), category="comparison",
                                title=f"Correlation: {self._humanize(c1)} & {self._humanize(c2)}",
                                description=(
                                    f"{'Strong' if abs(r) > 0.7 else 'Moderate'} "
                                    f"{'positive' if r > 0 else 'negative'} correlation ({r:.2f})."
                                ),
                                importance="high" if abs(r) > 0.7 else "medium",
                                related_columns=[c1, c2],
                            ))
                            if len(insights) >= 5:
                                break
            except Exception:
                pass

        return insights

    @staticmethod
    def _humanize(col_name: str) -> str:
        return col_name.replace("_", " ").replace("-", " ").title()
