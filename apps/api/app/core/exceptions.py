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


class DocumentValidationException(Exception):
    """Exception raised when document upload, format, or parsing fails."""

    def __init__(
        self,
        message: str = "Invalid or unsupported document file.",
        code: str = "DOCUMENT_VALIDATION_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class DocumentNotFoundException(Exception):
    """Exception raised when document ID is not found."""

    def __init__(
        self,
        message: str = "Document not found.",
        code: str = "DOCUMENT_NOT_FOUND",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class QdrantAPIException(Exception):
    """Exception raised when Qdrant Vector DB operation fails."""

    def __init__(
        self,
        message: str = "Unable to complete Qdrant operation.",
        code: str = "QDRANT_API_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class QdrantConfigException(Exception):
    """Exception raised when Qdrant configuration is invalid."""

    def __init__(
        self,
        message: str = "Qdrant configuration error.",
        code: str = "QDRANT_CONFIG_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class DatabaseException(Exception):
    """Exception raised when database connection or inspection operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed.",
        code: str = "DATABASE_ERROR",
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom JSON exception handlers for HTTP, validation, Gemini, Qdrant, DB, and document errors.

    Args:
        app: FastAPI instance.
    """

    @app.exception_handler(DocumentValidationException)
    async def document_validation_exception_handler(
        request: Request, exc: DocumentValidationException
    ) -> JSONResponse:
        """Handler for document format validation and parsing errors."""
        logger.warning(
            f"DocumentValidationException: {exc.message} - Path: {request.url.path}"
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(DocumentNotFoundException)
    async def document_not_found_exception_handler(
        request: Request, exc: DocumentNotFoundException
    ) -> JSONResponse:
        """Handler for missing document ID errors."""
        logger.warning(
            f"DocumentNotFoundException: {exc.message} - Path: {request.url.path}"
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

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

    @app.exception_handler(QdrantAPIException)
    async def qdrant_api_exception_handler(
        request: Request, exc: QdrantAPIException
    ) -> JSONResponse:
        """Handler for Qdrant operations and connection failures."""
        logger.error(f"QdrantAPIException: {exc.message} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(QdrantConfigException)
    async def qdrant_config_exception_handler(
        request: Request, exc: QdrantConfigException
    ) -> JSONResponse:
        """Handler for invalid Qdrant configuration."""
        logger.error(f"QdrantConfigException: {exc.message} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(
        request: Request, exc: DatabaseException
    ) -> JSONResponse:
        """Handler for database connection or inspection failures."""
        logger.error(f"DatabaseException: {exc.message} - Path: {request.url.path}")
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
