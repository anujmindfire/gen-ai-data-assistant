"""Document management route handlers (/documents/ingest, /documents, /documents/{id})."""

from apps.api.app.dependencies.services import get_document_service
from apps.api.app.models.documents import (
    DocumentIngestRequest,
    DocumentListResponse,
)
from apps.api.app.services.document_service import DocumentService
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/ingest",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Ingest Document into RAG Vector Store (Placeholder)",
    description="Parses, chunks, embeds, and indexes unstructured documents into Qdrant.",
)
async def ingest_document(
    request: DocumentIngestRequest,
    doc_service: DocumentService = Depends(get_document_service),
) -> None:
    """Placeholder endpoint for document ingestion pipeline.

    TODO (Phase 2):
        - Call DocumentIngestor and EmbeddingService to store document chunks in Qdrant.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document ingestion endpoint not implemented yet. TODO: Implement RAG ingestion pipeline.",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="List Ingested Documents (Placeholder)",
    description="Fetches metadata listing of documents stored in Qdrant vector database.",
)
async def list_documents(
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """Placeholder endpoint for listing ingested documents.

    TODO (Phase 2):
        - Query Qdrant collection payload points to return document catalog.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="List documents endpoint not implemented yet. TODO: Query vector database index.",
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Delete Document by ID (Placeholder)",
    description="Deletes all vectors and metadata matching target document_id.",
)
async def delete_document(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
) -> None:
    """Placeholder endpoint for purging document embeddings.

    TODO (Phase 2):
        - Remove document vector points from Qdrant index.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Delete document endpoint not implemented yet for ID '{document_id}'. TODO: Delete document from vector database.",
    )
