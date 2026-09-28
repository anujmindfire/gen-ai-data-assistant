from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_endpoint_returns_200_and_services_status(
    client: TestClient,
) -> None:
    """Test that GET /health returns HTTP 200 OK with enhanced services dictionary."""
    with (
        patch("packages.sql_agent.database.db_manager.get_engine"),
        patch(
            "packages.rag.vector_store.QdrantVectorStore.health_check",
            return_value={"status": "connected"},
        ),
    ):
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["api"] is True
        assert data["services"]["postgres"] is True
        assert data["services"]["qdrant"] is True
        assert isinstance(data["services"]["gemini_configured"], bool)
