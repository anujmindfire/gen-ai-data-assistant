"""Pydantic schemas for health check endpoint."""

from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Component service health and configuration flags."""

    api: bool = Field(default=True, description="API server status")
    postgres: bool = Field(default=True, description="PostgreSQL status")
    qdrant: bool = Field(default=True, description="Qdrant vector DB status")
    qdrant_collection: str = Field(
        default="company_documents",
        description="Active Qdrant collection name",
    )
    gemini_configured: bool = Field(
        default=False, description="Gemini API key configuration status"
    )


class HealthResponse(BaseModel):
    """Health check endpoint response payload."""

    status: str = Field(
        default="healthy", description="Current health status of API service"
    )
    services: ServiceStatus = Field(
        description="Services readiness and configuration status"
    )
