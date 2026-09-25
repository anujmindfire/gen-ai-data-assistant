"""Vector retriever service using Gemini embeddings and Qdrant similarity search."""

import time

from pydantic import BaseModel, Field

from packages.rag.embeddings import EmbeddingService
from packages.rag.vector_store import QdrantVectorStore
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class RetrievalResult(BaseModel):
    """Container model representing a ranked retrieved chunk with metadata and similarity score."""

    chunk_id: str = Field(..., description="Unique chunk UUID")
    document_id: str = Field(..., description="Parent document UUID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Document file extension/type")
    page: int = Field(default=1, description="Page number where chunk resides")
    chunk_index: int = Field(..., description="Zero-based chunk index")
    text: str = Field(..., description="Text content body of retrieved chunk")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")


class VectorRetriever:
    """Service executing semantic vector similarity search against Qdrant."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: QdrantVectorStore | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> None:
        self.embedding_service = (
            embedding_service if embedding_service is not None else EmbeddingService()
        )
        self.vector_store = (
            vector_store if vector_store is not None else QdrantVectorStore()
        )
        self.top_k = top_k if top_k is not None else settings.RAG_TOP_K
        self.score_threshold = (
            score_threshold
            if score_threshold is not None
            else settings.RAG_SCORE_THRESHOLD
        )

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        document_id: str | None = None,
        filename: str | None = None,
        file_type: str | None = None,
    ) -> list[RetrievalResult]:
        """Generate query embedding and perform Qdrant similarity search.

        Args:
            question: Search query string.
            top_k: Number of nearest neighbor results to retrieve.
            score_threshold: Minimum cosine similarity score threshold cutoff.
            document_id: Optional document ID metadata filter.
            filename: Optional filename metadata filter.
            file_type: Optional file type metadata filter.

        Returns:
            list[RetrievalResult]: Ranked list of matching document chunks sorted by similarity score.

        Raises:
            ValueError: If question is empty or whitespace-only.
        """
        if not question or not question.strip():
            raise ValueError("Search query question cannot be empty or whitespace.")

        limit = top_k if top_k is not None else self.top_k
        cutoff = (
            score_threshold if score_threshold is not None else self.score_threshold
        )

        logger.info(
            f"Executing semantic retrieval for query: '{question}' (top_k={limit}, score_threshold={cutoff})"
        )
        start_time = time.perf_counter()

        # Step 1: Generate Gemini vector embedding for query string
        query_vector = self.embedding_service.embed_text(question.strip())

        # Step 2: Execute similarity search against Qdrant collection
        raw_results = self.vector_store.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=cutoff,
            document_id=document_id,
            filename=filename,
            file_type=file_type,
        )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        results: list[RetrievalResult] = []

        for item in raw_results:
            results.append(
                RetrievalResult(
                    chunk_id=item.get("chunk_id", ""),
                    document_id=item.get("document_id", ""),
                    filename=item.get("filename", ""),
                    file_type=item.get("file_type", ""),
                    page=int(item.get("page", 1)),
                    chunk_index=int(item.get("chunk_index", 0)),
                    text=item.get("text", ""),
                    score=float(item.get("score", 0.0)),
                )
            )

        top_score = results[0].score if results else 0.0
        logger.info(
            f"Retrieval complete in {duration_ms}ms: found {len(results)} matching chunks "
            f"(highest similarity score: {top_score:.4f}, query='{question}')",
            extra={
                "query": question,
                "top_k": limit,
                "score_threshold": cutoff,
                "result_count": len(results),
                "top_score": top_score,
                "duration_ms": duration_ms,
            },
        )
        return results
