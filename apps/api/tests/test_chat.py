"""Tests for POST /chat endpoint using unittest.mock."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_chat_endpoint_returns_200_and_gemini_response(
    client: TestClient,
) -> None:
    """Test POST /chat returns HTTP 200 OK with mocked Gemini response."""
    with patch(
        "apps.api.app.services.chat_service.gemini_chat",
        return_value="Hello! I am your AI assistant.",
    ):
        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Hello! I am your AI assistant."
        assert data["provider"] == "gemini"
        assert "model" in data


def test_chat_endpoint_handles_gemini_api_failure(
    client: TestClient,
) -> None:
    """Test POST /chat returns HTTP 502 BAD GATEWAY on Gemini API exception."""
    with patch(
        "apps.api.app.services.chat_service.gemini_chat",
        side_effect=Exception("API connection timeout"),
    ):
        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 502
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "GEMINI_API_ERROR"
        assert data["error"]["message"] == "Unable to reach Gemini."


def test_chat_endpoint_invalid_request_body_returns_422(
    client: TestClient,
) -> None:
    """Test POST /chat with invalid body returns HTTP 422 Unprocessable Entity."""
    response = client.post("/chat", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
