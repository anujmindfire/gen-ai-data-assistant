"""FastAPI dependency injection module."""

from .services import get_chat_service, get_document_service

__all__ = ["get_chat_service", "get_document_service"]
