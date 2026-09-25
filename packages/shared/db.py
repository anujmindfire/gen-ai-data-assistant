"""Database connection and SQLAlchemy ORM models."""

import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DocumentModel(Base):
    """SQLAlchemy model for documents table in PostgreSQL."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(512), nullable=False)
    size = Column(BigInteger, nullable=False)
    pages = Column(Integer, nullable=False, default=1)
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    def to_dict(self) -> dict[str, str]:
        """Convert ORM model attributes to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "type": self.file_type,
            "file_path": self.file_path,
            "size": self.size,
            "pages": self.pages,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else "",
        }


# In-memory document repository fallback for environment without live Postgres
class InMemoryDocumentRepository:
    """Fallback repository for managing document metadata in memory."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    def add(self, doc_data: dict[str, str]) -> None:
        self._store[doc_data["id"]] = doc_data

    def get(self, doc_id: str) -> dict[str, str] | None:
        return self._store.get(doc_id)

    def list_all(self) -> list[dict[str, str]]:
        return list(self._store.values())

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._store:
            del self._store[doc_id]
            return True
        return False


# Shared repository singleton for fast local file persistence
doc_repository = InMemoryDocumentRepository()
