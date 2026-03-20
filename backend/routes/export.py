"""
Analytix AI — Export Route.
Handles PDF, PPTX, and image exports.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from routes.upload import datasets_store
from services.export_service import ExportService

router = APIRouter(prefix="/api", tags=["Export"])
export_service = ExportService()


@router.get("/export/{dataset_id}/pdf")
async def export_pdf(dataset_id: str):
    """Export dashboard as PDF report."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    store = datasets_store[dataset_id]
    dashboard = store["dashboard"]
    insights = store.get("insights", [])
    df = store["df"]

    dashboard_dict = dashboard.dict() if hasattr(dashboard, "dict") else dashboard.model_dump()
    insights_list = [i.dict() if hasattr(i, "dict") else i.model_dump() for i in insights]

    try:
        pdf_bytes = export_service.generate_pdf_report(dashboard_dict, insights_list, df)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=analytix_report_{dataset_id}.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/export/{dataset_id}/pptx")
async def export_pptx(dataset_id: str):
    """Export dashboard as PPTX presentation."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    store = datasets_store[dataset_id]
    dashboard = store["dashboard"]
    insights = store.get("insights", [])
    df = store["df"]

    dashboard_dict = dashboard.dict() if hasattr(dashboard, "dict") else dashboard.model_dump()
    insights_list = [i.dict() if hasattr(i, "dict") else i.model_dump() for i in insights]

    try:
        pptx_bytes = export_service.generate_pptx(dashboard_dict, insights_list, df)
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename=analytix_presentation_{dataset_id}.pptx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPTX generation failed: {str(e)}")


@router.get("/export/{dataset_id}/chart/{chart_id}")
async def export_chart_image(dataset_id: str, chart_id: str):
    """Export a single chart as PNG image."""
    if dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    store = datasets_store[dataset_id]
    dashboard = store["dashboard"]

    # Find the chart
    chart = None
    for c in dashboard.charts:
        c_dict = c.dict() if hasattr(c, "dict") else c.model_dump()
        if c_dict.get("id") == chart_id:
            chart = c_dict
            break

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found.")

    try:
        img_bytes = export_service.generate_chart_image(chart)
        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=chart_{chart_id}.png"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")
