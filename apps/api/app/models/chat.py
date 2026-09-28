"""Pydantic schemas for /chat endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User query request payload for /chat endpoint."""

    message: str = Field(
        ...,
        description="Natural language message prompt from user",
        examples=["Hello"],
    )
    session_id: str | None = Field(
        default=None,
        description="Optional conversation session ID string for session history and context tracking",
        examples=["sess_123abc456"],
    )


class CitationSource(BaseModel):
    """Document source citation metadata for chat response."""

    filename: str = Field(..., description="Document filename")
    page: int = Field(default=1, description="Page number of cited content")
    chunk_index: int | None = Field(
        default=None, description="Optional zero-based chunk index"
    )


class ChatResponse(BaseModel):
    """Response payload returned by /chat endpoint."""

    answer: str = Field(..., description="Generated answer text from Gemini")
    session_id: str = Field(..., description="Active conversation session ID")
    route: str | None = Field(
        default=None,
        description="Selected routing branch ('rag', 'sql', or 'combined')",
    )
    sources: list[CitationSource] = Field(
        default_factory=list, description="Array of document source citations"
    )
    provider: str = Field(default="gemini", description="LLM service provider name")
    model: str = Field(..., description="Gemini model identifier used")
