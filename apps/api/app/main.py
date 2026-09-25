"""Main FastAPI Application Entrypoint for GenAI Data Assistant API."""

from apps.api.app.api.router import api_router
from apps.api.app.core.exceptions import register_exception_handlers
from apps.api.app.core.middleware import LoggingMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger("api.main")


def create_app() -> FastAPI:
    """Factory function initializing FastAPI app instance with routers and middleware."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-ready GenAI Data Assistant API powering RAG document retrieval "
            "and SQL database analytics using LangChain, LangGraph, and Google Gemini."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom structured logging middleware
    app.add_middleware(LoggingMiddleware)

    # Register central exception handlers
    register_exception_handlers(app)

    # Mount master API router
    app.include_router(api_router)

    logger.info(
        f"Initialized FastAPI App: {settings.APP_NAME} (v{settings.APP_VERSION})"
    )
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.app.main:app", host="0.0.0.0", port=8000, reload=True)
