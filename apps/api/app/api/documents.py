"""Document management route handlers (/documents/ingest, /documents, /documents/{id})."""

from apps.api.app.dependencies.services import get_document_service
from apps.api.app.models.documents import (
    DocumentDeleteResponse,
    DocumentIngestResponse,
    DocumentItem,
)
from apps.api.app.services.document_service import DocumentService
from fastapi import APIRouter, Depends, File, UploadFile, status

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Document File",
    description="Uploads, parses, and registers document metadata for supported formats (.pdf, .docx, .txt, .md).",
)
async def ingest_document(
    file: UploadFile = File(..., description="Target document file to ingest"),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentIngestResponse:
    """Ingest uploaded document file."""
    return await doc_service.ingest_document(file=file)


@router.get(
    "",
    response_model=list[DocumentItem],
    status_code=status.HTTP_200_OK,
    summary="List Uploaded Documents",
    description="Returns array of all registered documents.",
)
async def list_documents(
    doc_service: DocumentService = Depends(get_document_service),
) -> list[DocumentItem]:
    """Retrieve list of registered documents."""
    response = await doc_service.list_documents()
    return response.documents


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document by ID",
    description="Purges document metadata record and deletes physical file from storage.",
)
async def delete_document(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    """Delete document by ID."""
    await doc_service.delete_document(document_id=document_id)
    return DocumentDeleteResponse(message="Document deleted")
