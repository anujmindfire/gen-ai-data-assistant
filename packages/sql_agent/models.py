"""Pydantic schemas for SQL database reflection and schema metadata."""

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema metadata definition for a single database column."""

    name: str = Field(..., description="Column name")
    type: str = Field(
        ..., description="Data type representation (e.g. INTEGER, VARCHAR)"
    )
    nullable: bool = Field(
        default=True, description="Whether column permits NULL values"
    )
    primary_key: bool = Field(
        default=False, description="Whether column is part of primary key"
    )
    default: str | None = Field(default=None, description="Default value or expression")


class RelationshipSchema(BaseModel):
    """Foreign key relationship metadata connecting two database tables."""

    from_table: str = Field(..., description="Source table name containing foreign key")
    from_column: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Referenced target table name")
    to_column: str = Field(..., description="Referenced target column name")
    constraint_name: str | None = Field(
        default=None, description="Foreign key constraint identifier"
    )


class TableSchema(BaseModel):
    """Schema metadata representation for a single database table."""

    name: str = Field(..., description="Table name")
    columns: list[ColumnSchema] = Field(
        default_factory=list, description="List of table columns"
    )
    primary_keys: list[str] = Field(
        default_factory=list, description="List of primary key column names"
    )
    foreign_keys: list[RelationshipSchema] = Field(
        default_factory=list,
        description="List of outgoing foreign key constraints",
    )


class DatabaseSchema(BaseModel):
    """Complete database schema representation including tables and relationships."""

    database_name: str = Field(..., description="Target database identifier/name")
    tables: list[TableSchema] = Field(
        default_factory=list, description="Array of database table schemas"
    )
    relationships: list[RelationshipSchema] = Field(
        default_factory=list,
        description="Array of detected foreign key relationships",
    )
    inspected_at: str = Field(
        ..., description="ISO 8601 timestamp of schema inspection"
    )


class SQLGenerateRequest(BaseModel):
    """Request payload for SQL generation from natural language question."""

    question: str = Field(
        ...,
        min_length=1,
        description="Natural language question to convert into SQL",
    )


class SQLGenerateResponse(BaseModel):
    """Structured response payload containing question and generated SQL statement."""

    question: str = Field(..., description="Original user natural language question")
    sql: str = Field(..., description="Generated PostgreSQL query statement")


class SQLExecuteRequest(BaseModel):
    """Request payload for executing SQL pipeline from natural language question."""

    question: str = Field(
        ...,
        min_length=1,
        description="Natural language question to generate, validate, and execute",
    )


class SQLQueryResult(BaseModel):
    """Structured result of executing a raw SQL query."""

    sql: str = Field(..., description="Executed SQL query statement")
    columns: list[str] = Field(
        default_factory=list, description="Array of column names returned by query"
    )
    rows: list[list[object]] = Field(
        default_factory=list, description="Array of data rows"
    )
    row_count: int = Field(default=0, description="Total number of returned rows")


class SQLExecutionResult(BaseModel):
    """Structured response payload containing query results for a user question."""

    question: str = Field(..., description="Original user natural language question")
    sql: str = Field(..., description="Generated and executed SQL statement")
    columns: list[str] = Field(
        default_factory=list, description="Array of column names returned by query"
    )
    rows: list[list[object]] = Field(
        default_factory=list, description="Array of data rows"
    )
    row_count: int = Field(default=0, description="Total number of returned rows")
    execution_duration_ms: float = Field(
        default=0.0, description="Total pipeline execution duration in milliseconds"
    )
