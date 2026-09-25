"""Unit tests for SQL database schema introspection service and API endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from packages.sql_agent.models import DatabaseSchema, TableSchema
from packages.sql_agent.schema import SchemaInspectorService
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Define test schema tables
customers_table = Table(
    "customers",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("email", String(100), nullable=True),
)

orders_table = Table(
    "orders",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("total_amount", Numeric(10, 2), nullable=False),
)


@pytest.fixture
def sqlite_test_engine():
    """Create in-memory SQLite database engine initialized with test tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_schema_inspection_tables_and_columns(sqlite_test_engine) -> None:
    """Test dynamic database schema inspection reflects tables, columns, and primary keys."""
    service = SchemaInspectorService(engine=sqlite_test_engine)
    schema = service.inspect_database()

    assert isinstance(schema, DatabaseSchema)
    table_names = [t.name for t in schema.tables]
    assert "customers" in table_names
    assert "orders" in table_names

    # Inspect customers table
    customers_schema = next(t for t in schema.tables if t.name == "customers")
    assert isinstance(customers_schema, TableSchema)
    assert "id" in customers_schema.primary_keys

    col_names = [c.name for c in customers_schema.columns]
    assert "id" in col_names
    assert "name" in col_names
    assert "email" in col_names

    name_col = next(c for c in customers_schema.columns if c.name == "name")
    assert name_col.nullable is False


def test_schema_relationship_discovery(sqlite_test_engine) -> None:
    """Test relationship discovery automatically detects foreign key connections."""
    service = SchemaInspectorService(engine=sqlite_test_engine)
    schema = service.inspect_database()

    assert len(schema.relationships) == 1
    rel = schema.relationships[0]

    assert rel.from_table == "orders"
    assert rel.from_column == "customer_id"
    assert rel.to_table == "customers"
    assert rel.to_column == "id"


def test_schema_caching_and_force_refresh(sqlite_test_engine) -> None:
    """Test thread-safe in-memory caching and force_refresh cache invalidation."""
    service = SchemaInspectorService(engine=sqlite_test_engine)

    # Initial inspection Populates cache
    s1 = service.get_schema()
    # Second call returns cached instance
    s2 = service.get_schema()
    assert s1 is s2

    # Force refresh creates new inspection instance
    s3 = service.get_schema(force_refresh=True)
    assert s3 is not s1
    assert s3.tables[0].name == s1.tables[0].name


def test_get_database_schema_api_endpoint(client: TestClient) -> None:
    """Test GET /database/schema endpoint returns HTTP 200 OK with database schema JSON."""
    mock_db_schema = DatabaseSchema(
        database_name="assistant",
        tables=[
            TableSchema(
                name="users",
                columns=[],
                primary_keys=["id"],
                foreign_keys=[],
            )
        ],
        relationships=[],
        inspected_at="2026-09-25T12:00:00Z",
    )

    with patch(
        "packages.sql_agent.schema.SchemaInspectorService.get_schema",
        return_value=mock_db_schema,
    ):
        response = client.get("/database/schema")

        assert response.status_code == 200
        data = response.json()
        assert data["database_name"] == "assistant"
        assert len(data["tables"]) == 1
        assert data["tables"][0]["name"] == "users"
