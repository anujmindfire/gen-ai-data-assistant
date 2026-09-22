"""Pydantic schemas for /chat endpoint."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User query payload for the /chat endpoint."""

    prompt: str = Field(
        ...,
        description="Natural language query or question from user",
        examples=["What was the total revenue in Q1 2026?"],
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Optional conversation session UUID"
    )


class ChatResponse(BaseModel):
    """Response payload returned by the /chat endpoint."""

    conversation_id: str
    response: str
    intent: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
