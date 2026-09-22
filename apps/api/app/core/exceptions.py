"""Centralized exception handlers for FastAPI application."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from packages.shared.logging import get_logger
from packages.shared.utils import get_utc_now

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom JSON exception handlers for all HTTP errors and unhandled exceptions.

    Args:
        app: FastAPI instance.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handler for HTTP status exceptions (including 501 Not Implemented)."""
        logger.warning(
            f"HTTPException [{exc.status_code}]: {exc.detail} - Path: {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
                    "details": exc.detail if not isinstance(exc.detail, str) else None,
                },
                "timestamp": get_utc_now(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handler for Pydantic input validation failures."""
        logger.warning(f"RequestValidationError - Path: {request.url.path} Errors: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Validation Error",
                    "details": exc.errors(),
                },
                "timestamp": get_utc_now(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler for unhandled internal server exceptions."""
        logger.error(
            f"Unhandled exception on path {request.url.path}: {str(exc)}", exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Internal Server Error",
                    "details": str(exc),
                },
                "timestamp": get_utc_now(),
            },
        )
