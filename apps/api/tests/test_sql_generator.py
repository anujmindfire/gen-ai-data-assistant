"""Unit tests for SQLGeneratorService and POST /database/generate-sql API endpoint."""

from unittest.mock import MagicMock

import pytest
from apps.api.app.core.exceptions import GeminiAPIException
from fastapi.testclient import TestClient
from packages.sql_agent.generator import SQLGeneratorService, clean_generated_sql
from packages.sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    RelationshipSchema,
    SQLGenerateResponse,
    TableSchema,
)


@pytest.fixture
def mock_schema() -> DatabaseSchema:
    """Fixture providing a mock DatabaseSchema instance."""
    return DatabaseSchema(
        database_name="test_db",
        tables=[
            TableSchema(
                name="customers",
                columns=[
                    ColumnSchema(
                        name="id",
                        type="INTEGER",
                        primary_key=True,
                        nullable=False,
                    ),
                    ColumnSchema(
                        name="name",
                        type="VARCHAR",
                        primary_key=False,
                        nullable=False,
                    ),
                    ColumnSchema(
                        name="email",
                        type="VARCHAR",
                        primary_key=False,
                        nullable=True,
                    ),
                ],
                primary_keys=["id"],
                foreign_keys=[],
            ),
            TableSchema(
                name="orders",
                columns=[
                    ColumnSchema(
                        name="id",
                        type="INTEGER",
                        primary_key=True,
                        nullable=False,
                    ),
                    ColumnSchema(
                        name="customer_id",
                        type="INTEGER",
                        primary_key=False,
                        nullable=False,
                    ),
                    ColumnSchema(
                        name="total_amount",
                        type="NUMERIC",
                        primary_key=False,
                        nullable=False,
                    ),
                ],
                primary_keys=["id"],
                foreign_keys=[
                    RelationshipSchema(
                        from_table="orders",
                        from_column="customer_id",
                        to_table="customers",
                        to_column="id",
                    )
                ],
            ),
        ],
        relationships=[
            RelationshipSchema(
                from_table="orders",
                from_column="customer_id",
                to_table="customers",
                to_column="id",
            )
        ],
        inspected_at="2026-09-25T12:00:00+00:00",
    )


def test_clean_generated_sql_strips_markdown_fences() -> None:
    """Test clean_generated_sql strips markdown ```sql ... ``` code block wrappers."""
    raw1 = "```sql\nSELECT * FROM customers;\n```"
    assert clean_generated_sql(raw1) == "SELECT * FROM customers;"

    raw2 = "```\nSELECT id, name FROM customers;\n```"
    assert clean_generated_sql(raw2) == "SELECT id, name FROM customers;"

    raw3 = "  SELECT name FROM customers WHERE id = 1;  "
    assert clean_generated_sql(raw3) == "SELECT name FROM customers WHERE id = 1;"

    assert clean_generated_sql("") == ""


def test_build_schema_prompt_includes_tables_and_relationships(
    mock_schema: DatabaseSchema,
) -> None:
    """Test schema prompt generation includes table names, columns, and relationships."""
    service = SQLGeneratorService()
    prompt = service.build_schema_prompt(
        "Top 5 customers by total spending", mock_schema
    )

    assert "Database Name: test_db" in prompt
    assert "Table 'customers'" in prompt
    assert "Table 'orders'" in prompt
    assert "orders.customer_id -> customers.id" in prompt
    assert "Top 5 customers by total spending" in prompt
    assert "CRITICAL INSTRUCTIONS" in prompt


