"""Unit tests for document ingestion, listing, and deletion endpoints."""

import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_ingest_txt_file_success(client: TestClient) -> None:
    """Test POST /documents/ingest with a valid text file."""
    file_content = b"This is a sample document for testing ingestion."
    files = {"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")}

    response = client.post("/documents/ingest", files=files)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_doc.txt"
    assert data["status"] == "ingested"
    assert "chunks_created" in data
    assert data["chunks_created"] >= 1


def test_ingest_md_file_success(client: TestClient) -> None:
    """Test POST /documents/ingest with a valid Markdown file."""
    file_content = b"# Document Title\n\nSample Markdown content."
    files = {"file": ("notes.md", io.BytesIO(file_content), "text/markdown")}

    response = client.post("/documents/ingest", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "notes.md"
    assert data["status"] == "ingested"
    assert data["chunks_created"] >= 1


def test_ingest_pdf_file_mocked_success(client: TestClient) -> None:
    """Test POST /documents/ingest with a PDF file using mocked PyPDFLoader."""
    pdf_content = b"%PDF-1.4 sample pdf content"
    files = {
        "file": (
            "handbook.pdf",
            io.BytesIO(pdf_content),
            "application/pdf",
        )
    }

    mock_doc = MagicMock()
    mock_doc.page_content = "Extracted PDF text page 1"

    with patch("packages.rag.ingest.PyPDFLoader.load", return_value=[mock_doc]):
        response = client.post("/documents/ingest", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "handbook.pdf"
        assert data["status"] == "ingested"
        assert data["chunks_created"] >= 1


def test_ingest_docx_file_mocked_success(client: TestClient) -> None:
    """Test POST /documents/ingest with a DOCX file using mocked Docx2txtLoader."""
    docx_content = b"docx binary content header"
    files = {
        "file": (
            "report.docx",
            io.BytesIO(docx_content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    mock_doc = MagicMock()
    mock_doc.page_content = "Extracted DOCX text payload"

    with patch("packages.rag.ingest.Docx2txtLoader.load", return_value=[mock_doc]):
        response = client.post("/documents/ingest", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "report.docx"
        assert data["status"] == "ingested"
        assert data["chunks_created"] >= 1


def test_ingest_invalid_file_extension_fails(client: TestClient) -> None:
    """Test POST /documents/ingest with unsupported extension (.png)."""
    files = {"file": ("image.png", io.BytesIO(b"png_data"), "image/png")}

    response = client.post("/documents/ingest", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DOCUMENT_VALIDATION_ERROR"


def test_ingest_empty_file_fails(client: TestClient) -> None:
    """Test POST /documents/ingest with empty 0-byte file."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

    response = client.post("/documents/ingest", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "DOCUMENT_VALIDATION_ERROR"


def test_list_and_delete_documents_flow(client: TestClient) -> None:
    """Test complete flow of uploading, listing, and deleting a document."""
    file_content = b"Content to be listed and deleted."
    files = {"file": ("policy.txt", io.BytesIO(file_content), "text/plain")}

    ingest_res = client.post("/documents/ingest", files=files)
    assert ingest_res.status_code == 201
    doc_id = ingest_res.json()["id"]

    list_res = client.get("/documents")
    assert list_res.status_code == 200
    doc_list = list_res.json()
    assert any(doc["id"] == doc_id for doc in doc_list)

    del_res = client.delete(f"/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Document deleted"

    list_res2 = client.get("/documents")
    assert not any(doc["id"] == doc_id for doc in list_res2.json())


def test_delete_non_existent_document_returns_404(client: TestClient) -> None:
    """Test DELETE /documents/{id} with invalid ID returns HTTP 404 Not Found."""
    response = client.delete("/documents/non_existent_uuid_12345")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"
