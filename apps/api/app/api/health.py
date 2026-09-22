"""Health check router handling GET /health."""

from fastapi import APIRouter, status
from apps.api.app.models.health import HealthResponse
from packages.shared.settings import settings
from packages.shared.utils import get_utc_now

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Returns the current operating status and API version.",
)
async def health_check() -> HealthResponse:
    """Return health status payload."""
    return HealthResponse(
        status="healthy",
        timestamp=get_utc_now(),
        version=settings.APP_VERSION,
    )
