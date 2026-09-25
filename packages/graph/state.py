"""Typed state definition for LangGraph state graph transitions."""

from typing import Any

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """Strongly typed state dictionary passed across LangGraph nodes.

    Attributes:
        question: User natural language input prompt string.
        route: Classified routing branch ('rag', 'sql', or 'combined').
        retrieved_docs: Document context payloads retrieved from Qdrant.
        rag_answer: Answer text generated from retrieved document context.
        sql_query: Generated SQL statement string.
        sql_result: DB query execution results dictionary (columns, rows, row_count).
        final_answer: Final answer output produced by graph workflow.
        sources: Citation source objects list.
        errors: Error messages list captured during graph execution.
    """

    question: str
    query: str  # Alias for backward compatibility
    route: str | None
    intent: str | None  # Alias for backward compatibility
    retrieved_docs: list[dict[str, Any]]
    rag_answer: str | None
    sql_query: str | None
    sql_result: dict[str, Any] | None
    final_answer: str | None
    sources: list[dict[str, Any]]
    errors: list[str]
