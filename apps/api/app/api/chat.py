"""Chat route handler for POST /chat endpoint."""

from apps.api.app.dependencies.services import get_chat_service
from apps.api.app.models.chat import ChatRequest, ChatResponse
from apps.api.app.services.chat_service import ChatService
from fastapi import APIRouter, Depends, status

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with Gemini Assistant",
    description="Submits user message prompt to Google Gemini LLM and returns structured answer.",
)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Execute direct chat completion with Google Gemini and session memory."""
    return await chat_service.generate_response(
        message=request.message, session_id=request.session_id
    )
