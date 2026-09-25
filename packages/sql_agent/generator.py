"""SQL query generator converting natural language questions to read-only SQL using Gemini."""

import re
import time

from apps.api.app.core.exceptions import GeminiAPIException
from packages.shared.gemini import GeminiClient
from packages.shared.logging import get_logger
from packages.sql_agent.models import (
    DatabaseSchema,
    SQLGenerateResponse,
)
from packages.sql_agent.schema import SchemaInspectorService

logger = get_logger(__name__)


def clean_generated_sql(raw_sql: str) -> str:
    """Clean markdown code blocks, backticks, and extra whitespace from generated SQL string.

    Args:
        raw_sql: Raw text output returned from Gemini LLM.

    Returns:
        str: Cleaned, raw SQL query string.
    """
    if not raw_sql:
        return ""

    cleaned = raw_sql.strip()

    # Remove markdown code block fences like ```sql ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    return cleaned


class SQLGeneratorService:
    """Service handling schema-aware natural language to SQL generation via Gemini."""

    def __init__(
        self,
        schema_service: SchemaInspectorService | None = None,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.schema_service = schema_service or SchemaInspectorService()
        self.gemini_client = gemini_client or GeminiClient()

    def build_schema_prompt(self, question: str, schema: DatabaseSchema) -> str:
        """Construct schema-aware prompt for Gemini LLM including table DDL and FK relationships.

        Args:
            question: User natural language input question.
            schema: DatabaseSchema metadata object.

        Returns:
            str: Complete prompt string formatted for Gemini.
        """
        schema_lines: list[str] = [f"Database Name: {schema.database_name}", ""]
        schema_lines.append("Tables:")

        for table in schema.tables:
            col_specs = []
            for col in table.columns:
                spec = f"{col.name} ({col.type}"
                if col.primary_key:
                    spec += ", PRIMARY KEY"
                if not col.nullable:
                    spec += ", NOT NULL"
                spec += ")"
                col_specs.append(spec)

            cols_str = ", ".join(col_specs)
            schema_lines.append(f"  - Table '{table.name}': [{cols_str}]")

        if schema.relationships:
            schema_lines.append("\nForeign Key Relationships:")
            for rel in schema.relationships:
                schema_lines.append(
                    f"  - {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}"
                )

        formatted_schema = "\n".join(schema_lines)

        prompt = f"""You are an expert PostgreSQL data assistant.
Your task is to convert the user's natural language question into a valid, read-only PostgreSQL SQL query.

DATABASE SCHEMA:
{formatted_schema}

QUESTION:
{question}

CRITICAL INSTRUCTIONS:
- Generate ONLY a single valid read-only SQL query (SELECT statement or WITH CTE that produces SELECT).
- Use ONLY tables and columns explicitly listed in the schema above. NEVER invent table names or column names.
- NEVER generate destructive SQL operations (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, EXECUTE, CALL).
- Do NOT include any conversational preamble, explanations, or markdown code block formatting (do NOT use ```sql or ```).
- Output raw, executable SQL text ONLY.
"""
        return prompt

    def generate_sql(
        self, question: str, force_schema_refresh: bool = False
    ) -> SQLGenerateResponse:
        """Convert natural language question into a structured SQL generation response.

        Args:
            question: User natural language question string.
            force_schema_refresh: Whether to force refresh in-memory database schema cache.

        Returns:
            SQLGenerateResponse: Object containing question and generated SQL query string.

        Raises:
            ValueError: If question string is empty.
            LLMException: If Gemini API generation fails or returns empty result.
        """
        if not question or not question.strip():
            raise ValueError("Question string cannot be empty.")

        clean_question = question.strip()
        start_time = time.perf_counter()

        logger.info(
            f"Generating SQL for question: '{clean_question}'...",
            extra={"question": clean_question},
        )

        # Step 1: Retrieve schema metadata
        schema = self.schema_service.get_schema(force_refresh=force_schema_refresh)
        if not schema or not schema.tables:
            logger.error("Database schema contains no tables for SQL generation.")
            raise GeminiAPIException(
                message="Database schema metadata is unavailable or empty."
            )

        # Step 2: Build prompt
        prompt = self.build_schema_prompt(clean_question, schema)

        # Step 3: Call Gemini LLM
        try:
            raw_response = self.gemini_client.chat(prompt)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"SQL generation failed via Gemini after {duration_ms}ms: {str(exc)}",
                exc_info=True,
            )
            raise GeminiAPIException(
                message=f"Gemini SQL generation failed: {str(exc)}"
            ) from exc

        # Step 4: Clean response
        sql_query = clean_generated_sql(raw_response)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not sql_query:
            logger.error("Gemini returned empty or whitespace SQL response.")
            raise GeminiAPIException(message="Generated SQL response was empty.")

        logger.info(
            f"SQL generation completed successfully in {duration_ms}ms.",
            extra={
                "question": clean_question,
                "generated_sql_len": len(sql_query),
                "duration_ms": duration_ms,
            },
        )

        return SQLGenerateResponse(question=clean_question, sql=sql_query)
