"""Qdrant vector store service for indexing, payload management, and collection lifecycle."""

import time
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from apps.api.app.core.exceptions import (
    QdrantAPIException,
    QdrantConfigException,
)
from packages.rag.embeddings import EnrichedChunk
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class QdrantVectorStore:
    """Service wrapping QdrantClient for vector indexing and collection management."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ) -> None:
        self.host = host if host is not None else settings.QDRANT_HOST
        self.port = port if port is not None else settings.QDRANT_PORT
        self.collection_name = (
            collection_name
            if collection_name is not None
            else settings.QDRANT_COLLECTION
        )
        self.vector_size = (
            vector_size if vector_size is not None else settings.QDRANT_VECTOR_SIZE
        )
        self._client: QdrantClient | None = None

    def get_client(self) -> QdrantClient:
        """Lazy-initialize QdrantClient instance."""
        if self._client is None:
            if not self.host or not self.port:
                raise QdrantConfigException(
                    message="QDRANT_HOST and QDRANT_PORT must be configured."
                )
            logger.info(
                f"Initializing QdrantClient at {self.host}:{self.port} "
                f"(collection: '{self.collection_name}', vector_size: {self.vector_size})"
            )
            try:
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    timeout=10.0,
                    check_compatibility=False,
                )
            except Exception as exc:
                logger.error(
                    f"Failed to create QdrantClient: {str(exc)}", exc_info=True
                )
                raise QdrantAPIException(
                    message=f"Failed to connect to Qdrant server: {str(exc)}"
                ) from exc
        return self._client

    def collection_exists(self, collection_name: str | None = None) -> bool:
        """Check if target vector collection exists in Qdrant.

        Args:
            collection_name: Optional override collection name.

        Returns:
            bool: True if collection exists, False otherwise.
        """
        target_name = collection_name or self.collection_name
        client = self.get_client()
        try:
            return client.collection_exists(collection_name=target_name)
        except Exception as exc:
            logger.error(
                f"Error checking if collection '{target_name}' exists: {str(exc)}",
                exc_info=True,
            )
            raise QdrantAPIException(
                message=f"Error checking Qdrant collection existence: {str(exc)}"
            ) from exc

    def create_collection(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ) -> None:
        """Create target Qdrant vector collection with Cosine distance if it does not exist.

        Args:
            collection_name: Optional collection name override.
            vector_size: Optional vector size override.
        """
        target_name = collection_name or self.collection_name
        target_size = vector_size or self.vector_size
        client = self.get_client()

        if self.collection_exists(collection_name=target_name):
            logger.info(
                f"Qdrant collection '{target_name}' already exists. Skipping creation."
            )
            return

        logger.info(
            f"Creating Qdrant collection '{target_name}' (vector_size={target_size}, distance=COSINE)..."
        )
        start_time = time.perf_counter()
        try:
            client.create_collection(
                collection_name=target_name,
                vectors_config=models.VectorParams(
                    size=target_size,
                    distance=models.Distance.COSINE,
                ),
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"Successfully created Qdrant collection '{target_name}' in {duration_ms}ms"
            )
        except Exception as exc:
            logger.error(
                f"Failed to create Qdrant collection '{target_name}': {str(exc)}",
                exc_info=True,
            )
            raise QdrantAPIException(
                message=f"Failed to create Qdrant collection: {str(exc)}"
            ) from exc

    def upsert_chunks(
        self,
        enriched_chunks: list[EnrichedChunk],
        collection_name: str | None = None,
    ) -> int:
        """Upsert embedded document chunks into Qdrant vector collection.

        Args:
            enriched_chunks: List of EnrichedChunk objects with dense vector embeddings.
            collection_name: Optional collection name override.

        Returns:
            int: Number of points successfully indexed.
        """
        if not enriched_chunks:
            return 0

        target_name = collection_name or self.collection_name
        self.create_collection(collection_name=target_name)

        doc_id = enriched_chunks[0].document_id if enriched_chunks else "unknown"
        total_chunks = len(enriched_chunks)
        points: list[models.PointStruct] = []

        for chunk in enriched_chunks:
            # Generate stable UUID for point ID
            try:
                point_id = str(uuid.UUID(chunk.chunk_id))
            except ValueError:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))

            payload = {
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "filename": str(chunk.metadata.get("filename", "")),
                "file_type": str(chunk.metadata.get("file_type", "")),
                "page": int(
                    chunk.metadata.get("page", chunk.metadata.get("page_number", 1))
                ),
                "chunk_index": int(chunk.chunk_index),
                "text": str(chunk.text),
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=chunk.embedding,
                    payload=payload,
                )
            )

        client = self.get_client()
        logger.info(
            f"Indexing {total_chunks} chunk vectors for document_id '{doc_id}' into collection '{target_name}'..."
        )
        start_time = time.perf_counter()
        try:
            client.upsert(collection_name=target_name, points=points)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"Successfully indexed {total_chunks} vectors into Qdrant collection '{target_name}' in {duration_ms}ms "
                f"(document_id='{doc_id}')"
            )
            return total_chunks
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Failed to upsert points for document_id '{doc_id}' after {duration_ms}ms: {str(exc)}",
                exc_info=True,
            )
            raise QdrantAPIException(
                message=f"Qdrant vector upsert failed: {str(exc)}"
            ) from exc

    def delete_document(
        self,
        document_id: str,
        collection_name: str | None = None,
    ) -> int:
        """Delete all vector points associated with a specific document_id.

        Args:
            document_id: Unique identifier of document.
            collection_name: Optional collection name override.

        Returns:
            int: Operation status indicator (1 for triggered deletion).
        """
        target_name = collection_name or self.collection_name
        client = self.get_client()

        if not self.collection_exists(collection_name=target_name):
            logger.info(
                f"Collection '{target_name}' does not exist. No vectors to delete for document_id '{document_id}'."
            )
            return 0

        logger.info(
            f"Deleting vectors for document_id '{document_id}' from Qdrant collection '{target_name}'..."
        )
        start_time = time.perf_counter()
        try:
            delete_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
            client.delete(
                collection_name=target_name,
                points_selector=delete_filter,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"Successfully requested deletion of vectors for document_id '{document_id}' in {duration_ms}ms"
            )
            return 1
        except Exception as exc:
            logger.error(
                f"Failed to delete vectors for document_id '{document_id}': {str(exc)}",
                exc_info=True,
            )
            raise QdrantAPIException(
                message=f"Failed to delete document vectors from Qdrant: {str(exc)}"
            ) from exc

    def health_check(self, collection_name: str | None = None) -> dict[str, Any]:
        """Verify Qdrant server connectivity and collection availability.

        Returns:
            dict[str, Any]: Health status detail dictionary.
        """
        target_name = collection_name or self.collection_name
        try:
            client = self.get_client()
            exists = client.collection_exists(collection_name=target_name)
            return {
                "status": "connected",
                "collection": target_name,
                "collection_exists": exists,
            }
        except Exception as exc:
            logger.warning(f"Qdrant health check failed: {str(exc)}", exc_info=True)
            return {
                "status": "disconnected",
                "collection": target_name,
                "error": str(exc),
            }
