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
    summary="Conversational AI Data Assistant Endpoint",
    description=(
        "Submits user natural language prompt to LangGraph StateGraph workflow DAG.\n\n"
        "**Routing Branches**:\n"
        "- `rag`: Vector search over Qdrant policy documents with source citations.\n"
        "- `sql`: AST-validated SELECT database analytics query over PostgreSQL.\n"
        "- `combined`: Dual-domain vector retrieval & SQL query context fusion.\n\n"
        "**Session Memory**: Pass optional `session_id` to continue multi-turn conversation context."
    ),
    responses={
        200: {
            "description": "Successful chat completion response with answer, route, citations, and session_id."
        },
        400: {"description": "Invalid input prompt or missing configuration error."},
        422: {"description": "Validation error in request JSON body."},
        502: {"description": "Gemini LLM API or backend service failure."},
    },
)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Execute direct chat completion with Google Gemini and session memory."""
    return await chat_service.generate_response(
        message=request.message, session_id=request.session_id
    )
