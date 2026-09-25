"""Database schema inspection route handler for GET /database/schema."""

from fastapi import APIRouter, Query, status
from packages.sql_agent.executor import SQLExecutorService
from packages.sql_agent.generator import SQLGeneratorService
from packages.sql_agent.models import (
    DatabaseSchema,
    SQLExecuteRequest,
    SQLExecutionResult,
    SQLGenerateRequest,
    SQLGenerateResponse,
)
from packages.sql_agent.schema import SchemaInspectorService
from packages.sql_agent.validator import SQLValidator, ValidationResult
from pydantic import BaseModel, Field

router = APIRouter(prefix="/database", tags=["Database"])


class SQLValidateRequest(BaseModel):
    """Request payload for POST /database/validate-sql debugging endpoint."""

    sql: str = Field(
        ..., min_length=1, description="SQL query statement string to validate"
    )


@router.get(
    "/schema",
    response_model=DatabaseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Database Schema Metadata",
    description="Reflects PostgreSQL database tables, columns, primary keys, and foreign key relationships.",
)
async def get_database_schema(
    force_refresh: bool = Query(
        default=False,
        description="Force refresh to bypass in-memory schema cache",
    ),
) -> DatabaseSchema:
    """Return database schema metadata with dynamic introspection."""
    service = SchemaInspectorService()
    return service.get_schema(force_refresh=force_refresh)


@router.post(
    "/validate-sql",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate SQL Query Safety",
    description="Parses and validates input SQL statement for read-only SELECT compliance without executing it.",
)
async def validate_sql_query(
    payload: SQLValidateRequest,
) -> ValidationResult:
    """Validate SQL statement string against read-only security rules."""
    validator = SQLValidator()
    return validator.validate(sql=payload.sql)


@router.post(
    "/generate-sql",
    response_model=SQLGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Read-Only SQL from Natural Language",
    description="Converts natural language question into PostgreSQL SELECT statement using Gemini & database schema.",
)
async def generate_sql_from_question(
    payload: SQLGenerateRequest,
) -> SQLGenerateResponse:
    """Generate SQL statement from natural language question without executing it."""
    generator = SQLGeneratorService()
    return generator.generate_sql(question=payload.question)


@router.post(
    "/query",
    response_model=SQLExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Generate, Validate, and Execute SQL Query",
    description="Full Text-to-SQL execution pipeline: converts natural language question to SQL, validates read-only AST compliance, executes against PostgreSQL, and returns structured result rows.",
)
async def execute_natural_language_query(
    payload: SQLExecuteRequest,
) -> SQLExecutionResult:
    """Execute complete Text-to-SQL pipeline for a natural language user question."""
    executor = SQLExecutorService()
    return executor.execute_question(question=payload.question)
