"""Tests for /health endpoint."""

from fastapi.testclient import TestClient


def test_health_endpoint_returns_200_and_healthy_status(client: TestClient) -> None:
    """Test that GET /health returns HTTP 200 OK with expected JSON body structure."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_placeholder_chat_returns_501(client: TestClient) -> None:
    """Test that POST /chat returns HTTP 501 Not Implemented."""
    response = client.post("/chat", json={"prompt": "Hello"})
    assert response.status_code == 501
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == 501


def test_placeholder_documents_ingest_returns_501(client: TestClient) -> None:
    """Test that POST /documents/ingest returns HTTP 501 Not Implemented."""
    response = client.post(
        "/documents/ingest",
        json={"title": "Test Doc", "content": "Sample content"},
    )
    assert response.status_code == 501
    data = response.json()
    assert data["error"]["code"] == 501
