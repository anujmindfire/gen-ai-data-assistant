"""Document service business logic layer."""

from packages.shared.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service layer interface for document ingestion and management.

    TODO (Phase 2):
        - Interface with DocumentIngestor and VectorRetriever.
        - Handle asynchronous file uploads and background ingestion jobs.
    """

    def __init__(self) -> None:
        logger.info("Initialized DocumentService stub")
