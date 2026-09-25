"""Document parsing and metadata extraction service using LangChain loaders."""

import os
from typing import Any

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)

from packages.shared.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class DocumentParser:
    """Document loader and parser detecting file format and extracting text & metadata."""

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if file extension is supported."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def get_file_type(file_path: str) -> str:
        """Return normalized file type extension without dot."""
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext

    def parse_document(self, file_path: str, original_filename: str) -> dict[str, Any]:
        """Load document from disk, extract text contents and metadata.

        Args:
            file_path: Physical storage path to document file.
            original_filename: Original name of uploaded file.

        Returns:
            Dict[str, Any]: Metadata containing text content, pages count, size, and file type.

        Raises:
            ValueError: If file extension is unsupported, empty, or corrupted.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError(f"File is empty: {original_filename}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt, .md"
            )

        logger.info(
            f"Parsing document '{original_filename}' (type: {ext}, size: {file_size} bytes)"
        )

        try:
            pages_count = 1
            extracted_text = ""

            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                pages_count = len(docs)
                extracted_text = "\n\n".join(d.page_content for d in docs)
            elif ext == ".docx":
                loader = Docx2txtLoader(file_path)
                docs = loader.load()
                extracted_text = "\n\n".join(d.page_content for d in docs)
                pages_count = max(1, len(extracted_text.split("\n\n")))
            elif ext in (".txt", ".md"):
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()
                extracted_text = "\n\n".join(d.page_content for d in docs)
                pages_count = max(1, len(extracted_text.split("\n\n")))

            logger.info(
                f"Successfully parsed document '{original_filename}': {pages_count} pages/sections extracted."
            )

            return {
                "filename": original_filename,
                "file_type": ext.lstrip("."),
                "file_path": file_path,
                "size": file_size,
                "pages": pages_count,
                "text": extracted_text,
            }
        except Exception as exc:
            logger.error(
                f"Failed to parse document '{original_filename}': {str(exc)}",
                exc_info=True,
            )
            raise ValueError(
                f"Corrupted or invalid document file '{original_filename}': {str(exc)}"
            ) from exc


# Backwards compatible class name
DocumentIngestor = DocumentParser
