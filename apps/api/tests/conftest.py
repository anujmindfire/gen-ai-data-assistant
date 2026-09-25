"""Pytest configuration and shared test fixtures."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path for monorepo imports
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from unittest.mock import MagicMock, patch

from apps.api.app.main import app


@pytest.fixture(autouse=True)
def mock_gemini_embeddings():
    """Autouse fixture to mock GoogleGenerativeAIEmbeddings for all tests."""
    with (
        patch(
            "packages.rag.embeddings.GoogleGenerativeAIEmbeddings.embed_documents",
            side_effect=lambda texts: [[0.1] * 768 for _ in texts],
        ),
        patch(
            "packages.rag.embeddings.GoogleGenerativeAIEmbeddings.embed_query",
            return_value=[0.1] * 768,
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_qdrant_client_network():
    """Autouse fixture to mock QdrantClient network calls for all tests."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.create_collection.return_value = None
    mock_client.upsert.return_value = None
    mock_client.delete.return_value = None

    with patch(
        "packages.rag.vector_store.QdrantClient",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a synchronous TestClient instance bound to the FastAPI app."""
    return TestClient(app)
