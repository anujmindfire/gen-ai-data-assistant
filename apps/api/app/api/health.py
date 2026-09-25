"""Health check router handling GET /health."""

from apps.api.app.models.health import HealthResponse, ServiceStatus
from fastapi import APIRouter, status
from packages.shared.settings import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Returns service readiness and configuration health status.",
)
async def health_check() -> HealthResponse:
    """Return component health status payload."""
    qdrant_ok = True
    try:
        from packages.rag.vector_store import QdrantVectorStore

        store = QdrantVectorStore()
        check = store.health_check()
        qdrant_ok = check.get("status") == "connected"
    except Exception:
        qdrant_ok = False

    return HealthResponse(
        status="healthy" if qdrant_ok else "degraded",
        services=ServiceStatus(
            api=True,
            postgres=True,
            qdrant=qdrant_ok,
            qdrant_collection=settings.QDRANT_COLLECTION,
            gemini_configured=settings.is_gemini_configured,
        ),
    )
