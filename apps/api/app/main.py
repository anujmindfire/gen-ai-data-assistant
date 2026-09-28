"""Main FastAPI Application Entrypoint for GenAI Data Assistant API."""

from apps.api.app.api.router import api_router
from apps.api.app.core.exceptions import register_exception_handlers
from apps.api.app.core.middleware import LoggingMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger("api.main")


tags_metadata = [
    {
        "name": "Health",
        "description": "Service status, readiness, component connectivity, and version information.",
    },
    {
        "name": "Chat",
        "description": "LangGraph multi-agent intelligent chat endpoint orchestrating RAG document retrieval and Text-to-SQL query generation.",
    },
    {
        "name": "Sessions",
        "description": "Session memory management endpoints for inspecting and clearing conversation history.",
    },
    {
        "name": "Documents",
        "description": "Document ingestion, listing, deletion, and semantic vector similarity search using Qdrant.",
    },
    {
        "name": "Database",
        "description": "SQL database schema introspection, read-only SQL validation, Text-to-SQL generation, and safe execution.",
    },
]


def create_app() -> FastAPI:
    """Factory function initializing FastAPI app instance with routers and middleware."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-ready GenAI Data Assistant API powering RAG document retrieval "
            "and SQL database analytics using LangChain, LangGraph, and Google Gemini.\n\n"
            "## Architecture Highlights\n"
            "- **Intelligent Router**: Classifies questions into `rag`, `sql`, or `combined` routes.\n"
            "- **Vector Store**: Qdrant embedding search for PDF, DOCX, TXT, and Markdown documents.\n"
            "- **Read-Only SQL Validation**: AST validation using `sqlglot` guaranteeing safe SELECT queries.\n"
            "- **Conversation Memory**: Thread-safe session tracking supporting context continuation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=tags_metadata,
        contact={
            "name": "GenAI Data Assistant Team",
            "url": "https://github.com/anujmindfire/gen-ai-data-assistant",
        },
        license_info={
            "name": "MIT License",
        },
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
