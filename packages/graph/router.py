"""Intent router node placeholder for LangGraph workflow."""

from packages.shared.logging import get_logger

from .state import AgentState

logger = get_logger(__name__)


async def route_intent_node(state: AgentState) -> AgentState:
    """LangGraph node classifying user query intent into RAG or SQL Agent branch.

    TODO (Phase 4):
        - Integrate Gemini structured output prompt to classify intent dynamically.
        - Keywords triggering 'sql': 'revenue', 'sales', 'customers', 'count', 'orders', 'total'.
        - Keywords triggering 'rag': 'documentation', 'policy', 'guide', 'how to', 'summary'.

    Args:
        state: Current AgentState payload.

    Returns:
        AgentState: Updated state with classified intent ('rag' or 'sql').
    """
    query = state.get("query", "").lower()
    logger.info(f"LangGraph Router Node evaluating query (placeholder): '{query}'")

    # Simple heuristic routing placeholder
    sql_keywords = [
        "revenue",
        "sales",
        "order",
        "customer",
        "product",
        "total",
        "count",
    ]
    if any(keyword in query for keyword in sql_keywords):
        intent = "sql"
    else:
        intent = "rag"

    logger.info(f"Router classified intent as: {intent}")
    state["intent"] = intent
    return state
