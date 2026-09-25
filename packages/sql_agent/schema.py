"""PostgreSQL database dynamic schema inspection and thread-safe caching service."""

import datetime
import threading
import time

from sqlalchemy import Engine, inspect

from apps.api.app.core.exceptions import DatabaseException
from packages.shared.logging import get_logger
from packages.shared.settings import settings
from packages.sql_agent.database import get_db_engine
from packages.sql_agent.models import (
    ColumnSchema,
    DatabaseSchema,
    RelationshipSchema,
    TableSchema,
)

logger = get_logger(__name__)


class SchemaInspectorService:
    """Service utilizing SQLAlchemy reflection API to dynamically discover tables, columns, and foreign keys."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine
        self._cache: DatabaseSchema | None = None
        self._lock = threading.Lock()

    def _get_engine(self) -> Engine:
        """Get SQLAlchemy Engine instance."""
        if self._engine is not None:
            return self._engine
        return get_db_engine()

    def inspect_database(self) -> DatabaseSchema:
        """Perform database inspection and reflect all table DDL specifications and relationships.

        Returns:
            DatabaseSchema: Structured metadata representation of all discovered tables and foreign keys.

        Raises:
            DatabaseException: If inspection fails or database is unreachable.
        """
        engine = self._get_engine()
        start_time = time.perf_counter()
        db_name = settings.POSTGRES_DB

        logger.info(f"Executing database schema inspection on database '{db_name}'...")
        try:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()

            table_schemas: list[TableSchema] = []
            all_relationships: list[RelationshipSchema] = []

            for table_name in table_names:
                # 1. Fetch Primary Keys
                try:
                    pk_info = inspector.get_pk_constraint(table_name)
                    pk_cols = set(pk_info.get("constrained_columns", []))
                except Exception:
                    pk_cols = set()

                # 2. Fetch Columns
                raw_columns = inspector.get_columns(table_name)
                column_schemas: list[ColumnSchema] = []

                for col in raw_columns:
                    col_name = str(col.get("name", ""))
                    col_type = str(col.get("type", "UNKNOWN"))
                    is_nullable = bool(col.get("nullable", True))
                    default_val = (
                        str(col.get("default"))
                        if col.get("default") is not None
                        else None
                    )
                    is_pk = col_name in pk_cols

                    column_schemas.append(
                        ColumnSchema(
                            name=col_name,
                            type=col_type,
                            nullable=is_nullable,
                            primary_key=is_pk,
                            default=default_val,
                        )
                    )

                # 3. Fetch Foreign Keys and Relationships
                raw_fks = inspector.get_foreign_keys(table_name)
                table_relationships: list[RelationshipSchema] = []

                for fk in raw_fks:
                    from_cols = fk.get("constrained_columns", [])
                    to_table = str(fk.get("referred_table", ""))
                    to_cols = fk.get("referred_columns", [])
                    constraint_name = fk.get("name")

                    for fc, tc in zip(from_cols, to_cols, strict=False):
                        rel = RelationshipSchema(
                            from_table=table_name,
                            from_column=str(fc),
                            to_table=to_table,
                            to_column=str(tc),
                            constraint_name=str(constraint_name)
                            if constraint_name
                            else None,
                        )
                        table_relationships.append(rel)
                        all_relationships.append(rel)

                table_schemas.append(
                    TableSchema(
                        name=table_name,
                        columns=column_schemas,
                        primary_keys=list(pk_cols),
                        foreign_keys=table_relationships,
                    )
                )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"Database schema inspection complete in {duration_ms}ms: "
                f"discovered {len(table_schemas)} tables, {len(all_relationships)} relationships.",
                extra={
                    "database_name": db_name,
                    "table_count": len(table_schemas),
                    "relationship_count": len(all_relationships),
                    "duration_ms": duration_ms,
                },
            )

            return DatabaseSchema(
                database_name=db_name,
                tables=table_schemas,
                relationships=all_relationships,
                inspected_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Database schema inspection failed after {duration_ms}ms: {str(exc)}",
                exc_info=True,
            )
            raise DatabaseException(
                message=f"Database schema inspection failed: {str(exc)}"
            ) from exc

    def get_schema(self, force_refresh: bool = False) -> DatabaseSchema:
        """Retrieve database schema with thread-safe in-memory caching.

        Args:
            force_refresh: If True, bypass cache and re-inspect database.

        Returns:
            DatabaseSchema: Full database schema metadata.
        """
        if self._cache is not None and not force_refresh:
            logger.info("Retrieved database schema metadata from in-memory cache.")
            return self._cache

        with self._lock:
            if self._cache is not None and not force_refresh:
                return self._cache

            if force_refresh:
                logger.info(
                    "Force refresh requested. Refreshing database schema cache..."
                )

            self._cache = self.inspect_database()
            return self._cache

    def refresh_schema(self) -> DatabaseSchema:
        """Manually invalidate cache and trigger fresh database schema inspection."""
        return self.get_schema(force_refresh=True)


# Module-level singleton service instance
schema_service = SchemaInspectorService()
