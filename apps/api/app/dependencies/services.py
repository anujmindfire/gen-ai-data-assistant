"""FastAPI dependency injectors for injecting services into route handlers."""

from apps.api.app.services.chat_service import ChatService
from apps.api.app.services.document_service import DocumentService


def get_chat_service() -> ChatService:
    """Dependency provider returning a ChatService instance."""
    return ChatService()


def get_document_service() -> DocumentService:
    """Dependency provider returning a DocumentService instance."""
    return DocumentService()
