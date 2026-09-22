"""Chat route handler for /chat placeholder endpoint."""

from fastapi import APIRouter, HTTPException, status, Depends
from apps.api.app.models.chat import ChatRequest, ChatResponse
from apps.api.app.dependencies.services import get_chat_service
from apps.api.app.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Invoke GenAI Chat Assistant (Placeholder)",
    description="Endpoint for querying the GenAI Data Assistant using LangGraph multi-agent routing.",
)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Placeholder endpoint returning 501 Not Implemented.

    TODO (Phase 4):
        - Pass user prompt to LangGraph workflow graph.
        - Stream or return synthesized response from Google Gemini API.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Chat endpoint not implemented yet. TODO: Integrate LangGraph workflow graph.",
    )
