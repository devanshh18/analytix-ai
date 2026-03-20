"""
Analytix AI — Chat Route.
Handles AI chat interactions with conversation history.
"""
from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.chat_service import ChatService
from routes.upload import datasets_store

router = APIRouter(prefix="/api", tags=["Chat"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message with full conversation history."""
    if request.dataset_id not in datasets_store:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload a dataset first.")

    store = datasets_store[request.dataset_id]
    df = store["df"]
    col_types = store["col_types"]
    current_charts = None

    # Get current chart configs if available
    if "dashboard" in store:
        dashboard = store["dashboard"]
        chart_list = dashboard.charts if hasattr(dashboard, "charts") else []
        current_charts = [c.dict() if hasattr(c, "dict") else c.model_dump() for c in chart_list]

    try:
        response = chat_service.process_message(
            message=request.message,
            df=df,
            col_types=col_types,
            current_charts=current_charts,
            conversation_history=request.conversation_history,
        )
        return response
    except Exception as e:
        return ChatResponse(
            reply=f"I encountered an error: {str(e)}. Please try rephrasing.",
            response_type="text",
            action_type="text",
        )
