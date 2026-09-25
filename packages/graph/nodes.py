"""LangGraph node handlers for RAG, SQL Agent, and Combined execution branches."""

import time
from typing import Any

from packages.rag.rag_service import RAGService
from packages.shared.gemini import GeminiClient
from packages.shared.logging import get_logger
from packages.shared.settings import settings
from packages.sql_agent.executor import SQLExecutorService

from .state import AgentState

logger = get_logger(__name__)


def _build_effective_question(question: str, history: list[dict[str, Any]]) -> str:
    """Build effective question string incorporating recent conversation history for follow-up questions."""
    if not history:
        return question.strip()

    # If question is short (<= 7 words) or pronoun-based, append recent history context
    if len(question.strip().split()) <= 7:
        recent_turns = history[-4:]
        turn_strs = [
            f"{turn.get('role', 'user')}: {turn.get('content', '')}"
            for turn in recent_turns
            if isinstance(turn, dict) and turn.get("content")
        ]
        if turn_strs:
            ctx_str = " | ".join(turn_strs)
            return f"[Context: {ctx_str}] Question: {question.strip()}"
    return question.strip()


def rag_node(state: AgentState) -> AgentState:
    """LangGraph node executing document context retrieval and answer generation via RAGService.

    Args:
        state: Current AgentState payload.

    Returns:
        AgentState: Updated state containing RAG answer and document citation sources.
    """
    raw_question = state.get("question") or state.get("query", "")
    history = state.get("conversation_history", [])
    effective_question = _build_effective_question(raw_question, history)

    logger.info(f"Executing LangGraph Node [rag] for question: '{raw_question}'")
    start_time = time.perf_counter()

    errors: list[str] = state.get("errors", [])

    try:
        rag_service = RAGService()
        rag_response = rag_service.answer_question(question=effective_question)

        sources = [
            {
                "filename": src.filename,
                "page": src.page,
                "chunk_index": src.chunk_index,
            }
            for src in rag_response.sources
        ]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"LangGraph Node [rag] completed in {duration_ms}ms with {len(sources)} citations.",
            extra={
                "sources_count": len(sources),
                "duration_ms": duration_ms,
            },
        )

        state["rag_answer"] = rag_response.answer
        state["sources"] = sources
        state["final_answer"] = rag_response.answer
        state["retrieved_docs"] = [
            {"filename": s["filename"], "page": s["page"]} for s in sources
        ]

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = f"RAG node execution failed: {str(exc)}"
        logger.error(
            f"LangGraph Node [rag] error after {duration_ms}ms: {err_msg}",
            exc_info=True,
        )
        errors.append(err_msg)
        state["errors"] = errors
        state["rag_answer"] = (
            "Unable to retrieve document information due to a service error."
        )
        state["final_answer"] = state["rag_answer"]
        state["sources"] = []

    return state


def _format_sql_results_text(columns: list[str], rows: list[list[Any]]) -> str:
    """Format column names and rows into readable text string for summary."""
    if not rows:
        return "No data rows returned from database query."

    headers = " | ".join(columns)
    row_strs = [" | ".join(str(cell) for cell in row) for row in rows]
    return f"Columns: [{headers}]\nData Rows:\n" + "\n".join(row_strs)


def sql_node(state: AgentState) -> AgentState:
    """LangGraph node executing text-to-SQL generation, AST validation, and database execution.

    Args:
        state: Current AgentState payload.

    Returns:
        AgentState: Updated state containing generated SQL query and structured execution results.
    """
    raw_question = state.get("question") or state.get("query", "")
    history = state.get("conversation_history", [])
    effective_question = _build_effective_question(raw_question, history)

    logger.info(f"Executing LangGraph Node [sql] for question: '{raw_question}'")
    start_time = time.perf_counter()

    errors: list[str] = state.get("errors", [])

    try:
        executor = SQLExecutorService()
        exec_result = executor.execute_question(question=effective_question)

        formatted_res = {
            "columns": exec_result.columns,
            "rows": exec_result.rows,
            "row_count": exec_result.row_count,
        }

        # Build readable answer string
        if exec_result.row_count == 0:
            final_text = f"Query executed successfully ({exec_result.sql}), but no matching database records were found."
        else:
            table_summary = _format_sql_results_text(
                exec_result.columns, exec_result.rows
            )
            final_text = (
                f"Based on database query (`{exec_result.sql}`):\n\n{table_summary}"
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"LangGraph Node [sql] completed in {duration_ms}ms ({exec_result.row_count} rows).",
            extra={
                "sql": exec_result.sql,
                "row_count": exec_result.row_count,
                "duration_ms": duration_ms,
            },
        )

        state["sql_query"] = exec_result.sql
        state["sql_result"] = formatted_res
        state["final_answer"] = final_text
        state["sources"] = []

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = f"SQL node execution failed: {str(exc)}"
        logger.error(
            f"LangGraph Node [sql] error after {duration_ms}ms: {err_msg}",
            exc_info=True,
        )
        errors.append(err_msg)
        state["errors"] = errors
        state["final_answer"] = f"Unable to execute database query: {str(exc)}"
        state["sources"] = []

    return state


