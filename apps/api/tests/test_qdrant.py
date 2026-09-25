"""Unit tests for Qdrant vector store service and collection management."""

from unittest.mock import MagicMock, patch

import pytest
from apps.api.app.core.exceptions import QdrantAPIException
from packages.rag.embeddings import EnrichedChunk
from packages.rag.vector_store import QdrantVectorStore


def test_create_collection_new_success() -> None:
    """Test create_collection creates target collection with Cosine distance if missing."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = False

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs", vector_size=768)
        store.create_collection()

        mock_client.collection_exists.assert_called_once_with(
            collection_name="test_docs"
        )
        mock_client.create_collection.assert_called_once()
        call_kwargs = mock_client.create_collection.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_docs"
        assert call_kwargs["vectors_config"].size == 768


def test_create_collection_already_exists_skips() -> None:
    """Test create_collection skips creation when collection already exists."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs")
        store.create_collection()

        mock_client.collection_exists.assert_called_once_with(
            collection_name="test_docs"
        )
        mock_client.create_collection.assert_not_called()


def test_upsert_chunks_success() -> None:
    """Test upserting EnrichedChunk objects converts metadata into PointStruct payloads and calls upsert."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    chunks = [
        EnrichedChunk(
            chunk_id="00000000-0000-0000-0000-000000000001",
            document_id="doc_abc",
            chunk_index=0,
            text="First sentence for testing vector store.",
            embedding=[0.1] * 768,
            metadata={"filename": "report.pdf", "file_type": "pdf", "page": 1},
        ),
        EnrichedChunk(
            chunk_id="00000000-0000-0000-0000-000000000002",
            document_id="doc_abc",
            chunk_index=1,
            text="Second sentence for testing vector store.",
            embedding=[0.2] * 768,
            metadata={"filename": "report.pdf", "file_type": "pdf", "page": 2},
        ),
    ]

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs")
        indexed_count = store.upsert_chunks(chunks)

        assert indexed_count == 2
        mock_client.upsert.assert_called_once()
        call_kwargs = mock_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_docs"
        points = call_kwargs["points"]
        assert len(points) == 2

        # Verify point payload structure
        payload0 = points[0].payload
        assert payload0["document_id"] == "doc_abc"
        assert payload0["chunk_id"] == "00000000-0000-0000-0000-000000000001"
        assert payload0["filename"] == "report.pdf"
        assert payload0["file_type"] == "pdf"
        assert payload0["page"] == 1
        assert payload0["chunk_index"] == 0
        assert payload0["text"] == "First sentence for testing vector store."


def test_delete_document_vectors_success() -> None:
    """Test delete_document executes point deletion by document_id filter."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs")
        result = store.delete_document("doc_xyz_99")

        assert result == 1
        mock_client.delete.assert_called_once()
        call_kwargs = mock_client.delete.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_docs"
        selector = call_kwargs["points_selector"]
        assert selector.must[0].key == "document_id"
        assert selector.must[0].match.value == "doc_xyz_99"


def test_qdrant_health_check_connected() -> None:
    """Test health_check returns connected status dictionary when Qdrant is responsive."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs")
        res = store.health_check()

        assert res["status"] == "connected"
        assert res["collection"] == "test_docs"
        assert res["collection_exists"] is True


def test_upsert_chunks_api_failure_raises_qdrant_exception() -> None:
    """Test that Qdrant API failures during upsert raise QdrantAPIException."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.upsert.side_effect = Exception("Connection timeout")

    chunks = [
        EnrichedChunk(
            chunk_id="c1",
            document_id="doc_err",
            chunk_index=0,
            text="Text chunk",
            embedding=[0.1] * 768,
            metadata={},
        )
    ]

    with patch("packages.rag.vector_store.QdrantClient", return_value=mock_client):
        store = QdrantVectorStore(collection_name="test_docs")
        with pytest.raises(QdrantAPIException, match="Qdrant vector upsert failed"):
            store.upsert_chunks(chunks)
