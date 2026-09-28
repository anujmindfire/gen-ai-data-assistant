import time

from apps.api.app.core.exceptions import GeminiAPIException, GeminiConfigException
from apps.api.app.models.chat import ChatResponse
from packages.graph.memory import memory_manager
from packages.graph.workflow import graph_app
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class ChatService:
    """Service layer executing user chat requests using LangGraph workflow graph with session memory."""

    async def generate_response(
        self, message: str, session_id: str | None = None
    ) -> ChatResponse:
        """Process user message using LangGraph workflow graph and return structured response.

        Args:
            message: Input user natural language message prompt.
            session_id: Optional session identifier for context continuation.

        Returns:
            ChatResponse: Structured response containing answer, session_id, route, citations, provider, and model.

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

        # Retrieve or initialize session data
        session = memory_manager.get_or_create_session(session_id)
        history_dumps = [msg.model_dump() for msg in session.history]

        try:
            logger.info(
                f"Dispatching chat message to LangGraph workflow graph for session '{session.session_id}' with model: {model_name}"
            )

            initial_state = {
                "question": message,
                "query": message,
                "errors": [],
                "session_id": session.session_id,
                "conversation_history": history_dumps,
                "previous_route": session.previous_route,
                "previous_sources": session.previous_sources,
                "previous_sql": session.previous_sql,
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
            sql_query = result_state.get("sql") or result_state.get("sql_query")

            sources_list = [
                {
                    "filename": str(src.get("filename", "")),
                    "page": int(src.get("page", 1)),
                    "chunk_index": src.get("chunk_index"),
                }
                for src in raw_sources
                if src and "filename" in src
            ]

            # Save completed interaction pair to session memory manager
            updated_session = memory_manager.add_interaction(
                session_id=session.session_id,
                question=message,
                response=final_answer,
                route=selected_route,
                sources=sources_list,
                sql=sql_query,
            )

            logger.info(
                f"LangGraph chat response generated in {duration_ms}ms (session: '{updated_session.session_id}', route: '{selected_route}', sources: {len(sources_list)})",
                extra={
                    "session_id": updated_session.session_id,
                    "model": model_name,
                    "route": selected_route,
                    "duration_ms": duration_ms,
                    "sources_count": len(sources_list),
                    "status": "success",
                },
            )

            return ChatResponse(
                answer=final_answer,
                session_id=updated_session.session_id,
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
                    "session_id": session.session_id,
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
