"""Pydantic schemas for /documents endpoints."""

from pydantic import BaseModel, Field


class DocumentIngestResponse(BaseModel):
    """Response payload returned by POST /documents/ingest."""

    id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original filename of uploaded document")
    status: str = Field(default="ingested", description="Ingestion processing status")
    chunks_created: int = Field(
        ..., description="Number of text chunks created from the document"
    )


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


class DocumentSearchRequest(BaseModel):
    """Request payload for POST /documents/search testing endpoint."""

    query: str = Field(..., min_length=1, description="Search query string")
    top_k: int | None = Field(
        default=None, description="Optional top-k nearest neighbors limit"
    )
    score_threshold: float | None = Field(
        default=None, description="Optional minimum score cutoff"
    )
    document_id: str | None = Field(
        default=None, description="Optional document ID metadata filter"
    )
    filename: str | None = Field(
        default=None, description="Optional filename metadata filter"
    )
    file_type: str | None = Field(
        default=None, description="Optional file type metadata filter"
    )


class DocumentSearchResponse(BaseModel):
    """Response payload returned by POST /documents/search."""

    results: list[dict] = Field(
        ...,
        description="Ranked list of matching document chunks with metadata and scores",
    )
    total_results: int = Field(
        ..., description="Total count of retrieved matching chunks"
    )
