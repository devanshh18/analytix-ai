"""
Analytix AI — Dashboard Route.
Returns dashboard configurations and handles chart operations.
"""
from fastapi import APIRouter, HTTPException
from models.schemas import DashboardConfig, InsightItem
from routes.upload import datasets_store

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard/{dataset_id}")
async def get_dashboard(dataset_id: str):
    """Get the dashboard configuration for a dataset."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload a dataset first.")

    store = datasets_store[dataset_id]
    dashboard = store["dashboard"]
    insights = store.get("insights", [])

    return {
        "dashboard": dashboard.dict() if hasattr(dashboard, "dict") else dashboard.model_dump(),
        "insights": [ins.dict() if hasattr(ins, "dict") else ins.model_dump() for ins in insights],
    }


@router.get("/dataset/{dataset_id}/preview")
async def get_preview(dataset_id: str):
    """Get a preview of the dataset."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    from services.data_processor import DataProcessor
    processor = DataProcessor()
    df = datasets_store[dataset_id]["df"]

    return {
        "preview": processor.get_preview(df),
        "columns": list(df.columns),
        "rows": len(df),
        "columns_count": len(df.columns),
    }


@router.post("/dashboard/{dataset_id}/explain-chart")
async def explain_chart(dataset_id: str, chart_config: dict):
    """Generate a natural language explanation for a chart."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    from services.insight_generator import InsightGenerator
    generator = InsightGenerator()
    df = datasets_store[dataset_id]["df"]

    explanation = generator.explain_chart(chart_config, df)
    return {"explanation": explanation}
