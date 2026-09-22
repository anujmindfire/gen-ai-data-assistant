"""Shared base models and schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Standard API success envelope."""

    status: str = Field(default="success")
    message: str = Field(default="Operation completed successfully")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorDetail(BaseModel):
    """Structured error payload."""

    code: int
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""

    error: ErrorDetail
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
