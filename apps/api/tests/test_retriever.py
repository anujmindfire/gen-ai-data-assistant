"""Unit tests for VectorRetriever service and POST /documents/search endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from packages.rag.retriever import RetrievalResult, VectorRetriever


def test_retrieve_query_success() -> None:
    """Test successful vector retrieval generates query embedding and returns ranked RetrievalResult objects."""
    mock_raw_results = [
        {
            "chunk_id": "c1",
            "document_id": "doc_1",
            "filename": "handbook.pdf",
            "file_type": "pdf",
            "page": 14,
            "chunk_index": 0,
            "text": "Employees receive 20 annual leave days.",
            "score": 0.95,
        },
        {
            "chunk_id": "c2",
            "document_id": "doc_1",
            "filename": "handbook.pdf",
            "file_type": "pdf",
            "page": 15,
            "chunk_index": 1,
            "text": "Sick leave requires medical certificate after 3 days.",
            "score": 0.82,
        },
    ]

    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 768

    mock_store = MagicMock()
    mock_store.search.return_value = mock_raw_results

    retriever = VectorRetriever(
        embedding_service=mock_embedder,
        vector_store=mock_store,
        top_k=5,
        score_threshold=0.5,
    )

    results = retriever.retrieve("What is the leave policy?")

    mock_embedder.embed_text.assert_called_once_with("What is the leave policy?")
    mock_store.search.assert_called_once()
    assert len(results) == 2
    assert isinstance(results[0], RetrievalResult)
    assert results[0].chunk_id == "c1"
    assert results[0].score == 0.95
    assert results[0].filename == "handbook.pdf"
    assert results[0].page == 14
    assert results[1].score == 0.82


def test_retrieve_empty_query_raises_value_error() -> None:
    """Test that passing an empty or whitespace query raises ValueError."""
    retriever = VectorRetriever()

    with pytest.raises(ValueError, match="cannot be empty"):
        retriever.retrieve("")

    with pytest.raises(ValueError, match="cannot be empty"):
        retriever.retrieve("   \n ")


def test_retrieve_no_matching_results_returns_empty_list() -> None:
    """Test that vector search returning no matches returns an empty list."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 768

    mock_store = MagicMock()
    mock_store.search.return_value = []

    retriever = VectorRetriever(
        embedding_service=mock_embedder, vector_store=mock_store
    )
    results = retriever.retrieve("Unrelated topics search query")

    assert results == []


def test_retrieve_with_metadata_filtering() -> None:
    """Test passing optional document_id, filename, and file_type filters to retriever."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 768

    mock_store = MagicMock()
    mock_store.search.return_value = []

    retriever = VectorRetriever(
        embedding_service=mock_embedder, vector_store=mock_store
    )

    retriever.retrieve(
        question="leave policy",
        top_k=3,
        document_id="doc_999",
        filename="policy.pdf",
        file_type="pdf",
    )

    mock_store.search.assert_called_once_with(
        query_vector=[0.1] * 768,
        limit=3,
        score_threshold=0.5,
        document_id="doc_999",
        filename="policy.pdf",
        file_type="pdf",
    )


def test_post_documents_search_endpoint_success(client: TestClient) -> None:
    """Test POST /documents/search testing endpoint returns HTTP 200 OK with ranked results."""
    mock_result = RetrievalResult(
        chunk_id="c_test",
        document_id="doc_test",
        filename="employee_handbook.pdf",
        file_type="pdf",
        page=5,
        chunk_index=2,
        text="Paid time off rules.",
        score=0.91,
    )

    with patch(
        "packages.rag.retriever.VectorRetriever.retrieve",
        return_value=[mock_result],
    ):
        response = client.post(
            "/documents/search",
            json={"query": "Paid time off", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total_results"] == 1
        assert data["results"][0]["filename"] == "employee_handbook.pdf"
        assert data["results"][0]["score"] == 0.91


def test_post_documents_search_empty_query_fails_validation(
    client: TestClient,
) -> None:
    """Test POST /documents/search with empty query string returns HTTP 422 Unprocessable Content."""
    response = client.post("/documents/search", json={"query": ""})
    assert response.status_code == 422
