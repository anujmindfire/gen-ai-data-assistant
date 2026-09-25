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
    return HealthResponse(
        status="healthy",
        services=ServiceStatus(
            api=True,
            postgres=True,
            qdrant=True,
            gemini_configured=settings.is_gemini_configured,
        ),
    )