def combined_node(state: AgentState) -> AgentState:
    """LangGraph node executing both RAG document retrieval and SQL Agent database analytics, fusing answers with Gemini.

    Args:
        state: Current AgentState payload.

    Returns:
        AgentState: Updated state containing synthesized combined answer and document citation sources.
    """
    question = state.get("question") or state.get("query", "")
    logger.info(f"Executing LangGraph Node [combined] for question: '{question}'")
    start_time = time.perf_counter()

    errors: list[str] = state.get("errors", [])
    rag_answer = None
    sources: list[dict[str, Any]] = []
    sql_query = None
    sql_result = None

    # Step 1: Execute RAG Service
    try:
        rag_service = RAGService()
        rag_response = rag_service.answer_question(question=question)
        rag_answer = rag_response.answer
        sources = [
            {
                "filename": src.filename,
                "page": src.page,
                "chunk_index": src.chunk_index,
            }
            for src in rag_response.sources
        ]
    except Exception as exc:
        err_msg = f"RAG execution failed in combined node: {str(exc)}"
        logger.warning(err_msg)
        errors.append(err_msg)

    # Step 2: Execute SQL Pipeline
    try:
        executor = SQLExecutorService()
        exec_result = executor.execute_question(question=question)
        sql_query = exec_result.sql
        sql_result = {
            "columns": exec_result.columns,
            "rows": exec_result.rows,
            "row_count": exec_result.row_count,
        }
    except Exception as exc:
        err_msg = f"SQL execution failed in combined node: {str(exc)}"
        logger.warning(err_msg)
        errors.append(err_msg)

    state["rag_answer"] = rag_answer
    state["sources"] = sources
    state["sql_query"] = sql_query
    state["sql_result"] = sql_result
    state["errors"] = errors

    # Step 3: Synthesize Answer
    # Graceful Fallback if SQL failed but RAG succeeded
    if rag_answer and not sql_result:
        state["final_answer"] = (
            f"{rag_answer}\n\n*(Note: Database analytics query could not be executed for this request.)*"
        )
        return state

    # Graceful Fallback if RAG failed but SQL succeeded
    if sql_result and not rag_answer:
        table_summary = _format_sql_results_text(
            sql_result["columns"], sql_result["rows"]
        )
        state["final_answer"] = (
            f"Database Analytics (`{sql_query}`):\n{table_summary}\n\n*(Note: Document context retrieval was unavailable.)*"
        )
        return state

    # If both failed
    if not rag_answer and not sql_result:
        state["final_answer"] = (
            "Unable to answer question due to RAG and SQL service errors."
        )
        return state

    # Step 4: Both RAG and SQL succeeded — Fuse responses using Gemini LLM
    if settings.is_gemini_configured:
        table_text = _format_sql_results_text(
            sql_result.get("columns", []), sql_result.get("rows", [])
        )
        fusion_prompt = f"""You are an intelligent data assistant. Synthesize a unified, natural answer to the user's question by combining information from BOTH document policy context AND database analytics.

USER QUESTION:
{question}

DOCUMENT POLICY INFORMATION:
{rag_answer}

DATABASE ANALYTICS INFORMATION (Query: {sql_query}):
{table_text}

CRITICAL INSTRUCTIONS:
- Combine both document policy and database numbers into a single cohesive response.
- Do NOT output raw JSON or code block formatting.
- Be clear, accurate, and concise.
"""
        try:
            gemini_client = GeminiClient()
            combined_text = gemini_client.chat(fusion_prompt)
            state["final_answer"] = combined_text.strip()
        except Exception as exc:
            logger.warning(
                f"LLM fusion prompt failed: {str(exc)}. Falling back to concatenated response."
            )
            table_text = _format_sql_results_text(
                sql_result.get("columns", []), sql_result.get("rows", [])
            )
            state["final_answer"] = (
                f"{rag_answer}\n\n**Database Analytics (`{sql_query}`):**\n{table_text}"
            )
    else:
        table_text = _format_sql_results_text(
            sql_result.get("columns", []), sql_result.get("rows", [])
        )
        state["final_answer"] = (
            f"{rag_answer}\n\n**Database Analytics (`{sql_query}`):**\n{table_text}"
        )

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        f"LangGraph Node [combined] completed in {duration_ms}ms.",
        extra={"duration_ms": duration_ms, "sources_count": len(sources)},
    )

    return state
