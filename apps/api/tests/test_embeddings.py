"""Unit tests for Gemini embedding generation service."""

from unittest.mock import patch

import pytest
from apps.api.app.core.exceptions import GeminiConfigException
from packages.rag.chunking import TextChunk
from packages.rag.embeddings import EmbeddingService, EnrichedChunk


def test_embed_text_single_success() -> None:
    """Test single text string embedding generation with mocked GoogleGenerativeAIEmbeddings."""
    mock_vector = [0.1, 0.2, 0.3, 0.4]

    with patch(
        "packages.rag.embeddings.GoogleGenerativeAIEmbeddings.embed_query",
        return_value=mock_vector,
    ):
        service = EmbeddingService(model_name="text-embedding-004")
        vector = service.embed_text("Sample text to embed")

        assert vector == mock_vector
        assert len(vector) == 4


def test_embed_batch_multiple_success() -> None:
    """Test batch embedding generation with batch size splitting."""
    texts = [f"Text line {i}" for i in range(5)]

    def mock_embed(batch: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _ in batch]

    with patch(
        "packages.rag.embeddings.GoogleGenerativeAIEmbeddings.embed_documents",
        side_effect=mock_embed,
    ):
        service = EmbeddingService(batch_size=2)
        results = service.embed_batch(texts)

        assert len(results) == 5


def test_embed_chunks_enrichment_and_metadata_preservation() -> None:
    """Test embed_chunks enriches TextChunk objects into EnrichedChunk objects preserving metadata."""
    chunks = [
        TextChunk(
            chunk_id="c1",
            document_id="doc_1",
            chunk_index=0,
            text="First chunk text",
            metadata={"filename": "guide.pdf", "page_number": 1},
        ),
        TextChunk(
            chunk_id="c2",
            document_id="doc_1",
            chunk_index=1,
            text="Second chunk text",
            metadata={"filename": "guide.pdf", "page_number": 2},
        ),
    ]

    def mock_embed(batch: list[str]) -> list[list[float]]:
        return [[0.5] * 3 for _ in batch]

    with patch(
        "packages.rag.embeddings.GoogleGenerativeAIEmbeddings.embed_documents",
        side_effect=mock_embed,
    ):
        service = EmbeddingService()
        enriched = service.embed_chunks(chunks)

        assert len(enriched) == 2
        assert isinstance(enriched[0], EnrichedChunk)
        assert enriched[0].chunk_id == "c1"
        assert enriched[0].embedding == [0.5, 0.5, 0.5]
        assert enriched[0].metadata["filename"] == "guide.pdf"
        assert enriched[0].metadata["page_number"] == 1

        assert enriched[1].chunk_id == "c2"
        assert enriched[1].embedding == [0.5, 0.5, 0.5]
        assert enriched[1].metadata["page_number"] == 2


def test_embed_empty_text_raises_value_error() -> None:
    """Test that empty or whitespace text raises ValueError."""
    service = EmbeddingService()

    with pytest.raises(ValueError, match="Cannot embed empty"):
        service.embed_text("")

    with pytest.raises(ValueError, match="Cannot embed empty"):
        service.embed_text("   \n ")

    with pytest.raises(ValueError, match="cannot be empty"):
        service.embed_batch([])


def test_embedding_unconfigured_api_key_raises_error() -> None:
    """Test that EmbeddingService raises GeminiConfigException when GEMINI_API_KEY is unconfigured."""
    from packages.shared.settings import settings

    with patch.object(settings, "GEMINI_API_KEY", ""):
        service = EmbeddingService()
        with pytest.raises(GeminiConfigException):
            service.embed_text("Hello")
