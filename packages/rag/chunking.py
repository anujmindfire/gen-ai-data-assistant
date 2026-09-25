"""Document chunking service using LangChain's RecursiveCharacterTextSplitter."""

import uuid
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class TextChunk(BaseModel):
    """Normalized text chunk schema representing a segment of a document."""

    chunk_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique UUID for this text chunk",
    )
    document_id: str = Field(..., description="Parent document unique ID")
    chunk_index: int = Field(
        ..., description="Zero-based sequential index of chunk within document"
    )
    text: str = Field(..., description="Text content body of chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved metadata (filename, page_number, file_type, chunk_size)",
    )


class DocumentChunker:
    """Service wrapping RecursiveCharacterTextSplitter for document chunking."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
        self.chunk_overlap = (
            chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
        )

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) must be smaller than CHUNK_SIZE ({self.chunk_size})."
            )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        logger.info(
            f"Initialized DocumentChunker (chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap})"
        )

    def split_text(
        self,
        text: str,
        document_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Split raw text string into a list of TextChunk objects.

        Args:
            text: Raw input text.
            document_id: Parent document UUID.
            metadata: Base metadata dictionary to include in each chunk.

        Returns:
            List[TextChunk]: Ordered list of chunk objects.

        Raises:
            ValueError: If input text is empty or whitespace-only.
        """
        if not text or not text.strip():
            raise ValueError("Cannot chunk empty or whitespace-only text.")

        base_meta = metadata.copy() if metadata else {}
        raw_splits = self.text_splitter.split_text(text)

        chunks: list[TextChunk] = []
        for idx, chunk_text in enumerate(raw_splits):
            clean_text = chunk_text.strip()
            if not clean_text:
                continue

            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "chunk_size": len(clean_text),
            }

            chunks.append(
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=idx,
                    text=clean_text,
                    metadata=chunk_meta,
                )
            )

        avg_size = sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0
        logger.info(
            f"Created {len(chunks)} chunks for document_id '{document_id}' (avg size: {avg_size} chars)"
        )
        return chunks

    def split_document(
        self, parsed_doc: dict[str, Any], document_id: str
    ) -> list[TextChunk]:
        """Split parsed document payload into structured TextChunk instances.

        Args:
            parsed_doc: Dictionary returned by DocumentParser (contains 'text', 'filename', 'file_type', 'pages').
            document_id: Parent document UUID.

        Returns:
            List[TextChunk]: List of generated text chunks.
        """
        extracted_text = parsed_doc.get("text", "")
        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                f"Document '{parsed_doc.get('filename', document_id)}' contains no text content to chunk."
            )

        base_metadata = {
            "filename": parsed_doc.get("filename", ""),
            "file_type": parsed_doc.get("file_type", ""),
            "total_pages": parsed_doc.get("pages", 1),
            "page_number": parsed_doc.get("page_number", 1),
        }

        return self.split_text(
            text=extracted_text,
            document_id=document_id,
            metadata=base_metadata,
        )

    def split_documents(self, parsed_docs: list[dict[str, Any]]) -> list[TextChunk]:
        """Process multiple parsed documents and return aggregated list of TextChunks.

        Args:
            parsed_docs: List of parsed document dictionaries.

        Returns:
            List[TextChunk]: Aggregated ordered text chunks.
        """
        all_chunks: list[TextChunk] = []
        for doc in parsed_docs:
            doc_id = doc.get("id", str(uuid.uuid4()))
            chunks = self.split_document(doc, document_id=doc_id)
            all_chunks.extend(chunks)
        return all_chunks
