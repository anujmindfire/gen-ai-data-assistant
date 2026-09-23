"""Pydantic schemas for /chat endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User query request payload for /chat endpoint."""

    message: str = Field(
        ...,
        description="Natural language message prompt from user",
        examples=["Hello"],
    )


class ChatResponse(BaseModel):
    """Response payload returned by /chat endpoint."""

    answer: str = Field(..., description="Generated answer text from Gemini")
    provider: str = Field(default="gemini", description="LLM service provider name")
    model: str = Field(..., description="Gemini model identifier used")
