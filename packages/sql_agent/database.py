"""Database connection engine and session factory management."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.app.core.exceptions import DatabaseException
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class DatabaseManager:
    """SQLAlchemy database connection and engine manager."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url if db_url is not None else settings.postgres_sync_url
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    def get_engine(self) -> Engine:
        """Lazy-initialize SQLAlchemy synchronous Engine instance.

        Returns:
            Engine: Active SQLAlchemy engine.
        """
        if self._engine is None:
            logger.info("Initializing SQLAlchemy database connection engine...")
            try:
                self._engine = create_engine(
                    self.db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                )
            except Exception as exc:
                logger.error(
                    f"Failed to create SQLAlchemy engine: {str(exc)}",
                    exc_info=True,
                )
                raise DatabaseException(
                    message=f"Failed to connect to database: {str(exc)}"
                ) from exc
        return self._engine

    def get_session(self) -> Session:
        """Create a new SQLAlchemy database session instance.

        Returns:
            Session: Active database session.
        """
        if self._session_factory is None:
            engine = self.get_engine()
            self._session_factory = sessionmaker(bind=engine, autoflush=False)
        return self._session_factory()

    def close(self) -> None:
        """Dispose database engine connection pool."""
        if self._engine is not None:
            logger.info("Disposing SQLAlchemy database engine connections...")
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Module-level singleton manager
db_manager = DatabaseManager()


def get_db_engine() -> Engine:
    """Helper function to retrieve singleton database engine."""
    return db_manager.get_engine()


class DatabaseInspector:
    """PostgreSQL Database reflection and schema inspector helper."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url if db_url is not None else settings.postgres_sync_url

    def get_schema_summary(self) -> str:
        """Fetch human-readable database schema description for SQL generation prompts."""
        from packages.sql_agent.schema import SchemaInspectorService

        service = SchemaInspectorService()
        schema = service.get_schema()
        lines = []
        for tbl in schema.tables:
            cols = ", ".join(f"{c.name} {c.type}" for c in tbl.columns)
            lines.append(f"TABLE {tbl.name} ({cols});")
        return "\n".join(lines)
