"""SQL statement validator enforcing read-only SELECT queries with AST parsing."""

import time

import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp

from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)

# List of AST node types strictly prohibited in any part of the query (including CTEs & subqueries)
FORBIDDEN_AST_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Grant,
    exp.Revoke,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
)


class ValidationResult(BaseModel):
    """Result payload representing the outcome of SQL validation."""

    valid: bool = Field(..., description="Whether SQL query is valid and read-only")
    reason: str = Field(
        ..., description="Validation success message or rejection explanation"
    )
    statement_type: str | None = Field(
        default=None,
        description="Detected SQL statement type (e.g. SELECT, DELETE)",
    )


def _extract_statement_type(stmt: exp.Expression, original_sql: str) -> str:
    """Extract a clean, normalized statement type string for the statement."""
    if isinstance(stmt, exp.Select):
        return "SELECT"
    if isinstance(stmt, exp.Insert):
        return "INSERT"
    if isinstance(stmt, exp.Update):
        return "UPDATE"
    if isinstance(stmt, exp.Delete):
        return "DELETE"
    if isinstance(stmt, exp.Drop):
        return "DROP"
    if isinstance(stmt, exp.Alter):
        return "ALTER"
    if isinstance(stmt, exp.Create):
        return "CREATE"
    if isinstance(stmt, exp.TruncateTable):
        return "TRUNCATE"
    if isinstance(stmt, exp.Grant):
        return "GRANT"
    if isinstance(stmt, exp.Revoke):
        return "REVOKE"
    if isinstance(stmt, (exp.Transaction, exp.Commit, exp.Rollback)):
        return "TRANSACTION"

    # Fallback to first word token from original SQL text
    tokens = original_sql.strip().split()
    if tokens:
        first_word = tokens[0].upper().rstrip(";")
        if first_word.isalpha():
            return first_word

    return type(stmt).__name__.upper()


class SQLValidator:
    """Validator enforcing read-only SELECT statements and blocking destructive SQL operations."""

    def __init__(
        self,
        max_sql_length: int | None = None,
        allow_cte_select_only: bool | None = None,
    ) -> None:
        self.max_sql_length = (
            max_sql_length if max_sql_length is not None else settings.SQL_MAX_LENGTH
        )
        self.allow_cte_select_only = (
            allow_cte_select_only
            if allow_cte_select_only is not None
            else settings.SQL_ALLOW_CTE_SELECT_ONLY
        )

    def validate_query(self, sql: str) -> tuple[bool, str]:
        """Validate query and return tuple (is_valid, reason) for backward compatibility."""
        result = self.validate(sql)
        return result.valid, result.reason

    def validate(self, sql: str) -> ValidationResult:
        """Parse and validate SQL query string to ensure read-only SELECT compliance.

        Args:
            sql: SQL statement string.

        Returns:
            ValidationResult: Result object indicating validity, reason, and statement type.
        """
        if not sql or not sql.strip():
            return ValidationResult(
                valid=False,
                reason="SQL query string cannot be empty.",
                statement_type=None,
            )

        clean_sql = sql.strip()
        start_time = time.perf_counter()

        # Step 1: Max length check
        if len(clean_sql) > self.max_sql_length:
            logger.warning(
                f"SQL validation rejected: length ({len(clean_sql)}) exceeds max limit ({self.max_sql_length})"
            )
            return ValidationResult(
                valid=False,
                reason=f"SQL query exceeds maximum character length limit ({len(clean_sql)} > {self.max_sql_length}).",
                statement_type="OVERSIZED",
            )

        # Step 2: AST Parsing
        try:
            statements = [s for s in sqlglot.parse(clean_sql, read="postgres") if s]
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                f"SQL validation rejected due to syntax error in {duration_ms}ms: {str(exc)}"
            )
            return ValidationResult(
                valid=False,
                reason=f"Invalid SQL syntax: {str(exc)}",
                statement_type="SYNTAX_ERROR",
            )

        if not statements:
            return ValidationResult(
                valid=False,
                reason="SQL query could not be parsed into a valid statement.",
                statement_type="EMPTY",
            )

        # Step 3: Multi-statement check
        if len(statements) > 1:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                f"SQL validation rejected: multi-statement query detected ({len(statements)} statements) in {duration_ms}ms"
            )
            return ValidationResult(
                valid=False,
                reason="Multiple SQL statements in a single query are blocked for security.",
                statement_type="MULTI_STATEMENT",
            )

        stmt = statements[0]
        stmt_type = _extract_statement_type(stmt, clean_sql)

        # Step 4: Validate Root Statement is SELECT
        if not isinstance(stmt, exp.Select):
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                f"SQL validation rejected: statement type '{stmt_type}' is not allowed in {duration_ms}ms",
                extra={"statement_type": stmt_type, "valid": False},
            )
            return ValidationResult(
                valid=False,
                reason=f"Disallowed SQL statement type '{stmt_type}'. Only read-only SELECT statements are permitted.",
                statement_type=stmt_type,
            )

        # Step 5: Validate no forbidden child AST nodes exist anywhere in query (e.g. nested in CTEs)
        forbidden_nodes = list(stmt.find_all(FORBIDDEN_AST_NODES))
        if forbidden_nodes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            forbidden_type = type(forbidden_nodes[0]).__name__.upper()
            logger.warning(
                f"SQL validation rejected: nested disallowed AST node '{forbidden_type}' found in query in {duration_ms}ms"
            )
            return ValidationResult(
                valid=False,
                reason=f"Query contains disallowed nested operation '{forbidden_type}'.",
                statement_type=forbidden_type,
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"SQL validation passed: read-only SELECT statement verified in {duration_ms}ms",
            extra={
                "statement_type": stmt_type,
                "valid": True,
                "duration_ms": duration_ms,
            },
        )

        return ValidationResult(
            valid=True,
            reason="Query passed read-only validation.",
            statement_type="SELECT",
        )
