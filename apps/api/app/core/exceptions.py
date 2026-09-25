"""Centralized exception handlers for FastAPI application."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from packages.shared.logging import get_logger

logger = get_logger(__name__)


class GeminiAPIException(Exception):
    """Exception raised when Gemini API invocation fails."""

    def __init__(
        self,
        message: str = "Unable to reach Gemini.",
        code: str = "GEMINI_API_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class GeminiConfigException(Exception):
    """Exception raised when Gemini API configuration is missing or invalid."""

    def __init__(
        self,
        message: str = "GEMINI_API_KEY is not configured.",
        code: str = "GEMINI_CONFIG_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom JSON exception handlers for all HTTP, validation, and Gemini errors.

    Args:
        app: FastAPI instance.
    """

    @app.exception_handler(GeminiAPIException)
    async def gemini_api_exception_handler(
        request: Request, exc: GeminiAPIException
    ) -> JSONResponse:
        """Handler for Gemini API execution failures."""
        logger.error(f"GeminiAPIException: {exc.message} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(GeminiConfigException)
    async def gemini_config_exception_handler(
        request: Request, exc: GeminiConfigException
    ) -> JSONResponse:
        """Handler for missing or invalid Gemini configuration."""
        logger.error(f"GeminiConfigException: {exc.message} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handler for standard HTTP status exceptions."""
        logger.warning(
            f"HTTPException [{exc.status_code}]: {exc.detail} - Path: {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": (
                        exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
                    ),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handler for input validation failures."""
        logger.warning(
            f"RequestValidationError - Path: {request.url.path} Errors: {exc.errors()}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request body.",
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler for unhandled server exceptions."""
        logger.error(
            f"Unhandled exception on path {request.url.path}: {str(exc)}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                }
            },
        )
