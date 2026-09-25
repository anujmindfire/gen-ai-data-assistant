"""Chat service business logic layer implementing Gemini LLM interaction."""

import time

from apps.api.app.core.exceptions import GeminiAPIException, GeminiConfigException
from apps.api.app.models.chat import ChatResponse
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class ChatService:
    """Service layer for handling chat interactions with Google Gemini LLM."""

    async def generate_response(self, message: str) -> ChatResponse:
        """Process user message and return Gemini response.

        Args:
            message: Input message prompt string.

        Returns:
            ChatResponse: Structured answer payload.

        Raises:
            GeminiConfigException: If API key is unconfigured.
            GeminiAPIException: If Gemini API call fails or times out.
        """
        if not settings.is_gemini_configured:
            logger.error("Chat service error: Gemini API key is not configured.")
            raise GeminiConfigException(
                message="GEMINI_API_KEY is missing or invalid. Please check your .env file."
            )

        start_time = time.perf_counter()
        model_name = settings.GEMINI_MODEL

        try:
            logger.info(
                f"Dispatching chat message to RAG Service with model: {model_name}"
            )
            from packages.rag.rag_service import RAGService

            rag_service = RAGService()
            rag_response = rag_service.answer_question(question=message)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            sources_list = [
                {
                    "filename": src.filename,
                    "page": src.page,
                    "chunk_index": src.chunk_index,
                }
                for src in rag_response.sources
            ]

            logger.info(
                f"RAG chat response generated in {duration_ms}ms (model: {model_name}, sources: {len(sources_list)})",
                extra={
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "sources_count": len(sources_list),
                    "status": "success",
                },
            )

            return ChatResponse(
                answer=rag_response.answer,
                sources=sources_list,
                provider="gemini",
                model=model_name,
            )
        except ValueError as exc:
            logger.error(f"Validation error in chat service: {str(exc)}")
            raise GeminiConfigException(message=str(exc)) from exc
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Gemini API failure after {duration_ms}ms: {str(exc)}",
                extra={
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "status": "failure",
                },
                exc_info=True,
            )
            raise GeminiAPIException(
                message="Unable to reach Gemini.",
                code="GEMINI_API_ERROR",
            ) from exc
