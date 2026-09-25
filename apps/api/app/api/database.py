"""Database schema inspection route handler for GET /database/schema."""

from fastapi import APIRouter, Query, status
from packages.sql_agent.models import DatabaseSchema
from packages.sql_agent.schema import SchemaInspectorService

router = APIRouter(prefix="/database", tags=["Database"])


@router.get(
    "/schema",
    response_model=DatabaseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Database Schema Metadata",
    description="Reflects PostgreSQL database tables, columns, primary keys, and foreign key relationships.",
)
async def get_database_schema(
    force_refresh: bool = Query(
        default=False,
        description="Force refresh to bypass in-memory schema cache",
    ),
) -> DatabaseSchema:
    """Return database schema metadata with dynamic introspection."""
    service = SchemaInspectorService()
    return service.get_schema(force_refresh=force_refresh)
