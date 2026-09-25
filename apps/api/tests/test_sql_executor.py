"""Unit and integration tests for SQLExecutorService and POST /database/query API endpoint."""

from unittest.mock import MagicMock

import pytest
from apps.api.app.core.exceptions import DatabaseException
from fastapi.testclient import TestClient
from packages.sql_agent.executor import SQLExecutorService, _serialize_cell
from packages.sql_agent.models import (
    SQLExecutionResult,
    SQLGenerateResponse,
    SQLQueryResult,
)
from sqlalchemy import Engine, create_engine, text


@pytest.fixture
def sqlite_engine() -> Engine:
    """Fixture providing an in-memory SQLite database pre-populated with test tables."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(50), revenue NUMERIC);"
            )
        )
        conn.execute(
            text(
                "INSERT INTO customers VALUES (1, 'Alice', 1200), (2, 'Bob', 950), (3, 'Charlie', 1500), (4, 'David', 800), (5, 'Eve', 2000);"
            )
        )
        conn.commit()
    return engine


def test_serialize_cell_primitives_and_types() -> None:
    """Test _serialize_cell converts dates, decimals, UUIDs, and primitives to JSON types."""
    import datetime
    import decimal
    import uuid

    assert _serialize_cell(123) == 123
    assert _serialize_cell("Alice") == "Alice"
    assert _serialize_cell(None) is None
    assert _serialize_cell(datetime.date(2026, 9, 25)) == "2026-09-25"
    assert _serialize_cell(decimal.Decimal("123.45")) == "123.45"

    uid = uuid.uuid4()
    assert _serialize_cell(uid) == str(uid)


def test_execute_raw_sql_valid_query(sqlite_engine: Engine) -> None:
    """Test execute_raw_sql executes valid SELECT query and returns structured results."""
    executor = SQLExecutorService(engine=sqlite_engine)
    result = executor.execute_raw_sql(
        "SELECT name, revenue FROM customers ORDER BY id ASC;"
    )

    assert isinstance(result, SQLQueryResult)
    assert result.columns == ["name", "revenue"]
    assert result.row_count == 5
    assert result.rows[0] == ["Alice", 1200]
    assert result.rows[1] == ["Bob", 950]


def test_execute_raw_sql_invalid_query_rejected_before_db(
    sqlite_engine: Engine,
) -> None:
    """Test non-SELECT destructive statement is rejected by validator before touching database."""
    executor = SQLExecutorService(engine=sqlite_engine)

    with pytest.raises(
        DatabaseException, match="SQL execution blocked by security validator"
    ):
        executor.execute_raw_sql("DELETE FROM customers;")

    # Verify database table contents remain untouched
    with sqlite_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM customers;")).scalar()
        assert count == 5


def test_row_limit_truncation(sqlite_engine: Engine) -> None:
    """Test max_rows limit safely truncates query response row set."""
    executor = SQLExecutorService(engine=sqlite_engine, max_rows=2)
    result = executor.execute_raw_sql("SELECT * FROM customers;")

    assert result.row_count == 2
    assert len(result.rows) == 2


def test_execute_question_complete_pipeline(sqlite_engine: Engine) -> None:
    """Test execute_question handles complete generator -> validator -> executor pipeline."""
    mock_generator = MagicMock()
    mock_generator.generate_sql.return_value = SQLGenerateResponse(
        question="Top two customers by revenue",
        sql="SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 2;",
    )

    executor = SQLExecutorService(engine=sqlite_engine, generator=mock_generator)
    result = executor.execute_question("Top two customers by revenue")

    assert isinstance(result, SQLExecutionResult)
    assert result.question == "Top two customers by revenue"
    assert "SELECT name, revenue FROM customers" in result.sql
    assert result.columns == ["name", "revenue"]
    assert result.row_count == 2
    assert result.rows[0] == ["Eve", 2000]
    assert result.rows[1] == ["Charlie", 1500]
    assert result.execution_duration_ms > 0


def test_execute_question_validation_failure_raises_exception(
    sqlite_engine: Engine,
) -> None:
    """Test execute_question raises DatabaseException if generated SQL fails validator."""
    mock_generator = MagicMock()
    mock_generator.generate_sql.return_value = SQLGenerateResponse(
        question="Drop customers table",
        sql="DROP TABLE customers;",
    )

    executor = SQLExecutorService(engine=sqlite_engine, generator=mock_generator)

    with pytest.raises(
        DatabaseException, match="SQL execution blocked by security validator"
    ):
        executor.execute_question("Drop customers table")


def test_post_database_query_endpoint_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test POST /database/query API endpoint returns 200 OK with structured execution result."""
    mock_execution_result = SQLExecutionResult(
        question="Top customers by revenue",
        sql="SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 2;",
        columns=["name", "revenue"],
        rows=[["Eve", 2000], ["Charlie", 1500]],
        row_count=2,
        execution_duration_ms=12.5,
    )

    monkeypatch.setattr(
        "packages.sql_agent.executor.SQLExecutorService.execute_question",
        lambda self, question: mock_execution_result,
    )

    response = client.post(
        "/database/query",
        json={"question": "Top customers by revenue"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Top customers by revenue"
    assert data["columns"] == ["name", "revenue"]
    assert data["rows"] == [["Eve", 2000], ["Charlie", 1500]]
    assert data["row_count"] == 2
    assert data["execution_duration_ms"] == 12.5


def test_post_database_query_endpoint_invalid_body(client: TestClient) -> None:
    """Test POST /database/query endpoint returns HTTP 422 for invalid request body."""
    response = client.post("/database/query", json={})
    assert response.status_code == 422
