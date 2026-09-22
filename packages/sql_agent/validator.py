"""SQL query validator placeholder for security checks and query safety enforcement."""

from typing import Tuple
from packages.shared.logging import get_logger

logger = get_logger(__name__)


class SQLValidator:
    """SQL Safety and AST Validator service.

    TODO (Phase 3):
        - Integrate sqlglot parsing to enforce strictly SELECT queries.
        - Block mutating operations (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE).
        - Enforce statement limit caps (e.g. LIMIT 100) to prevent memory exhaust DB queries.
    """

    @staticmethod
    def validate_query(sql_query: str) -> Tuple[bool, str]:
        """Validate whether an LLM-generated SQL query is safe to execute.

        Args:
            sql_query: SQL statement string.

        Returns:
            Tuple[bool, str]: (is_valid, error_reason_if_any)
        """
        cleaned_query = sql_query.strip().upper()

        forbidden_keywords = [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
        ]

        for keyword in forbidden_keywords:
            if f" {keyword} " in f" {cleaned_query} ":
                logger.warning(
                    f"SQL validation failed: contains forbidden keyword '{keyword}'"
                )
                return False, f"Forbidden keyword detected: {keyword}"

        if not cleaned_query.startswith("SELECT") and not cleaned_query.startswith(
            "WITH"
        ):
            logger.warning(
                "SQL validation failed: query does not start with SELECT or WITH"
            )
            return False, "Query must be a read-only SELECT or WITH statement"

        logger.info("SQL query validation passed (placeholder)")
        return True, ""
