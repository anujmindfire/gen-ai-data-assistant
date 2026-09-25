"""Master APIRouter instance combining all domain endpoint routes."""

from apps.api.app.api.chat import router as chat_router
from apps.api.app.api.database import router as database_router
from apps.api.app.api.documents import router as documents_router
from apps.api.app.api.health import router as health_router
from apps.api.app.api.sessions import router as sessions_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(database_router)
api_router.include_router(sessions_router)
