"""Chat service business logic layer."""

from packages.shared.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service wrapper for executing LangGraph workflow interactions.

    TODO (Phase 4):
        - Initialize and invoke LangGraph runnable compiled DAG workflow.
        - Persist chat conversation state in PostgreSQL session storage.
    """

    def __init__(self) -> None:
        logger.info("Initialized ChatService stub")

    async def process_chat(self, prompt: str, conversation_id: str) -> None:
        """Placeholder for invoking LangGraph agent graph."""
        # TODO: Execute workflow graph
        pass
