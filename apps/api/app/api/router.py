"""Master APIRouter instance combining all domain endpoint routes."""

from fastapi import APIRouter
from apps.api.app.api.health import router as health_router
from apps.api.app.api.chat import router as chat_router
from apps.api.app.api.documents import router as documents_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
