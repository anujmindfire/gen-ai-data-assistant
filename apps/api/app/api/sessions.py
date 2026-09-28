"""Session memory management API routes for inspecting and clearing conversation context."""

from fastapi import APIRouter, HTTPException, status
from packages.graph.memory import SessionData, memory_manager
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class DeleteSessionResponse(BaseModel):
    """Response payload returned when a session is deleted."""

    message: str
    session_id: str


@router.get(
    "/{session_id}",
    response_model=SessionData,
    status_code=status.HTTP_200_OK,
    summary="Get Session Memory History",
    description="Retrieves message history and previous context for a given session ID.",
)
async def get_session_endpoint(session_id: str) -> SessionData:
    """Get session history and metadata by session_id."""
    session = memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return session


@router.delete(
    "/{session_id}",
    response_model=DeleteSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Session Memory",
    description="Deletes session memory history for a given session ID.",
)
async def delete_session_endpoint(session_id: str) -> DeleteSessionResponse:
    """Delete session memory by session_id."""
    deleted = memory_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return DeleteSessionResponse(
        message="Session deleted successfully",
        session_id=session_id,
    )
