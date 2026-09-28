"""Intent router node for classifying questions into 'rag', 'sql', or 'combined' routes."""

import json
import re
import time

from packages.shared.gemini import GeminiClient
from packages.shared.logging import get_logger
from packages.shared.settings import settings

from .state import AgentState

logger = get_logger(__name__)


def classify_question_heuristic(question: str) -> str:
    """Fallback keyword heuristic classifier for question routing.

    Args:
        question: Input user question text.

    Returns:
        str: Route decision ('rag', 'sql', or 'combined').
    """
    q_lower = question.lower().strip()

    sql_keywords = [
        "revenue",
        "sales",
        "order",
        "customer",
        "product",
        "total",
        "count",
        "amount",
        "spending",
        "top 5",
        "top 10",
        "top five",
    ]
    rag_keywords = [
        "policy",
        "guideline",
        "handbook",
        "document",
        "rule",
        "leave",
        "vacation",
        "refund",
        "procedure",
        "terms",
    ]

    has_sql = any(kw in q_lower for kw in sql_keywords)
    has_rag = any(kw in q_lower for kw in rag_keywords)

    if has_sql and has_rag:
        return "combined"
    if has_sql:
        return "sql"
    return "rag"


def route_intent_node(state: AgentState) -> AgentState:
    """LangGraph router node classifying input question into 'rag', 'sql', or 'combined' route.

    Args:
        state: Current AgentState payload.

    Returns:
        AgentState: Updated state dictionary containing classified route.
    """
    question = state.get("question") or state.get("query", "")
    if not question or not question.strip():
        state["route"] = "rag"
        state["intent"] = "rag"
        return state

    clean_question = question.strip()
    start_time = time.perf_counter()

    logger.info(f"LangGraph Router Node evaluating question: '{clean_question}'")

    route = None
    history = state.get("conversation_history", [])
    history_context = ""
    if history:
        # Build brief context string from recent turns (last 4 messages)
        recent_msgs = history[-4:]
        history_lines = [
            f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
            for msg in recent_msgs
            if isinstance(msg, dict) and msg.get("content")
        ]
        if history_lines:
            history_context = (
                "RECENT CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n\n"
            )

    # Step 1: Try Gemini LLM Classification if configured
    if settings.is_gemini_configured:
        prompt = f"""You are a router node in an AI data assistant. Classify the user question into exactly ONE of the three routes:
1. "rag": Questions about unstructured documents, policies, guidelines, handbooks, or text rules.
2. "sql": Questions about database analytics, totals, revenue, sales, order counts, customer rankings, or structured metrics.
3. "combined": Questions asking for BOTH document policy rules AND database numbers in a single request.

{history_context}CURRENT USER QUESTION:
{clean_question}

CRITICAL INSTRUCTIONS:
- If the question is a follow-up (e.g. "What about the second one?"), use the conversation history to determine the appropriate route.
- Respond ONLY with a valid JSON object: {{"route": "rag"}} or {{"route": "sql"}} or {{"route": "combined"}}.
- Do NOT output explanations or markdown code fences.
"""
        try:
            client = GeminiClient()
            raw_res = client.chat(prompt)
            clean_res = re.sub(
                r"^```(?:json)?\s*", "", raw_res.strip(), flags=re.IGNORECASE
            )
            clean_res = re.sub(r"\s*```$", "", clean_res).strip()
            parsed = json.loads(clean_res)
            candidate = str(parsed.get("route", "")).lower().strip()
            if candidate in ("rag", "sql", "combined"):
                route = candidate
        except Exception as exc:
            logger.warning(
                f"Gemini LLM router classification failed: {str(exc)}. Falling back to heuristic classifier."
            )

    # Step 2: Fallback to Heuristic Classifier if route is unassigned
    if not route:
        # Check if follow-up question and previous_route exists
        prev_route = state.get("previous_route")
        if (
            prev_route in ("rag", "sql", "combined")
            and len(clean_question.split()) <= 6
        ):
            route = prev_route
        else:
            route = classify_question_heuristic(clean_question)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        f"LangGraph Router classified question as route '{route}' in {duration_ms}ms.",
        extra={
            "question": clean_question,
            "route": route,
            "duration_ms": duration_ms,
        },
    )

    state["route"] = route
    state["intent"] = route
    return state
