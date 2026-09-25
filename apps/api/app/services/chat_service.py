"""Chat service business logic layer implementing LangGraph intelligent workflow execution."""

import time

from apps.api.app.core.exceptions import GeminiAPIException, GeminiConfigException
from apps.api.app.models.chat import ChatResponse
from packages.graph.workflow import graph_app
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class ChatService:
    """Service layer executing user chat requests using LangGraph workflow graph."""

    async def generate_response(self, message: str) -> ChatResponse:
        """Process user message using LangGraph workflow graph and return structured response.

        Args:
            message: Input user natural language message prompt.

        Returns:
            ChatResponse: Structured response containing answer, route, citations, provider, and model.

        Raises:
            GeminiConfigException: If API key configuration is invalid.
            GeminiAPIException: If LangGraph graph execution encounters an unhandled exception.
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
                f"Dispatching chat message to LangGraph workflow graph with model: {model_name}"
            )

            initial_state = {
                "question": message,
                "query": message,
                "errors": [],
            }

            # Invoke compiled LangGraph DAG
            result_state = await graph_app.ainvoke(initial_state)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            selected_route = result_state.get("route") or result_state.get(
                "intent", "rag"
            )
            final_answer = (
                result_state.get("final_answer")
                or "No answer was produced by the assistant."
            )
            raw_sources = result_state.get("sources", [])

            sources_list = [
                {
                    "filename": str(src.get("filename", "")),
                    "page": int(src.get("page", 1)),
                    "chunk_index": src.get("chunk_index"),
                }
                for src in raw_sources
                if src and "filename" in src
            ]

            logger.info(
                f"LangGraph chat response generated in {duration_ms}ms (route: '{selected_route}', sources: {len(sources_list)})",
                extra={
                    "model": model_name,
                    "route": selected_route,
                    "duration_ms": duration_ms,
                    "sources_count": len(sources_list),
                    "status": "success",
                },
            )

            return ChatResponse(
                answer=final_answer,
                route=selected_route,
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
                f"LangGraph workflow execution failure after {duration_ms}ms: {str(exc)}",
                extra={
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "status": "failure",
                },
                exc_info=True,
            )
            raise GeminiAPIException(
                message="Unable to complete request via LangGraph assistant.",
                code="GEMINI_API_ERROR",
            ) from exc
