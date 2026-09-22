"""LangGraph workflow definition specifying nodes and conditional edges.

Nodes:
    - router: Classifies user prompt into RAG vs SQL agent
    - rag: Retrieves context documents from Qdrant
    - sql: Generates and executes database queries on PostgreSQL
    - combine: Merges context into prompt context for Gemini
    - respond: Generates final response using Google Gemini API
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from packages.shared.logging import get_logger
from .state import AgentState
from .router import route_intent_node

logger = get_logger(__name__)


# --- Node Definitions ---

async def rag_node(state: AgentState) -> AgentState:
    """RAG retrieval node skeleton.

    TODO (Phase 2): Integrate VectorRetriever to fetch relevant doc embeddings from Qdrant.
    """
    logger.info("Executing LangGraph Node: [rag]")
    state["retrieved_docs"] = [
        {"content": "Placeholder retrieved context for document query.", "score": 0.9}
    ]
    return state


async def sql_node(state: AgentState) -> AgentState:
    """SQL Agent execution node skeleton.

    TODO (Phase 3): Integrate SQLAgent to generate, validate, and run SQL queries against PostgreSQL.
    """
    logger.info("Executing LangGraph Node: [sql]")
    state["sql_query"] = "SELECT SUM(total_amount) FROM orders;"
    state["sql_result"] = [{"sum": 45000.00}]
    return state


async def combine_node(state: AgentState) -> AgentState:
    """Combine node synthesizing structured DB output or RAG docs into LLM prompt context.

    TODO (Phase 4): Synthesize formatted prompt payload for final LLM generation step.
    """
    logger.info("Executing LangGraph Node: [combine]")
    return state


async def respond_node(state: AgentState) -> AgentState:
    """Respond node producing final output response via Google Gemini API.

    TODO (Phase 4): Invoke ChatGoogleGenerativeAI client with combined context.
    """
    logger.info("Executing LangGraph Node: [respond]")
    intent = state.get("intent", "unknown")
    if intent == "sql":
        state["final_response"] = (
            f"Based on database analytics (Query: {state.get('sql_query')}), "
            f"the result is: {state.get('sql_result')}"
        )
    else:
        state["final_response"] = (
            "Based on retrieved document context: "
            f"{state.get('retrieved_docs', [{}])[0].get('content', '')}"
        )
    return state


# --- Conditional Routing Decision ---

def select_next_node(state: AgentState) -> Literal["rag", "sql"]:
    """Conditional edge decision function directing traffic based on intent."""
    intent = state.get("intent")
    if intent == "sql":
        return "sql"
    return "rag"


# --- Workflow Graph Builder ---

def create_workflow_graph() -> StateGraph:
    """Construct and compile the complete LangGraph DAG workflow.

    Returns:
        Compiled LangGraph runnable graph instance.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("router", route_intent_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("combine", combine_node)
    workflow.add_node("respond", respond_node)

    # Define Graph Execution Flow
    workflow.set_entry_point("router")

    # Conditional Branching from Router
    workflow.add_conditional_edges(
        "router",
        select_next_node,
        {
            "rag": "rag",
            "sql": "sql",
        },
    )

    # Edge transitions to Combine and Respond
    workflow.add_edge("rag", "combine")
    workflow.add_edge("sql", "combine")
    workflow.add_edge("combine", "respond")
    workflow.add_edge("respond", END)

    logger.info("Successfully constructed LangGraph DAG workflow graph.")
    return workflow.compile()
