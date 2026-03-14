"""Middleware for request timing and logging."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.middleware.logging import get_logger

logger = get_logger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status code, and duration for every request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))
        return response