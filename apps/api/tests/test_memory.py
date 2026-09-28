"""Unit and integration tests for ConversationMemoryManager and session endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from packages.graph.memory import ConversationMemoryManager, memory_manager


def test_memory_manager_create_and_get_session() -> None:
    """Test session creation and retrieval in ConversationMemoryManager."""
    mgr = ConversationMemoryManager(max_messages=10)
    session = mgr.create_session(session_id="custom_sess_1")

    assert session.session_id == "custom_sess_1"
    assert session.history == []

    fetched = mgr.get_session("custom_sess_1")
    assert fetched is not None
    assert fetched.session_id == "custom_sess_1"

    # Non-existent session
    assert mgr.get_session("non_existent_id") is None


def test_memory_manager_add_interaction_and_trimming() -> None:
    """Test adding interactions and memory trimming when history exceeds max_messages."""
    mgr = ConversationMemoryManager(max_messages=4)
    sess_id = "trim_test_session"

    # Add 1st interaction pair (2 messages: user + assistant)
    mgr.add_interaction(
        session_id=sess_id,
        question="What is total revenue?",
        response="Total revenue is $500,000.",
        route="sql",
        sql="SELECT SUM(amount) FROM sales;",
    )

    session = mgr.get_session(sess_id)
    assert session is not None
    assert len(session.history) == 2
    assert session.previous_route == "sql"
    assert session.previous_sql == "SELECT SUM(amount) FROM sales;"

    # Add 2nd interaction pair (now 4 messages total)
    mgr.add_interaction(
        session_id=sess_id,
        question="What about top customer?",
        response="Top customer is Acme Corp.",
        route="sql",
        sql="SELECT customer FROM sales ORDER BY amount DESC LIMIT 1;",
    )

    session = mgr.get_session(sess_id)
    assert session is not None
    assert len(session.history) == 4

    # Add 3rd interaction pair (exceeds max_messages=4, should trim 2 oldest messages)
    mgr.add_interaction(
        session_id=sess_id,
        question="Tell me about Acme Corp.",
        response="Acme Corp is a leading B2B client.",
        route="rag",
        sources=[{"filename": "acme.pdf", "page": 1}],
    )

    session = mgr.get_session(sess_id)
    assert session is not None
    assert len(session.history) == 4  # Trimmed from 6 down to 4
    # The oldest pair ("What is total revenue?") was dropped
    assert session.history[0].content == "What about top customer?"
    assert session.history[-1].content == "Acme Corp is a leading B2B client."


def test_memory_manager_delete_and_clear_all() -> None:
    """Test session deletion and clear_all operations."""
    mgr = ConversationMemoryManager()
    mgr.create_session("sess_del_1")
    sess2 = mgr.create_session("sess_del_2")

    assert mgr.get_session("sess_del_1") is not None
    assert mgr.delete_session("sess_del_1") is True
    assert mgr.get_session("sess_del_1") is None
    assert mgr.delete_session("sess_del_1") is False

    mgr.clear_all()
    assert mgr.get_session(sess2.session_id) is None


def test_chat_endpoint_creates_and_persists_session(client: TestClient) -> None:
    """Test POST /chat creates a new session_id and follow-up query reuses session."""
    memory_manager.clear_all()

    mock_state_1 = {
        "question": "Which customer spent the most?",
        "route": "sql",
        "final_answer": "Customer Acme Corp spent $150,000.",
        "sql": "SELECT customer_name, SUM(total) FROM orders GROUP BY 1 ORDER BY 2 DESC LIMIT 1;",
        "sources": [],
    }

    with patch(
        "packages.graph.workflow.graph_app.ainvoke",
        return_value=mock_state_1,
    ):
        response1 = client.post(
            "/chat", json={"message": "Which customer spent the most?"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert "session_id" in data1
        session_id = data1["session_id"]
        assert session_id is not None
        assert data1["answer"] == "Customer Acme Corp spent $150,000."

    # Follow-up request using same session_id
    mock_state_2 = {
        "question": "What about the second highest?",
        "route": "sql",
        "final_answer": "The second highest spending customer is Globex Corp.",
        "sql": "SELECT customer_name, SUM(total) FROM orders GROUP BY 1 ORDER BY 2 DESC LIMIT 1 OFFSET 1;",
        "sources": [],
    }

    with patch(
        "packages.graph.workflow.graph_app.ainvoke",
        return_value=mock_state_2,
    ) as mock_ainvoke:
        response2 = client.post(
            "/chat",
            json={
                "message": "What about the second highest?",
                "session_id": session_id,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        assert data2["answer"] == "The second highest spending customer is Globex Corp."

        # Verify initial_state passed to ainvoke included conversation history
        called_args = mock_ainvoke.call_args[0][0]
        assert called_args["session_id"] == session_id
        assert len(called_args["conversation_history"]) == 2
        assert (
            called_args["conversation_history"][0]["content"]
            == "Which customer spent the most?"
        )


def test_get_and_delete_session_endpoints(client: TestClient) -> None:
    """Test GET /sessions/{id} and DELETE /sessions/{id} HTTP endpoints."""
    memory_manager.clear_all()
    session = memory_manager.create_session("api_test_sess_100")
    memory_manager.add_interaction(
        session_id=session.session_id,
        question="Hi",
        response="Hello!",
    )

    # GET /sessions/{id} success
    resp_get = client.get(f"/sessions/{session.session_id}")
    assert resp_get.status_code == 200
    sess_data = resp_get.json()
    assert sess_data["session_id"] == "api_test_sess_100"
    assert len(sess_data["history"]) == 2

    # GET /sessions/{id} not found
    resp_get_404 = client.get("/sessions/unknown_session_id")
    assert resp_get_404.status_code == 404
    assert "not found" in resp_get_404.json()["error"]["message"]

    # DELETE /sessions/{id} success
    resp_del = client.delete(f"/sessions/{session.session_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["message"] == "Session deleted successfully"

    # DELETE /sessions/{id} not found
    resp_del_404 = client.delete(f"/sessions/{session.session_id}")
    assert resp_del_404.status_code == 404
