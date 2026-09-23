"""Pydantic schemas for /documents endpoints."""

from pydantic import BaseModel, Field


class DocumentIngestResponse(BaseModel):
    """Response payload returned by POST /documents/ingest."""

    id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original filename of uploaded document")
    type: str = Field(
        ...,
        description="Normalized document file extension (pdf, docx, txt, md)",
    )
    size: int = Field(..., description="File size in bytes")
    status: str = Field(default="ingested", description="Ingestion processing status")


class DocumentItem(BaseModel):
    """Document metadata item schema for GET /documents response."""

    id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Document filename")
    type: str = Field(..., description="Document file extension type")


class DocumentListResponse(BaseModel):
    """Response list payload returned by GET /documents."""

    documents: list[DocumentItem] = Field(description="Array of stored document items")


class DocumentDeleteResponse(BaseModel):
    """Response payload returned by DELETE /documents/{id}."""

    message: str = Field(
        default="Document deleted",
        description="Status message confirming document deletion",
    )
