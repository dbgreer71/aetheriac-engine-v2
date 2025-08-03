"""
FastAPI middleware for observability.

This module provides middleware for request ID correlation,
structured logging, and request timing.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_request_id, json_log, should_log


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for request correlation and structured logging."""

    def __init__(self, app: ASGIApp, sample_rate: float = 1.0):
        super().__init__(app)
        self.sample_rate = sample_rate

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability instrumentation."""

        # Get or generate request ID
        request_id = get_request_id(request)

        # Store request ID in request state for later use
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log request start
        if should_log(self.sample_rate):
            json_log(
                "info",
                "Request started",
                req_id=request_id,
                method=request.method,
                path=request.url.path,
                query=dict(request.query_params),
                user_agent=request.headers.get("user-agent", ""),
                client_ip=request.client.host if request.client else None,
            )

        try:
            # Process request
            response = await call_next(request)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Get additional context from request state
            intent = getattr(request.state, "intent", None)
            target = getattr(request.state, "target", None)
            cache_hit = getattr(request.state, "cache_hit", None)
            mode = getattr(request.state, "mode", None)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            if should_log(self.sample_rate):
                json_log(
                    "info",
                    "Request completed",
                    req_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    lat_ms=round(latency_ms, 2),
                    intent=intent,
                    target=target,
                    cache_hit=cache_hit,
                    mode=mode,
                )

            return response

        except Exception as e:
            # Calculate latency for failed requests
            latency_ms = (time.time() - start_time) * 1000

            # Log request failure
            if should_log(self.sample_rate):
                json_log(
                    "error",
                    "Request failed",
                    req_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    lat_ms=round(latency_ms, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # Re-raise the exception
            raise
