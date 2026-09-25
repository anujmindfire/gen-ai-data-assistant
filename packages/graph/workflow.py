"""LangGraph workflow definition specifying nodes and conditional edges.

Nodes:
    - router: Classifies user prompt into RAG, SQL, or Combined route
    - rag: Executes RAGService document context retrieval
    - sql: Executes SQLExecutorService database query pipeline
    - combined: Executes both RAG and SQL pipelines, fusing responses with Gemini
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from packages.shared.logging import get_logger

from .nodes import combined_node, rag_node, sql_node
from .router import route_intent_node
from .state import AgentState

logger = get_logger(__name__)


# --- Conditional Routing Decision ---


def select_next_node(state: AgentState) -> Literal["rag", "sql", "combined"]:
    """Conditional edge decision function directing traffic based on classified route.

    Args:
        state: AgentState payload containing classified route/intent.

    Returns:
        Literal["rag", "sql", "combined"]: Target node name.
    """
    route = (state.get("route") or state.get("intent") or "rag").lower().strip()
    if route in ("rag", "sql", "combined"):
        return route  # type: ignore[return-value]
    return "rag"


# --- Workflow Graph Builder ---


def create_workflow_graph() -> StateGraph:
    """Construct and compile the complete LangGraph StateGraph workflow.

    Returns:
        Compiled LangGraph runnable graph instance.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("router", route_intent_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("combined", combined_node)

    # Define Graph Entry Point
    workflow.set_entry_point("router")

    # Conditional Branching from Router
    workflow.add_conditional_edges(
        "router",
        select_next_node,
        {
            "rag": "rag",
            "sql": "sql",
            "combined": "combined",
        },
    )

    # Terminal Transitions to END
    workflow.add_edge("rag", END)
    workflow.add_edge("sql", END)
    workflow.add_edge("combined", END)

    logger.info("Successfully constructed LangGraph StateGraph workflow graph.")
    return workflow.compile()


# Module-level compiled workflow graph application
graph_app = create_workflow_graph()
