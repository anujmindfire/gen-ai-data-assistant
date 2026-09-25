"""Embedding generation service using Google Gemini embeddings."""

import time
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel, Field

from apps.api.app.core.exceptions import (
    GeminiAPIException,
    GeminiConfigException,
)
from packages.rag.chunking import TextChunk
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class EnrichedChunk(BaseModel):
    """Normalized chunk model enriched with a dense vector embedding."""

    chunk_id: str = Field(..., description="Unique text chunk UUID")
    document_id: str = Field(..., description="Parent document UUID")
    chunk_index: int = Field(..., description="Zero-based chunk index")
    text: str = Field(..., description="Chunk text content body")
    embedding: list[float] = Field(..., description="Dense vector embedding array")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Preserved metadata dictionary"
    )


class EmbeddingService:
    """Service wrapping GoogleGenerativeAIEmbeddings with batching and retry logic."""

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.model_name = (
            model_name if model_name is not None else settings.GEMINI_EMBEDDING_MODEL
        )
        self.batch_size = (
            batch_size if batch_size is not None else settings.EMBEDDING_BATCH_SIZE
        )
        self._embeddings_client: GoogleGenerativeAIEmbeddings | None = None

    def _get_client(self) -> GoogleGenerativeAIEmbeddings:
        """Lazy-initialize GoogleGenerativeAIEmbeddings client instance."""
        if self._embeddings_client is None:
            if not settings.is_gemini_configured:
                logger.error(
                    "EmbeddingService initialization failed: Missing Gemini API key."
                )
                raise GeminiConfigException(
                    message="GEMINI_API_KEY is not configured. Please check your .env file."
                )

            logger.info(
                f"Initializing GoogleGenerativeAIEmbeddings client (model: {self.model_name}, batch_size: {self.batch_size})"
            )
            self._embeddings_client = GoogleGenerativeAIEmbeddings(
                model=self.model_name,
                google_api_key=settings.GEMINI_API_KEY,
            )
        return self._embeddings_client

    def embed_text(self, text: str) -> list[float]:
        """Generate a dense vector embedding array for a single text string.

        Args:
            text: Input text string.

        Returns:
            List[float]: Vector embedding array.

        Raises:
            ValueError: If text is empty.
            GeminiAPIException: If API call fails.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty or whitespace-only text.")

        client = self._get_client()
        try:
            vector = client.embed_query(text)
            return vector
        except Exception as exc:
            logger.error(f"Gemini embedding API call failed: {str(exc)}", exc_info=True)
            raise GeminiAPIException(
                message=f"Gemini embedding generation failed: {str(exc)}",
                code="GEMINI_EMBEDDING_ERROR",
            ) from exc

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings in batches using GEMINI_EMBEDDING_MODEL.

        Args:
            texts: List of text strings to embed.

        Returns:
            List[List[float]]: Matrix of vector embedding arrays matching input order.

        Raises:
            ValueError: If texts list is empty.
        """
        if not texts:
            raise ValueError("Input texts list for batch embedding cannot be empty.")

        client = self._get_client()
        all_embeddings: list[list[float]] = []
        total_texts = len(texts)

        logger.info(
            f"Starting batch embedding generation for {total_texts} texts (batch_size: {self.batch_size})"
        )
        start_time = time.perf_counter()

        for i in range(0, total_texts, self.batch_size):
            batch_slice = texts[i : i + self.batch_size]
            try:
                batch_vectors = client.embed_documents(batch_slice)
                all_embeddings.extend(batch_vectors)
            except Exception as exc:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.error(
                    f"Failed batch embedding generation at slice [{i}:{i + len(batch_slice)}] after {duration_ms}ms: {str(exc)}",
                    exc_info=True,
                )
                raise GeminiAPIException(
                    message=f"Batch embedding generation failed: {str(exc)}",
                    code="GEMINI_EMBEDDING_ERROR",
                ) from exc

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"Successfully generated {len(all_embeddings)} vector embeddings in {duration_ms}ms"
        )
        return all_embeddings

    def embed_chunks(self, chunks: list[TextChunk]) -> list[EnrichedChunk]:
        """Enrich a list of TextChunk objects with Gemini vector embeddings.

        Args:
            chunks: List of TextChunk objects.

        Returns:
            List[EnrichedChunk]: List of enriched chunk objects containing embeddings and metadata.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        doc_id = chunks[0].document_id if chunks else "unknown"

        logger.info(f"Embedding {len(chunks)} text chunks for document_id '{doc_id}'")
        vectors = self.embed_batch(texts)

        enriched_chunks: list[EnrichedChunk] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            enriched_chunks.append(
                EnrichedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    embedding=vector,
                    metadata=chunk.metadata.copy(),
                )
            )

        logger.info(
            f"Enriched {len(enriched_chunks)} chunks with dense vectors for document_id '{doc_id}'"
        )
        return enriched_chunks
