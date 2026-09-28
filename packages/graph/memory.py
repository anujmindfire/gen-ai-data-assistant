"""In-memory session-based conversation memory manager for LangGraph state persistence."""

import datetime
import threading
import uuid
from typing import Any

from pydantic import BaseModel, Field

from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class ConversationMessage(BaseModel):
    """Single message entry in a conversation session."""

    role: str = Field(..., description="Message author role ('user' or 'assistant')")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(..., description="ISO 8601 timestamp string")
    route: str | None = Field(default=None, description="Optional routing decision")
    sources: list[dict[str, Any]] = Field(
        default_factory=list, description="Optional citation sources"
    )
    sql: str | None = Field(default=None, description="Optional executed SQL statement")


class SessionData(BaseModel):
    """Session state payload storing history, metadata, and previous context."""

    session_id: str = Field(..., description="Unique session identifier string")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last updated timestamp")
    history: list[ConversationMessage] = Field(
        default_factory=list, description="Array of historical conversation messages"
    )
    previous_route: str | None = Field(
        default=None, description="Most recent route used in session"
    )
    previous_sources: list[dict[str, Any]] = Field(
        default_factory=list, description="Most recent document citation sources"
    )
    previous_sql: str | None = Field(
        default=None, description="Most recent SQL statement executed in session"
    )


class ConversationMemoryManager:
    """Thread-safe in-memory session manager handling message history, context tracking, and auto-trimming."""

    def __init__(self, max_messages: int | None = None) -> None:
        self.max_messages = (
            max_messages
            if max_messages is not None
            else settings.MAX_CONVERSATION_MESSAGES
        )
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str | None = None) -> SessionData:
        """Create a new conversation session.

        Args:
            session_id: Optional custom session ID string.

        Returns:
            SessionData: Initialized session payload.
        """
        sid = (
            session_id.strip()
            if session_id and session_id.strip()
            else uuid.uuid4().hex[:12]
        )
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()

        with self._lock:
            session = SessionData(
                session_id=sid,
                created_at=now_iso,
                updated_at=now_iso,
                history=[],
            )
            self._sessions[sid] = session
            logger.info(f"Created new conversation session: '{sid}'")
            return session

    def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve existing session data by ID.

        Args:
            session_id: Target session ID string.

        Returns:
            SessionData | None: Session object if found, None otherwise.
        """
        if not session_id or not session_id.strip():
            return None
        with self._lock:
            return self._sessions.get(session_id.strip())

    def get_or_create_session(self, session_id: str | None = None) -> SessionData:
        """Retrieve existing session or create a new session if not found.

        Args:
            session_id: Optional session ID string.

        Returns:
            SessionData: Active session object.
        """
        if session_id and session_id.strip():
            existing = self.get_session(session_id.strip())
            if existing is not None:
                logger.info(f"Reusing existing conversation session: '{session_id}'")
                return existing
        return self.create_session(session_id=session_id)

    def trim_history(self, session_id: str) -> None:
        """Trim oldest messages when session history exceeds max_messages.

        Args:
            session_id: Target session ID string.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return

            history_len = len(session.history)
            if history_len > self.max_messages:
                excess = history_len - self.max_messages
                logger.info(
                    f"Trimming conversation memory for session '{session_id}': "
                    f"dropping {excess} oldest messages ({history_len} -> {self.max_messages})"
                )
                session.history = session.history[excess:]
                session.updated_at = datetime.datetime.now(datetime.UTC).isoformat()

    def add_interaction(
        self,
        session_id: str,
        question: str,
        response: str,
        route: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        sql: str | None = None,
    ) -> SessionData:
        """Append user question and assistant response pair to session memory.

        Args:
            session_id: Active session ID.
            question: User question message.
            response: Assistant response answer text.
            route: Optional route branch used ('rag', 'sql', 'combined').
            sources: Optional document source citations.
            sql: Optional executed SQL statement string.

        Returns:
            SessionData: Updated session object.
        """
        session = self.get_or_create_session(session_id)
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        src_list = sources or []

        user_msg = ConversationMessage(
            role="user",
            content=question.strip(),
            timestamp=now_iso,
        )
        assistant_msg = ConversationMessage(
            role="assistant",
            content=response.strip(),
            timestamp=now_iso,
            route=route,
            sources=src_list,
            sql=sql,
        )

        with self._lock:
            session.history.append(user_msg)
            session.history.append(assistant_msg)
            session.updated_at = now_iso
            if route:
                session.previous_route = route
            if src_list:
                session.previous_sources = src_list
            if sql:
                session.previous_sql = sql

        self.trim_history(session.session_id)

        logger.info(
            f"Added interaction to session '{session.session_id}': "
            f"history size now {len(session.history)} messages."
        )
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete session from memory.

        Args:
            session_id: Target session ID string.

        Returns:
            bool: True if deleted, False if not found.
        """
        if not session_id or not session_id.strip():
            return False
        sid = session_id.strip()
        with self._lock:
            if sid in self._sessions:
                del self._sessions[sid]
                logger.info(f"Deleted conversation session: '{sid}'")
                return True
            return False

    def clear_all(self) -> None:
        """Clear all session data from memory."""
        with self._lock:
            self._sessions.clear()
            logger.info("Cleared all conversation sessions from memory.")


# Module-level singleton instance
memory_manager = ConversationMemoryManager()