def test_generate_sql_simple_query(mock_schema: DatabaseSchema) -> None:
    """Test generate_sql converts simple question to SQL response object."""
    mock_schema_service = MagicMock()
    mock_schema_service.get_schema.return_value = mock_schema

    mock_gemini_client = MagicMock()
    mock_gemini_client.chat.return_value = "SELECT * FROM customers;"

    generator = SQLGeneratorService(
        schema_service=mock_schema_service,
        gemini_client=mock_gemini_client,
    )

    response = generator.generate_sql("List all customers")

    assert isinstance(response, SQLGenerateResponse)
    assert response.question == "List all customers"
    assert response.sql == "SELECT * FROM customers;"
    mock_gemini_client.chat.assert_called_once()


def test_generate_sql_join_and_aggregation_query(
    mock_schema: DatabaseSchema,
) -> None:
    """Test generate_sql handles complex JOIN and aggregation queries with markdown stripping."""
    mock_schema_service = MagicMock()
    mock_schema_service.get_schema.return_value = mock_schema

    mock_gemini_client = MagicMock()
    raw_sql = """```sql
SELECT c.name, SUM(o.total_amount) AS revenue
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.name
ORDER BY revenue DESC
LIMIT 5;
```"""
    mock_gemini_client.chat.return_value = raw_sql

    generator = SQLGeneratorService(
        schema_service=mock_schema_service,
        gemini_client=mock_gemini_client,
    )

    response = generator.generate_sql("Which are the top 5 customers by revenue?")

    expected_sql = """SELECT c.name, SUM(o.total_amount) AS revenue
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.name
ORDER BY revenue DESC
LIMIT 5;"""

    assert response.sql == expected_sql


def test_generate_sql_empty_question_raises_value_error() -> None:
    """Test passing empty or whitespace question raises ValueError."""
    generator = SQLGeneratorService()
    with pytest.raises(ValueError, match="Question string cannot be empty"):
        generator.generate_sql("   ")


def test_generate_sql_gemini_failure_raises_gemini_exception(
    mock_schema: DatabaseSchema,
) -> None:
    """Test Gemini API failure raises GeminiAPIException."""
    mock_schema_service = MagicMock()
    mock_schema_service.get_schema.return_value = mock_schema

    mock_gemini_client = MagicMock()
    mock_gemini_client.chat.side_effect = Exception("API quota exceeded")

    generator = SQLGeneratorService(
        schema_service=mock_schema_service,
        gemini_client=mock_gemini_client,
    )

    with pytest.raises(GeminiAPIException, match="Gemini SQL generation failed"):
        generator.generate_sql("Show all orders")


def test_generate_sql_empty_gemini_response_raises_gemini_exception(
    mock_schema: DatabaseSchema,
) -> None:
    """Test empty LLM response raises GeminiAPIException."""
    mock_schema_service = MagicMock()
    mock_schema_service.get_schema.return_value = mock_schema

    mock_gemini_client = MagicMock()
    mock_gemini_client.chat.return_value = " ```sql\n\n``` "

    generator = SQLGeneratorService(
        schema_service=mock_schema_service,
        gemini_client=mock_gemini_client,
    )

    with pytest.raises(GeminiAPIException, match="Generated SQL response was empty"):
        generator.generate_sql("Show all orders")


def test_post_database_generate_sql_endpoint_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test POST /database/generate-sql API endpoint with mocked SQL generator."""
    mock_response = SQLGenerateResponse(
        question="Top customers by revenue",
        sql="SELECT c.name, SUM(o.total_amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name LIMIT 5;",
    )

    monkeypatch.setattr(
        "packages.sql_agent.generator.SQLGeneratorService.generate_sql",
        lambda self, question: mock_response,
    )

    response = client.post(
        "/database/generate-sql",
        json={"question": "Top customers by revenue"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "Top customers by revenue"
    assert (
        data["sql"]
        == "SELECT c.name, SUM(o.total_amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name LIMIT 5;"
    )


def test_post_database_generate_sql_endpoint_invalid_body(
    client: TestClient,
) -> None:
    """Test POST /database/generate-sql endpoint returns HTTP 422 on invalid request body."""
    response = client.post("/database/generate-sql", json={})
    assert response.status_code == 422
