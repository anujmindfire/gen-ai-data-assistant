"""Unit tests for document chunking service."""

import pytest
from packages.rag.chunking import DocumentChunker, TextChunk


def test_chunk_creation_small_document() -> None:
    """Test that a document smaller than chunk_size produces exactly 1 chunk."""
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
    small_text = (
        "This is a short text string well below the five hundred character limit."
    )

    chunks = chunker.split_text(
        text=small_text,
        document_id="doc_123",
        metadata={"filename": "small.txt"},
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, TextChunk)
    assert chunk.document_id == "doc_123"
    assert chunk.chunk_index == 0
    assert chunk.text == small_text
    assert chunk.metadata["filename"] == "small.txt"
    assert chunk.metadata["chunk_index"] == 0


def test_chunk_creation_large_document_and_overlap() -> None:
    """Test that a large document produces multiple ordered chunks with preserved overlap."""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=30)
    paragraphs = [
        f"Paragraph number {i} with some additional descriptive text to fill space."
        for i in range(10)
    ]
    large_text = "\n\n".join(paragraphs)

    chunks = chunker.split_text(
        text=large_text,
        document_id="doc_large",
        metadata={"filename": "large.txt"},
    )

    assert len(chunks) > 1

    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.document_id == "doc_large"
        assert c.metadata["filename"] == "large.txt"
        assert len(c.text) <= 100

    first_chunk_end = chunks[0].text[-15:]
    second_chunk_text = chunks[1].text
    assert any(part in second_chunk_text for part in first_chunk_end.split())


def test_chunking_empty_document_raises_error() -> None:
    """Test that empty or whitespace text raises ValueError."""
    chunker = DocumentChunker()

    with pytest.raises(ValueError, match="Cannot chunk empty"):
        chunker.split_text(text="", document_id="doc_empty")

    with pytest.raises(ValueError, match="Cannot chunk empty"):
        chunker.split_text(text="   \n\n  ", document_id="doc_empty")


def test_split_document_dictionary_payload() -> None:
    """Test split_document with a parsed document payload dictionary."""
    chunker = DocumentChunker(chunk_size=200, chunk_overlap=50)
    parsed_doc = {
        "text": "Header Section\n\nContent paragraph 1.\n\nContent paragraph 2.",
        "filename": "policy.pdf",
        "file_type": "pdf",
        "pages": 2,
    }

    chunks = chunker.split_document(parsed_doc, document_id="doc_policy")
    assert len(chunks) >= 1
    assert chunks[0].metadata["filename"] == "policy.pdf"
    assert chunks[0].metadata["file_type"] == "pdf"
    assert chunks[0].metadata["total_pages"] == 2
