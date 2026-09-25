"""Unit and integration tests for LangGraph state router, nodes, workflow DAG, and /chat endpoint."""

import pytest
from fastapi.testclient import TestClient
from packages.graph.nodes import combined_node, rag_node, sql_node
from packages.graph.router import classify_question_heuristic, route_intent_node
from packages.graph.state import AgentState
from packages.graph.workflow import create_workflow_graph, graph_app, select_next_node
from packages.rag.rag_service import CitationSource, RAGResponse
from packages.sql_agent.models import SQLExecutionResult


def test_classify_question_heuristic() -> None:
    """Test heuristic keyword classifier assigns correct route types."""
    assert classify_question_heuristic("What is the leave policy?") == "rag"
    assert classify_question_heuristic("Top 5 customers by revenue") == "sql"
    assert (
        classify_question_heuristic(
            "What is the refund policy and how much revenue was refunded?"
        )
        == "combined"
    )


def test_route_intent_node_updates_state() -> None:
    """Test route_intent_node classifies question and updates state route."""
    state: AgentState = {"question": "How many orders were placed last month?"}
    updated = route_intent_node(state)
    assert updated.get("route") == "sql"


def test_select_next_node_decision() -> None:
    """Test select_next_node returns correct target node string."""
    assert select_next_node({"route": "rag"}) == "rag"
    assert select_next_node({"route": "sql"}) == "sql"
    assert select_next_node({"route": "combined"}) == "combined"
    assert select_next_node({}) == "rag"


def test_rag_node_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test rag_node executes RAGService and sets state rag_answer and sources."""
    mock_rag_res = RAGResponse(
        answer="Employees receive 20 days of leave.",
        sources=[CitationSource(filename="handbook.pdf", page=2, chunk_index=0)],
        query="leave policy",
    )

    monkeypatch.setattr(
        "packages.rag.rag_service.RAGService.answer_question",
        lambda self, question: mock_rag_res,
    )

    state: AgentState = {"question": "What is the leave policy?"}
    result = rag_node(state)

    assert result["rag_answer"] == "Employees receive 20 days of leave."
    assert result["final_answer"] == "Employees receive 20 days of leave."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["filename"] == "handbook.pdf"


def test_sql_node_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test sql_node executes SQLExecutorService and populates sql_query and sql_result."""
    mock_exec_res = SQLExecutionResult(
        question="Top customers by revenue",
        sql="SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 2;",
        columns=["name", "revenue"],
        rows=[["Alice", 1200], ["Bob", 950]],
        row_count=2,
        execution_duration_ms=10.0,
    )

    monkeypatch.setattr(
        "packages.sql_agent.executor.SQLExecutorService.execute_question",
        lambda self, question: mock_exec_res,
    )

    state: AgentState = {"question": "Top customers by revenue"}
    result = sql_node(state)

    assert (
        result["sql_query"]
        == "SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 2;"
    )
    assert result["sql_result"]["row_count"] == 2
    assert "Alice" in result["final_answer"]


def test_combined_node_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test combined_node executes both RAG and SQL services and fuses outputs."""
    mock_rag_res = RAGResponse(
        answer="Refunds are processed within 30 days.",
        sources=[CitationSource(filename="refund.pdf", page=1, chunk_index=0)],
        query="refund policy",
    )
    mock_exec_res = SQLExecutionResult(
        question="Refund policy and total refunded",
        sql="SELECT SUM(total_amount) FROM orders WHERE status = 'refunded';",
        columns=["sum"],
        rows=[[450.00]],
        row_count=1,
        execution_duration_ms=8.0,
    )

    monkeypatch.setattr(
        "packages.rag.rag_service.RAGService.answer_question",
        lambda self, question: mock_rag_res,
    )
    monkeypatch.setattr(
        "packages.sql_agent.executor.SQLExecutorService.execute_question",
        lambda self, question: mock_exec_res,
    )
    monkeypatch.setattr(
        "packages.shared.gemini.GeminiClient.chat",
        lambda self, prompt: (
            "Refunds take 30 days and total refunded last month was $450.00."
        ),
    )

    state: AgentState = {"question": "What is the refund policy and total refunded?"}
    result = combined_node(state)

    assert result["rag_answer"] == "Refunds are processed within 30 days."
    assert (
        result["sql_query"]
        == "SELECT SUM(total_amount) FROM orders WHERE status = 'refunded';"
    )
    assert len(result["sources"]) == 1
    assert "Refunds take 30 days" in result["final_answer"]


def test_combined_node_sql_failure_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test combined_node gracefully falls back to document answer if SQL execution fails."""
    mock_rag_res = RAGResponse(
        answer="Refunds are processed within 30 days.",
        sources=[CitationSource(filename="refund.pdf", page=1, chunk_index=0)],
        query="refund policy",
    )

    monkeypatch.setattr(
        "packages.rag.rag_service.RAGService.answer_question",
        lambda self, question: mock_rag_res,
    )

    def mock_failing_sql(self, question: str) -> None:
        raise Exception("Database connection timeout")

    monkeypatch.setattr(
        "packages.sql_agent.executor.SQLExecutorService.execute_question",
        mock_failing_sql,
    )

    state: AgentState = {"question": "What is the refund policy and total refunded?"}
    result = combined_node(state)

    assert result["rag_answer"] == "Refunds are processed within 30 days."
    assert "Refunds are processed within 30 days" in result["final_answer"]
    assert "could not be executed" in result["final_answer"]
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_workflow_graph_rag_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test full LangGraph StateGraph workflow execution for RAG route."""
    mock_rag_res = RAGResponse(
        answer="Leave policy grants 20 days.",
        sources=[CitationSource(filename="leave.pdf", page=1, chunk_index=0)],
        query="leave policy",
    )
    monkeypatch.setattr(
        "packages.rag.rag_service.RAGService.answer_question",
        lambda self, question: mock_rag_res,
    )

    app = create_workflow_graph()
    state = await app.ainvoke({"question": "What is the leave policy?"})

    assert state["route"] == "rag"
    assert state["final_answer"] == "Leave policy grants 20 days."


@pytest.mark.asyncio
async def test_workflow_graph_sql_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test full LangGraph StateGraph workflow execution for SQL route."""
    mock_exec_res = SQLExecutionResult(
        question="Top 5 customers by revenue",
        sql="SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 5;",
        columns=["name", "revenue"],
        rows=[["Alice", 1200]],
        row_count=1,
        execution_duration_ms=5.0,
    )
    monkeypatch.setattr(
        "packages.sql_agent.executor.SQLExecutorService.execute_question",
        lambda self, question: mock_exec_res,
    )

    state = await graph_app.ainvoke({"question": "Top 5 customers by revenue"})

    assert state["route"] == "sql"
    assert "Alice" in state["final_answer"]


def test_post_chat_endpoint_returns_route(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test POST /chat API endpoint returns HTTP 200 with answer, route, and sources."""
    mock_rag_res = RAGResponse(
        answer="Our leave policy allows 20 annual leave days.",
        sources=[CitationSource(filename="handbook.pdf", page=5, chunk_index=1)],
        query="What is the leave policy?",
    )
    monkeypatch.setattr(
        "packages.rag.rag_service.RAGService.answer_question",
        lambda self, question: mock_rag_res,
    )

    response = client.post(
        "/chat",
        json={"message": "What is the leave policy?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["route"] == "rag"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "handbook.pdf"
    assert data["provider"] == "gemini"
