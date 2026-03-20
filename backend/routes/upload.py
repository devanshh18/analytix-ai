"""
Analytix AI — Upload Route.
Handles CSV file upload, validation, cleaning, and LLM-driven processing.
"""
import os
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.data_processor import DataProcessor
from services.analytics_engine import AnalyticsEngine
from services.insight_generator import InsightGenerator
from ai.llm_service import get_llm_service, GroqLLM
from ai.prompts import ANALYST_SYSTEM, CHAT_SUGGESTIONS_PROMPT
from models.schemas import UploadResponse
from utils.helpers import generate_id, get_upload_dir, safe_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])

# In-memory store for datasets (in production, use a database)
datasets_store = {}
processor = DataProcessor()
engine = AnalyticsEngine()
insight_gen = InsightGenerator()
llm = get_llm_service()


def _generate_suggestions(analysis: dict, columns: list) -> list[str]:
    """Generate LLM-powered chat suggestions based on dataset context."""
    fallback = [
        "Show summary statistics",
        "Show missing values",
        "What patterns exist in the data?",
        "Show top 10 rows",
        f"Show distribution of {columns[0]}" if columns else "Describe the data",
        "What insights can you find?",
    ]
    if not isinstance(llm, GroqLLM):
        return fallback
    try:
        prompt = CHAT_SUGGESTIONS_PROMPT.format(
            purpose=analysis.get("purpose", "General dataset"),
            columns=", ".join(columns[:15]),
            domain=analysis.get("domain", "General"),
        )
        result = llm.generate_json(prompt, ANALYST_SYSTEM, max_tokens=512)
        suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
        return suggestions[:6] if suggestions else fallback
    except Exception as e:
        logger.warning(f"Failed to generate suggestions: {e}")
        return fallback


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """Upload and process a CSV dataset with LLM-driven analysis."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Read file
    try:
        contents = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read the uploaded file.")

    # Check size
    max_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")) * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(status_code=400,
                            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB.")

    # Validate & parse
    try:
        df = processor.validate_csv(contents, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Detect types & clean
    col_types = processor.detect_column_types(df)
    df = processor.clean_data(df, col_types)

    # Re-detect types after cleaning
    col_types = processor.detect_column_types(df)
    column_info = processor.get_column_info(df, col_types)
    preview = processor.get_preview(df)

    # Generate LLM-driven dashboard
    dataset_id = generate_id()
    logger.info(f"Generating LLM-driven dashboard for {file.filename} (id: {dataset_id})")

    dashboard = engine.generate_dashboard(df, col_types, dataset_id, filename=file.filename or "")

    # Generate LLM-driven insights (pass dataset context from analysis)
    dataset_context = dashboard.title
    insights = insight_gen.generate_insights(df, col_types, dataset_context=dataset_context)
    dashboard.insights = [ins.description for ins in insights]

    # Generate LLM-powered chat suggestions specific to this dataset
    analysis = engine.analyze_dataset(df, col_types, filename=file.filename or "")
    suggestions = _generate_suggestions(analysis, list(df.columns))

    # Save to store
    upload_dir = get_upload_dir()
    save_path = upload_dir / f"{dataset_id}.csv"
    df.to_csv(str(save_path), index=False)

    datasets_store[dataset_id] = {
        "filename": safe_filename(file.filename),
        "df": df,
        "col_types": col_types,
        "dashboard": dashboard,
        "insights": insights,
        "suggestions": suggestions,
    }

    logger.info(f"Dashboard generated: {len(dashboard.kpis)} KPIs, {len(dashboard.charts)} charts, {len(insights)} insights, {len(suggestions)} suggestions")

    return UploadResponse(
        dataset_id=dataset_id,
        filename=safe_filename(file.filename),
        rows=len(df),
        columns=len(df.columns),
        column_info=column_info,
        preview=preview,
    )


@router.get("/suggestions/{dataset_id}")
async def get_suggestions(dataset_id: str):
    """Get LLM-generated chat suggestions for a dataset."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"suggestions": datasets_store[dataset_id].get("suggestions", [])}
