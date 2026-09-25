"""Pytest configuration and shared test fixtures."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path for monorepo imports
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from unittest.mock import patch

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


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a synchronous TestClient instance bound to the FastAPI app."""
    return TestClient(app)
