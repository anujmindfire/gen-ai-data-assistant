"""Pydantic schemas for /documents endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """Payload for initiating document ingestion."""

    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Raw text content of the document")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary metadata attributes"
    )


class DocumentItem(BaseModel):
    """Document metadata schema."""

    id: str
    title: str
    chunk_count: int
    created_at: str


class DocumentListResponse(BaseModel):
    """List response for documents endpoint."""

    documents: list[DocumentItem]
    total: int
