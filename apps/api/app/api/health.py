from apps.api.app.models.health import HealthResponse, ServiceStatus
from fastapi import APIRouter, status
from packages.shared.settings import settings
from packages.sql_agent.database import db_manager
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Returns service readiness, PostgreSQL connectivity, Qdrant vector store status, and Gemini API configuration health status.",
)
async def health_check() -> HealthResponse:
    """Return component health status payload."""
    postgres_ok = True
    try:
        engine = db_manager.get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        postgres_ok = False

    qdrant_ok = True
    try:
        from packages.rag.vector_store import QdrantVectorStore

        store = QdrantVectorStore()
        check = store.health_check()
        qdrant_ok = check.get("status") == "connected"
    except Exception:
        qdrant_ok = False

    is_healthy = postgres_ok and qdrant_ok

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version=settings.APP_VERSION,
        services=ServiceStatus(
            api=True,
            postgres=postgres_ok,
            qdrant=qdrant_ok,
            qdrant_collection=settings.QDRANT_COLLECTION,
            gemini_configured=settings.is_gemini_configured,
        ),
    )
