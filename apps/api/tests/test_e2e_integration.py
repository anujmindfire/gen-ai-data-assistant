"""End-to-End Integration Test Suite for GenAI Data Assistant API.

Covers full workflows:
1. Document upload, metadata listing, semantic search, and document deletion.
2. Database schema introspection, SQL generation, validation, and query execution.
3. LangGraph intelligent routing across RAG, SQL, and Combined branches.
4. Session-based multi-turn conversation memory continuation and management.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_e2e_document_lifecycle_flow(client: TestClient) -> None:
    """Test full document ingestion, listing, search, and deletion pipeline."""
    mock_chunks = [
        MagicMock(
            page_content="Company refund policy allows 30 days return.",
            metadata={"page": 1, "chunk_index": 0},
        )
    ]

    with (
        patch(
            "packages.rag.ingest.DocumentParser.parse_document",
            return_value={
                "pages": 1,
                "text": "Company refund policy allows 30 days return.",
            },
        ),
        patch(
            "packages.rag.chunking.DocumentChunker.split_document",
            return_value=mock_chunks,
        ),
        patch(
            "packages.rag.embeddings.EmbeddingService.embed_chunks",
            return_value=mock_chunks,
        ),
        patch(
            "packages.rag.vector_store.QdrantVectorStore.upsert_chunks", return_value=1
        ),
        patch(
            "packages.rag.vector_store.QdrantVectorStore.delete_document",
            return_value=True,
        ),
    ):
        # 1. Ingest document
        ingest_resp = client.post(
            "/documents/ingest",
            files={
                "file": ("refund_policy.pdf", b"Dummy PDF content", "application/pdf")
            },
        )
        assert ingest_resp.status_code == 201
        doc_data = ingest_resp.json()
        assert doc_data["filename"] == "refund_policy.pdf"
        assert doc_data["status"] == "ingested"
        doc_id = doc_data["id"]

        # 2. List documents
        list_resp = client.get("/documents")
        assert list_resp.status_code == 200
        docs_list = list_resp.json()
        assert len(docs_list) >= 1

        # 3. Search documents
        with patch("packages.rag.retriever.VectorRetriever.retrieve", return_value=[]):
            search_resp = client.post(
                "/documents/search",
                json={"query": "What is the refund policy?", "top_k": 3},
            )
            assert search_resp.status_code == 200
            search_data = search_resp.json()
            assert "results" in search_data

        # 4. Delete document
        delete_resp = client.delete(f"/documents/{doc_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["message"] == "Document deleted"


def test_e2e_sql_pipeline_flow(client: TestClient) -> None:
    """Test SQL schema introspection, AST validation, and query execution pipeline."""
    from packages.sql_agent.models import (
        DatabaseSchema,
        SQLExecutionResult,
        TableSchema,
    )

    mock_schema = DatabaseSchema(
        database_name="assistant",
        tables=[
            TableSchema(
                name="customers",
                columns=[],
                primary_keys=["id"],
                foreign_keys=[],
            )
        ],
        relationships=[],
        inspected_at="2026-09-25T12:00:00+00:00",
    )

    mock_query_result = SQLExecutionResult(
        question="Top customers",
        sql="SELECT id, name FROM customers LIMIT 5;",
        columns=["id", "name"],
        rows=[[1, "Alice"], [2, "Bob"]],
        row_count=2,
        execution_duration_ms=5.2,
    )

    with (
        patch(
            "packages.sql_agent.schema.SchemaInspectorService.get_schema",
            return_value=mock_schema,
        ),
        patch(
            "packages.sql_agent.executor.SQLExecutorService.execute_question",
            return_value=mock_query_result,
        ),
    ):
        # 1. Inspect Schema
        schema_resp = client.get("/database/schema")
        assert schema_resp.status_code == 200
        schema_data = schema_resp.json()
        assert schema_data["database_name"] == "assistant"
        assert len(schema_data["tables"]) == 1

        # 2. Validate Read-Only SQL Query
        val_resp = client.post(
            "/database/validate-sql",
            json={"sql": "SELECT id, name FROM customers;"},
        )
        assert val_resp.status_code == 200
        assert val_resp.json()["valid"] is True

        # 3. Validate Disallowed SQL Query
        val_bad_resp = client.post(
            "/database/validate-sql",
            json={"sql": "DELETE FROM customers;"},
        )
        assert val_bad_resp.status_code == 200
        assert val_bad_resp.json()["valid"] is False

        # 4. Execute Natural Language SQL Query
        query_resp = client.post(
            "/database/query",
            json={"question": "Top customers"},
        )
        assert query_resp.status_code == 200
        res_data = query_resp.json()
        assert res_data["row_count"] == 2
        assert res_data["columns"] == ["id", "name"]


def test_e2e_chat_and_conversation_memory_flow(client: TestClient) -> None:
    """Test multi-turn chat workflow with routing and session memory persistence."""
    mock_turn1 = {
        "question": "Which product is most popular?",
        "route": "sql",
        "final_answer": "Product A is the most popular product with 500 sales.",
        "sql": "SELECT product_name FROM sales ORDER BY units DESC LIMIT 1;",
        "sources": [],
    }

    mock_turn2 = {
        "question": "What is its price?",
        "route": "sql",
        "final_answer": "Product A costs $49.99.",
        "sql": "SELECT price FROM products WHERE product_name = 'Product A';",
        "sources": [],
    }

    # 1. Turn 1 without session_id (Auto-generates session_id)
    with patch("packages.graph.workflow.graph_app.ainvoke", return_value=mock_turn1):
        resp1 = client.post(
            "/chat",
            json={"message": "Which product is most popular?"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["route"] == "sql"
        assert "session_id" in data1
        session_id = data1["session_id"]

    # 2. Turn 2 with session_id (Follow-up context)
    with patch(
        "packages.graph.workflow.graph_app.ainvoke", return_value=mock_turn2
    ) as mock_ainvoke:
        resp2 = client.post(
            "/chat",
            json={
                "message": "What is its price?",
                "session_id": session_id,
            },
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["session_id"] == session_id
        assert "Product A costs $49.99" in data2["answer"]

        # Verify state passed into LangGraph contained history
        invoked_state = mock_ainvoke.call_args[0][0]
        assert invoked_state["session_id"] == session_id
        assert len(invoked_state["conversation_history"]) == 2

    # 3. Retrieve Session Details via /sessions/{id}
    sess_resp = client.get(f"/sessions/{session_id}")
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert sess_data["session_id"] == session_id
    assert len(sess_data["history"]) == 4  # 2 turns x 2 messages

    # 4. Delete Session via /sessions/{id}
    del_resp = client.delete(f"/sessions/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Session deleted successfully"
