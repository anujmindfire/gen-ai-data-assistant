"""Document management service for saving, parsing, listing, and deleting documents."""

import datetime
import os
import uuid

from apps.api.app.core.exceptions import (
    DocumentNotFoundException,
    DocumentValidationException,
)
from apps.api.app.models.documents import (
    DocumentIngestResponse,
    DocumentItem,
    DocumentListResponse,
)
from fastapi import UploadFile
from packages.rag.ingest import SUPPORTED_EXTENSIONS, DocumentParser
from packages.shared.db import doc_repository
from packages.shared.logging import get_logger

logger = get_logger(__name__)

STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../data/documents")
)


class DocumentService:
    """Service layer managing physical document storage, parsing, and persistence."""

    def __init__(self, storage_dir: str = STORAGE_DIR) -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.parser = DocumentParser()

    async def ingest_document(self, file: UploadFile) -> DocumentIngestResponse:
        """Handle multipart document upload, parsing, storage, and metadata persistence.

        Args:
            file: FastAPI UploadFile object.

        Returns:
            DocumentIngestResponse: Ingestion metadata response schema.

        Raises:
            DocumentValidationException: If format is unsupported, empty, or parsing fails.
        """
        filename = file.filename or "unnamed_document"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            logger.warning(
                f"Rejected upload '{filename}': Unsupported file format '{ext}'"
            )
            raise DocumentValidationException(
                message=f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt, .md"
            )

        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}_{filename}"
        target_path = os.path.join(self.storage_dir, safe_filename)

        try:
            content = await file.read()
            file_size = len(content)

            if file_size == 0:
                logger.warning(f"Rejected upload '{filename}': File is empty (0 bytes)")
                raise DocumentValidationException(
                    message=f"File '{filename}' is empty."
                )

            with open(target_path, "wb") as f:
                f.write(content)

            logger.info(
                f"Saved physical file '{filename}' to '{target_path}' (size: {file_size} bytes)"
            )

            metadata = self.parser.parse_document(
                target_path, original_filename=filename
            )
            normalized_type = ext.lstrip(".")

            record = {
                "id": doc_id,
                "filename": filename,
                "type": normalized_type,
                "file_path": target_path,
                "size": file_size,
                "pages": metadata.get("pages", 1),
                "uploaded_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }

            doc_repository.add(record)
            logger.info(
                f"Successfully registered document '{filename}' (ID: {doc_id}, type: {normalized_type})"
            )

            return DocumentIngestResponse(
                id=doc_id,
                filename=filename,
                type=normalized_type,
                size=file_size,
                status="ingested",
            )
        except DocumentValidationException:
            if os.path.exists(target_path):
                os.remove(target_path)
            raise
        except Exception as exc:
            if os.path.exists(target_path):
                os.remove(target_path)
            logger.error(
                f"Failed to ingest document '{filename}': {str(exc)}",
                exc_info=True,
            )
            raise DocumentValidationException(
                message=f"Corrupted or invalid document file '{filename}': {str(exc)}"
            ) from exc

    async def list_documents(self) -> DocumentListResponse:
        """Fetch all stored document records.

        Returns:
            DocumentListResponse: List of stored documents.
        """
        records = doc_repository.list_all()
        items = [
            DocumentItem(
                id=r["id"],
                filename=r["filename"],
                type=r["type"],
            )
            for r in records
        ]
        logger.info(f"Retrieved {len(items)} stored document records.")
        return DocumentListResponse(documents=items)

    async def delete_document(self, document_id: str) -> None:
        """Delete document file from disk and remove metadata record.

        Args:
            document_id: Unique document UUID string.

        Raises:
            DocumentNotFoundException: If document ID is not found.
        """
        record = doc_repository.get(document_id)
        if not record:
            logger.warning(f"Deletion failed: Document ID '{document_id}' not found.")
            raise DocumentNotFoundException(
                message=f"Document with ID '{document_id}' not found."
            )

        file_path = record.get("file_path")
        filename = record.get("filename", "unknown")

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted physical document file: '{file_path}'")
            except OSError as exc:
                logger.error(
                    f"Failed to delete file '{file_path}' from disk: {str(exc)}"
                )

        doc_repository.delete(document_id)
        logger.info(
            f"Successfully deleted document record '{filename}' (ID: {document_id})"
        )
