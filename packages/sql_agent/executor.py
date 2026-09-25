"""Safe SQL query execution service with AST validation enforcement and row limiting."""

import datetime
import decimal
import time
import uuid
from typing import Any

from sqlalchemy import Engine, text

from apps.api.app.core.exceptions import DatabaseException
from packages.shared.logging import get_logger
from packages.shared.settings import settings
from packages.sql_agent.database import get_db_engine
from packages.sql_agent.generator import SQLGeneratorService
from packages.sql_agent.models import (
    SQLExecutionResult,
    SQLQueryResult,
)
from packages.sql_agent.validator import SQLValidator

logger = get_logger(__name__)


def _serialize_cell(val: Any) -> Any:
    """Convert database cell value to JSON-serializable Python types.

    Args:
        val: Any cell object returned from SQLAlchemy.

    Returns:
        JSON-serializable primitive type (int, float, str, bool, None).
    """
    if val is None:
        return None
    if isinstance(val, (int, float, bool, str)):
        return val
    if isinstance(val, (datetime.date, datetime.datetime, datetime.time)):
        return val.isoformat()
    if isinstance(val, (decimal.Decimal, uuid.UUID)):
        return str(val)
    return str(val)


class SQLExecutorService:
    """Service handling safe execution of validated SELECT queries with row limits and structured logging."""

    def __init__(
        self,
        engine: Engine | None = None,
        validator: SQLValidator | None = None,
        generator: SQLGeneratorService | None = None,
        max_rows: int | None = None,
    ) -> None:
        self._engine = engine
        self.validator = validator or SQLValidator()
        self.generator = generator or SQLGeneratorService()
        self.max_rows = max_rows if max_rows is not None else settings.MAX_SQL_ROWS

    def _get_engine(self) -> Engine:
        """Retrieve active SQLAlchemy engine instance."""
        if self._engine is not None:
            return self._engine
        return get_db_engine()

    def execute_raw_sql(self, sql: str) -> SQLQueryResult:
        """Validate and execute a raw SQL query string against PostgreSQL database.

        Args:
            sql: SQL statement string.

        Returns:
            SQLQueryResult: Object containing executed SQL, columns, rows, and row count.

        Raises:
            DatabaseException: If query fails validation or database execution fails.
        """
        if not sql or not sql.strip():
            raise DatabaseException(message="SQL query string cannot be empty.")

        clean_sql = sql.strip()

        # Step 1: Enforce AST Validation
        validation = self.validator.validate(clean_sql)
        if not validation.valid:
            logger.warning(
                f"SQL execution rejected by validator before database touch: {validation.reason}",
                extra={
                    "sql": clean_sql,
                    "statement_type": validation.statement_type,
                    "reason": validation.reason,
                },
            )
            raise DatabaseException(
                message=f"SQL execution blocked by security validator: {validation.reason}"
            )

        engine = self._get_engine()
        start_time = time.perf_counter()

        # Step 2: Execute query via SQLAlchemy connection
        try:
            with engine.connect() as conn:
                result_set = conn.execute(text(clean_sql))
                columns = list(result_set.keys()) if result_set.returns_rows else []
                raw_rows = (
                    result_set.fetchmany(self.max_rows)
                    if result_set.returns_rows
                    else []
                )

            rows = [[_serialize_cell(cell) for cell in row] for row in raw_rows]
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                f"Executed SQL query in {duration_ms}ms: returned {len(rows)} rows.",
                extra={
                    "sql": clean_sql,
                    "columns": columns,
                    "row_count": len(rows),
                    "duration_ms": duration_ms,
                },
            )

            return SQLQueryResult(
                sql=clean_sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
            )

        except DatabaseException:
            raise
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Database query execution failed after {duration_ms}ms: {str(exc)}",
                exc_info=True,
            )
            raise DatabaseException(
                message=f"Database query execution failed: {str(exc)}"
            ) from exc

    def execute_question(self, question: str) -> SQLExecutionResult:
        """Execute full Text-to-SQL pipeline: Generate -> Validate -> Execute.

        Args:
            question: User natural language input question.

        Returns:
            SQLExecutionResult: Complete query result payload with columns, rows, and metadata.

        Raises:
            ValueError: If question string is empty.
            DatabaseException: If validation or execution fails.
        """
        if not question or not question.strip():
            raise ValueError("Question string cannot be empty.")

        clean_question = question.strip()
        start_time = time.perf_counter()

        # Step 1: Generate SQL from question
        gen_response = self.generator.generate_sql(clean_question)
        generated_sql = gen_response.sql

        # Step 2 & 3: Validate and Execute SQL
        query_result = self.execute_raw_sql(generated_sql)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Step 4: Structured Query Log
        logger.info(
            f"Completed Text-to-SQL pipeline for '{clean_question}' in {duration_ms}ms.",
            extra={
                "question": clean_question,
                "sql": generated_sql,
                "validation": "PASSED",
                "row_count": query_result.row_count,
                "duration_ms": duration_ms,
            },
        )

        return SQLExecutionResult(
            question=clean_question,
            sql=generated_sql,
            columns=query_result.columns,
            rows=query_result.rows,
            row_count=query_result.row_count,
            execution_duration_ms=duration_ms,
        )
