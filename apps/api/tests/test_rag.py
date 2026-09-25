"""Unit tests for RAGService answer generation with source citations and /chat endpoint integration."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from packages.rag.rag_service import CitationSource, RAGResponse, RAGService
from packages.rag.retriever import RetrievalResult


def test_rag_service_successful_answer_with_citations() -> None:
    """Test RAGService generates grounded answer with structured source citations."""
    mock_chunks = [
        RetrievalResult(
            chunk_id="c1",
            document_id="doc1",
            filename="employee_handbook.pdf",
            file_type="pdf",
            page=14,
            chunk_index=0,
            text="Employees receive 20 annual leave days per year.",
            score=0.92,
        ),
        RetrievalResult(
            chunk_id="c2",
            document_id="doc1",
            filename="employee_handbook.pdf",
            file_type="pdf",
            page=15,
            chunk_index=1,
            text="Unused leave cannot be carried over.",
            score=0.85,
        ),
    ]

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = mock_chunks

    mock_gemini = MagicMock()
    mock_gemini.chat.return_value = "Employees receive 20 annual leave days per year. Unused leave cannot be carried over."

    rag_service = RAGService(retriever=mock_retriever, gemini_client=mock_gemini)
    response = rag_service.answer_question("What is the leave policy?")

    mock_retriever.retrieve.assert_called_once_with(
        question="What is the leave policy?",
        top_k=None,
        score_threshold=None,
    )
    mock_gemini.chat.assert_called_once()
    prompt_used = mock_gemini.chat.call_args[0][0]
    assert "Context:" in prompt_used
    assert "employee_handbook.pdf" in prompt_used
    assert "What is the leave policy?" in prompt_used

    assert isinstance(response, RAGResponse)
    assert (
        response.answer
        == "Employees receive 20 annual leave days per year. Unused leave cannot be carried over."
    )
    assert len(response.sources) == 2
    assert response.sources[0].filename == "employee_handbook.pdf"
    assert response.sources[0].page == 14
    assert response.sources[1].page == 15


def test_rag_service_no_context_returns_safe_fallback() -> None:
    """Test RAGService returns safe fallback message and empty sources when retrieval finds no chunks."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = []

    mock_gemini = MagicMock()

    rag_service = RAGService(retriever=mock_retriever, gemini_client=mock_gemini)
    response = rag_service.answer_question("What is the quantum computing policy?")

    mock_retriever.retrieve.assert_called_once()
    mock_gemini.chat.assert_not_called()

    assert (
        response.answer
        == "I couldn't find relevant information in the uploaded documents."
    )
    assert response.sources == []


def test_rag_service_context_limit_truncation() -> None:
    """Test that context builder respects max_context_chars budget limit."""
    mock_chunks = [
        RetrievalResult(
            chunk_id=f"c{i}",
            document_id="doc1",
            filename="long_policy.pdf",
            file_type="pdf",
            page=i,
            chunk_index=i,
            text=f"This is chunk number {i} with long detailed content section." * 3,
            score=0.9 - (i * 0.1),
        )
        for i in range(5)
    ]

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = mock_chunks

    mock_gemini = MagicMock()
    mock_gemini.chat.return_value = "Answer synthesized from truncated context."

    rag_service = RAGService(
        retriever=mock_retriever,
        gemini_client=mock_gemini,
        max_context_chars=350,
    )
    response = rag_service.answer_question("Long policy query?")

    assert len(response.sources) < len(mock_chunks)
    assert mock_gemini.chat.called


def test_rag_service_empty_question_raises_value_error() -> None:
    """Test that empty user question raises ValueError."""
    rag_service = RAGService()

    with pytest.raises(ValueError, match="cannot be empty"):
        rag_service.answer_question("")

    with pytest.raises(ValueError, match="cannot be empty"):
        rag_service.answer_question("   \n ")


def test_chat_endpoint_returns_rag_response_with_citations(
    client: TestClient,
) -> None:
    """Test POST /chat returns RAG answer with source citations."""
    mock_rag_response = RAGResponse(
        answer="Refunds are processed within 14 business days.",
        sources=[CitationSource(filename="refund_policy.pdf", page=3, chunk_index=1)],
    )

    with patch(
        "packages.rag.rag_service.RAGService.answer_question",
        return_value=mock_rag_response,
    ):
        response = client.post("/chat", json={"message": "What is refund time?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Refunds are processed within 14 business days."
        assert data["provider"] == "gemini"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["filename"] == "refund_policy.pdf"
        assert data["sources"][0]["page"] == 3
        assert data["sources"][0]["chunk_index"] == 1
