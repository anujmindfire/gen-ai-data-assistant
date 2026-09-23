"""Structured logging middleware for tracking request ID, duration, and endpoint stats."""

import time
import uuid

from fastapi import Request
from packages.shared.logging import get_logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = get_logger("api.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for injecting Request ID header and logging execution latency."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"Request {request.method} {request.url.path} finished in {duration_ms}ms with status {response.status_code}",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "duration_ms": duration_ms,
                "status_code": response.status_code,
            },
        )

        return response
