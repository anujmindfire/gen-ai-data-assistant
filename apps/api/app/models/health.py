"""Pydantic schemas for health check endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check endpoint response payload."""

    status: str = Field(
        default="healthy", description="Current health status of the API service"
    )
    timestamp: str = Field(description="ISO 8601 UTC timestamp of response")
    version: str = Field(
        default="0.1.0", description="Current application semantic version"
    )
