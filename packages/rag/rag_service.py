"""RAG (Retrieval-Augmented Generation) answer generation service with source citations."""

import time

from pydantic import BaseModel, Field

from packages.rag.retriever import VectorRetriever
from packages.shared.gemini import GeminiClient
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class CitationSource(BaseModel):
    """Container model representing a document source citation."""

    filename: str = Field(..., description="Document filename")
    page: int = Field(default=1, description="Page number of cited content")
    chunk_index: int | None = Field(
        default=None, description="Optional zero-based chunk index"
    )


class RAGResponse(BaseModel):
    """Response payload returned by RAG answer generation service."""

    answer: str = Field(..., description="Grounded RAG answer string")
    sources: list[CitationSource] = Field(
        default_factory=list, description="Array of source citations"
    )


class RAGService:
    """Service combining vector retrieval and Gemini LLM prompt synthesis for grounded Q&A."""

    def __init__(
        self,
        retriever: VectorRetriever | None = None,
        gemini_client: GeminiClient | None = None,
        max_context_chars: int | None = None,
    ) -> None:
        self.retriever = retriever if retriever is not None else VectorRetriever()
        self.gemini_client = (
            gemini_client if gemini_client is not None else GeminiClient()
        )
        self.max_context_chars = (
            max_context_chars
            if max_context_chars is not None
            else settings.RAG_MAX_CONTEXT_CHARS
        )

    def answer_question(
        self,
        question: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> RAGResponse:
        """Process user question, retrieve document context, and generate grounded Gemini answer with citations.

        Args:
            question: Input user question string.
            top_k: Optional top-k retrieval count override.
            score_threshold: Optional similarity score threshold cutoff.

        Returns:
            RAGResponse: Grounded answer and list of unique source citations.

        Raises:
            ValueError: If question is empty or whitespace-only.
        """
        if not question or not question.strip():
            raise ValueError("User question cannot be empty or whitespace.")

        clean_question = question.strip()
        logger.info(f"Processing RAG Q&A for question: '{clean_question}'")
        start_time = time.perf_counter()

        # Step 1: Execute vector similarity retrieval
        chunks = self.retriever.retrieve(
            question=clean_question,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        # Step 2: Handle empty retrieval context
        if not chunks:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"No relevant document chunks retrieved for question '{clean_question}' in {duration_ms}ms. Returning fallback response."
            )
            return RAGResponse(
                answer="I couldn't find relevant information in the uploaded documents.",
                sources=[],
            )

        # Step 3: Build context string while respecting RAG_MAX_CONTEXT_CHARS
        context_blocks: list[str] = []
        sources: list[CitationSource] = []
        seen_sources: set[tuple[str, int, int | None]] = set()
        current_chars = 0

        for chunk in chunks:
            header = f"[Document: {chunk.filename}, Page: {chunk.page}]\n"
            body = f"{chunk.text}\n\n"
            block = header + body

            if current_chars + len(block) > self.max_context_chars:
                logger.info(
                    f"RAG context limit reached ({current_chars}/{self.max_context_chars} chars). Truncating remaining chunks."
                )
                break

            context_blocks.append(block)
            current_chars += len(block)

            source_key = (chunk.filename, chunk.page, chunk.chunk_index)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    CitationSource(
                        filename=chunk.filename,
                        page=chunk.page,
                        chunk_index=chunk.chunk_index,
                    )
                )

        if not context_blocks:
            return RAGResponse(
                answer="I couldn't find relevant information in the uploaded documents.",
                sources=[],
            )

        # Step 4: Construct context-grounded prompt
        formatted_context = "".join(context_blocks).strip()
        prompt = (
            "You are a helpful GenAI Data Assistant. Answer the user's question using ONLY the provided document context below.\n\n"
            "STRICT INSTRUCTIONS:\n"
            "- Answer using strictly the context provided below. Do not use outside knowledge or invent facts.\n"
            '- If the context does not contain enough information to answer the question, state: "I couldn\'t find relevant information in the uploaded documents."\n'
            "- Keep answers concise, factual, and direct.\n\n"
            f"Context:\n{formatted_context}\n\n"
            f"Question:\n{clean_question}\n\n"
            "Answer:"
        )

        # Step 5: Invoke Gemini client
        try:
            raw_answer = self.gemini_client.chat(prompt)
            answer_text = raw_answer.strip() if raw_answer else ""
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Gemini call failed during RAG answer generation after {duration_ms}ms: {str(exc)}",
                exc_info=True,
            )
            raise

        if not answer_text:
            answer_text = (
                "I couldn't find relevant information in the uploaded documents."
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"Generated grounded RAG response in {duration_ms}ms for question '{clean_question}' "
            f"({len(chunks)} chunks retrieved, {len(sources)} source citations)",
            extra={
                "question": clean_question,
                "chunks_retrieved": len(chunks),
                "citation_count": len(sources),
                "duration_ms": duration_ms,
            },
        )

        return RAGResponse(answer=answer_text, sources=sources)
