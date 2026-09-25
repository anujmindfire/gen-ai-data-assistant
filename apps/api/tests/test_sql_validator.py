"""Unit tests for SQLValidator service and POST /database/validate-sql API endpoint."""

import pytest
from fastapi.testclient import TestClient
from packages.sql_agent.validator import SQLValidator, ValidationResult


@pytest.mark.parametrize(
    "sql_query",
    [
        "SELECT * FROM customers;",
        "SELECT id, name, email FROM customers WHERE country = 'USA';",
        "SELECT c.name, SUM(o.total_amount) AS revenue FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name ORDER BY revenue DESC;",
        "WITH top_spenders AS (SELECT customer_id, SUM(total_amount) AS total FROM orders GROUP BY customer_id HAVING SUM(total_amount) > 1000) SELECT c.name, ts.total FROM top_spenders ts JOIN customers c ON ts.customer_id = c.id;",
        "SELECT COUNT(*) FROM products WHERE category IN ('Electronics', 'Books');",
    ],
)
def test_valid_select_queries_pass_validation(sql_query: str) -> None:
    """Test read-only SELECT queries (including JOINs, aggregations, and CTEs) pass validation."""
    validator = SQLValidator()
    result = validator.validate(sql_query)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.statement_type == "SELECT"
    assert "passed read-only validation" in result.reason


@pytest.mark.parametrize(
    ("sql_query", "expected_type"),
    [
        ("DELETE FROM customers;", "DELETE"),
        ("DELETE FROM orders WHERE total_amount = 0;", "DELETE"),
        (
            "INSERT INTO customers (name, email) VALUES ('Alice', 'alice@example.com');",
            "INSERT",
        ),
        ("UPDATE customers SET name = 'Bob' WHERE id = 1;", "UPDATE"),
        ("DROP TABLE customers;", "DROP"),
        ("ALTER TABLE customers ADD COLUMN phone VARCHAR(20);", "ALTER"),
        ("CREATE TABLE temp_data (id INT);", "CREATE"),
        ("TRUNCATE TABLE orders;", "TRUNCATE"),
        ("GRANT ALL ON customers TO public;", "GRANT"),
        ("REVOKE ALL ON customers FROM public;", "REVOKE"),
        ("EXECUTE run_analytics_job();", "EXECUTE"),
        ("CALL execute_cleanup_procedure();", "CALL"),
    ],
)
def test_invalid_destructive_statements_are_rejected(
    sql_query: str, expected_type: str
) -> None:
    """Test non-SELECT destructive SQL statements are rejected by validator."""
    validator = SQLValidator()
    result = validator.validate(sql_query)

    assert result.valid is False
    assert result.statement_type == expected_type
    assert "Disallowed SQL statement type" in result.reason


def test_multi_statement_queries_are_blocked() -> None:
    """Test semicolon-separated multi-statement SQL queries are rejected."""
    validator = SQLValidator()
    multi_sql = "SELECT * FROM customers; DELETE FROM customers;"
    result = validator.validate(multi_sql)

    assert result.valid is False
    assert result.statement_type == "MULTI_STATEMENT"
    assert "Multiple SQL statements" in result.reason


def test_empty_and_whitespace_sql_validation() -> None:
    """Test empty or whitespace-only SQL queries return invalid result."""
    validator = SQLValidator()

    res1 = validator.validate("")
    assert res1.valid is False
    assert res1.statement_type is None

    res2 = validator.validate("   \n\t ")
    assert res2.valid is False
    assert res2.statement_type is None


def test_oversized_sql_validation() -> None:
    """Test SQL query exceeding MAX_SQL_LENGTH character budget is rejected."""
    validator = SQLValidator(max_sql_length=100)
    oversized_sql = "SELECT * FROM customers WHERE " + " OR ".join(
        [f"id = {i}" for i in range(50)]
    )

    result = validator.validate(oversized_sql)
    assert result.valid is False
    assert result.statement_type == "OVERSIZED"
    assert "exceeds maximum character length" in result.reason


def test_invalid_sql_syntax_returns_syntax_error() -> None:
    """Test malformed SQL syntax returns SYNTAX_ERROR validation result."""
    validator = SQLValidator()
    invalid_sql = "SELECT FROM WHERE GROUP HAVING ORDER BY;"
    result = validator.validate(invalid_sql)

    assert result.valid is False
    assert result.statement_type == "SYNTAX_ERROR"
    assert "Invalid SQL syntax" in result.reason


def test_post_database_validate_sql_endpoint_valid(client: TestClient) -> None:
    """Test POST /database/validate-sql debugging endpoint with valid SELECT query."""
    response = client.post(
        "/database/validate-sql",
        json={"sql": "SELECT * FROM customers;"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["statement_type"] == "SELECT"


def test_post_database_validate_sql_endpoint_invalid(
    client: TestClient,
) -> None:
    """Test POST /database/validate-sql debugging endpoint with destructive query."""
    response = client.post(
        "/database/validate-sql",
        json={"sql": "DROP TABLE customers;"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["statement_type"] == "DROP"
    assert "Disallowed SQL statement type" in data["reason"]


def test_post_database_validate_sql_endpoint_empty_body(
    client: TestClient,
) -> None:
    """Test POST /database/validate-sql with empty request body returns HTTP 422."""
    response = client.post("/database/validate-sql", json={})
    assert response.status_code == 422
