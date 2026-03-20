"""
Analytix AI — Data Processing Service.
Handles CSV validation, cleaning, type detection, and dataset preview.
"""
import pandas as pd
import numpy as np
from io import BytesIO
from typing import Any
from models.schemas import ColumnInfo, ColumnType
from utils.helpers import generate_id


class DataProcessor:
    """Processes uploaded CSV datasets — validates, cleans, and analyzes."""

    # Threshold for dropping columns with too many missing values
    MISSING_THRESHOLD = 0.5

    def validate_csv(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Validate and parse a CSV file into a DataFrame."""
        if not filename.lower().endswith(".csv"):
            raise ValueError("Only CSV files are supported.")

        try:
            df = pd.read_csv(BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(BytesIO(file_bytes), encoding="latin-1")
            except Exception:
                raise ValueError("Unable to read file. Please ensure it is a valid CSV.")
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

        if df.empty:
            raise ValueError("The uploaded CSV file is empty.")
        if len(df.columns) < 2:
            raise ValueError("Dataset must have at least 2 columns.")
        if len(df) > 500_000:
            raise ValueError("Dataset is too large. Maximum 500,000 rows supported.")

        return df

    def detect_column_types(self, df: pd.DataFrame) -> dict[str, ColumnType]:
        """Detect semantic column types for each column."""
        col_types = {}

        for col in df.columns:
            series = df[col].dropna()
            if series.empty:
                col_types[col] = ColumnType.TEXT
                continue

            # Check if datetime
            if pd.api.types.is_datetime64_any_dtype(series):
                col_types[col] = ColumnType.DATETIME
                continue

            # Try parsing as datetime
            if series.dtype == object:
                try:
                    parsed = pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
                    if parsed.notna().sum() / len(series) > 0.8:
                        col_types[col] = ColumnType.DATETIME
                        continue
                except Exception:
                    pass

            # Check boolean
            if series.dtype == bool or set(series.unique()).issubset({True, False, 0, 1, "True", "False", "true", "false", "yes", "no", "Yes", "No"}):
                col_types[col] = ColumnType.BOOLEAN
                continue

            # Check numeric
            if pd.api.types.is_numeric_dtype(series):
                unique_ratio = series.nunique() / len(series)
                if series.nunique() <= 10 and unique_ratio < 0.05:
                    col_types[col] = ColumnType.CATEGORICAL
                else:
                    col_types[col] = ColumnType.NUMERIC
                continue

            # Check categorical (object type with few unique values)
            if series.dtype == object:
                unique_ratio = series.nunique() / len(series)
                if series.nunique() <= 50 or unique_ratio < 0.1:
                    col_types[col] = ColumnType.CATEGORICAL
                else:
                    col_types[col] = ColumnType.TEXT

        return col_types

    def clean_data(self, df: pd.DataFrame, col_types: dict[str, ColumnType]) -> pd.DataFrame:
        """Clean the dataset — handle missing values and type coercion."""
        df = df.copy()

        # Drop columns with >50% missing values
        missing_pct = df.isnull().sum() / len(df)
        cols_to_drop = missing_pct[missing_pct > self.MISSING_THRESHOLD].index.tolist()
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
            # Remove dropped columns from col_types
            for col in cols_to_drop:
                col_types.pop(col, None)

        # Handle missing values based on type
        for col in df.columns:
            ct = col_types.get(col, ColumnType.TEXT)

            if ct == ColumnType.NUMERIC:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val if pd.notna(median_val) else 0)

            elif ct == ColumnType.CATEGORICAL:
                mode_val = df[col].mode()
                fill = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                df[col] = df[col].fillna(fill).astype(str)

            elif ct == ColumnType.DATETIME:
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass

            elif ct == ColumnType.BOOLEAN:
                df[col] = df[col].map({
                    True: True, False: False,
                    1: True, 0: False,
                    "True": True, "False": False,
                    "true": True, "false": False,
                    "yes": True, "no": False,
                    "Yes": True, "No": False,
                }).fillna(False)

            else:
                df[col] = df[col].fillna("").astype(str)

        # Drop fully duplicate rows
        df = df.drop_duplicates()

        return df

    def get_column_info(self, df: pd.DataFrame, col_types: dict[str, ColumnType]) -> list[ColumnInfo]:
        """Get metadata for each column."""
        info_list = []
        for col in df.columns:
            ct = col_types.get(col, ColumnType.TEXT)
            missing = int(df[col].isnull().sum())
            sample = df[col].dropna().head(5).tolist()
            # Convert numpy types to native Python types for JSON serialization
            sample = [s.item() if hasattr(s, "item") else s for s in sample]
            # Convert timestamps to strings
            sample = [str(s) if isinstance(s, pd.Timestamp) else s for s in sample]

            info_list.append(ColumnInfo(
                name=col,
                dtype=str(df[col].dtype),
                col_type=ct,
                missing_count=missing,
                missing_pct=round(missing / len(df) * 100, 1) if len(df) > 0 else 0,
                unique_count=int(df[col].nunique()),
                sample_values=sample,
            ))
        return info_list

    def get_preview(self, df: pd.DataFrame, max_rows: int = 100) -> list[dict[str, Any]]:
        """Get a JSON-serializable preview of the dataset."""
        preview_df = df.head(max_rows).copy()

        # Convert all types to JSON-safe values
        for col in preview_df.columns:
            if pd.api.types.is_datetime64_any_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].astype(str)
            elif pd.api.types.is_numeric_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].apply(
                    lambda x: None if pd.isna(x) else (int(x) if x == int(x) else round(float(x), 4))
                )

        return preview_df.where(preview_df.notna(), None).to_dict(orient="records")
