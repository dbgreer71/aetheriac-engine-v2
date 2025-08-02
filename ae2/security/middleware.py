"""
Security middleware for AE v2.

This module provides middleware for CORS, rate limiting, and security headers.
"""

import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from .models import SecurityConfig

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for rate limiting and security headers."""

    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config
        self.rate_limit_data: Dict[str, List[datetime]] = defaultdict(list)
        self.last_cleanup = datetime.utcnow()

    async def dispatch(self, request: Request, call_next):
        """Process the request through security middleware."""
        # Clean up old rate limit data periodically
        await self._cleanup_rate_limit_data()

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limiting
        if self.config.enable_rate_limiting:
            if not self._check_rate_limit(client_id):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests",
                        "retry_after": self.config.rate_limit_requests,
                    },
                    headers={"Retry-After": str(self.config.rate_limit_requests)},
                )

        # Process the request
        response = await call_next(request)

        # Add security headers
        if self.config.enable_security_headers:
            self._add_security_headers(response)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Try to get real IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Use User-Agent as additional identifier
        user_agent = request.headers.get("User-Agent", "unknown")

        return f"{client_ip}:{user_agent}"

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)

        # Get requests in the current window
        requests = self.rate_limit_data[client_id]
        recent_requests = [req_time for req_time in requests if req_time > window_start]

        # Update the list
        self.rate_limit_data[client_id] = recent_requests

        # Check if limit exceeded
        if len(recent_requests) >= self.config.rate_limit_requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False

        # Add current request
        recent_requests.append(now)
        self.rate_limit_data[client_id] = recent_requests

        return True

    async def _cleanup_rate_limit_data(self) -> None:
        """Clean up old rate limit data to prevent memory leaks."""
        now = datetime.utcnow()

        # Clean up every 5 minutes
        if now - self.last_cleanup < timedelta(minutes=5):
            return

        cutoff = now - timedelta(hours=1)
        cleaned_clients = []

        for client_id, requests in self.rate_limit_data.items():
            recent_requests = [req_time for req_time in requests if req_time > cutoff]

            if recent_requests:
                self.rate_limit_data[client_id] = recent_requests
            else:
                cleaned_clients.append(client_id)

        # Remove empty entries
        for client_id in cleaned_clients:
            del self.rate_limit_data[client_id]

        self.last_cleanup = now

        if cleaned_clients:
            logger.debug(
                f"Cleaned up rate limit data for {len(cleaned_clients)} clients"
            )

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to the response."""
        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Content Security Policy
        if self.config.enable_content_security_policy:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers["Content-Security-Policy"] = csp_policy

        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]


def create_cors_middleware(config: SecurityConfig):
    """Create CORS middleware with security configuration."""
    if not config.enable_cors:
        return None

    return CORSMiddleware(
        app=None,  # Will be set by FastAPI
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
        expose_headers=["X-Total-Count"],
        max_age=3600,
    )


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization."""

    def __init__(self, app):
        super().__init__(app)
        self.max_content_length = 10 * 1024 * 1024  # 10MB
        self.forbidden_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"onclick=",
        ]

    async def dispatch(self, request: Request, call_next):
        """Process the request through input validation."""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_content_length:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "message": f"Request body too large. Maximum size: {self.max_content_length} bytes",
                        },
                    )
            except ValueError:
                pass

        # Validate query parameters
        for param_name, param_value in request.query_params.items():
            if self._contains_forbidden_content(param_value):
                logger.warning(
                    f"Forbidden content detected in query parameter: {param_name}"
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_input",
                        "message": "Invalid input detected",
                    },
                )

        # For POST/PUT requests, validate body content
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8", errors="ignore")
                    if self._contains_forbidden_content(body_str):
                        logger.warning("Forbidden content detected in request body")
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "invalid_input",
                                "message": "Invalid input detected",
                            },
                        )
            except Exception as e:
                logger.error(f"Error validating request body: {e}")

        response = await call_next(request)
        return response

    def _contains_forbidden_content(self, content: str) -> bool:
        """Check if content contains forbidden patterns."""
        import re

        content_lower = content.lower()
        for pattern in self.forbidden_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for security audit logging."""

    def __init__(self, app):
        super().__init__(app)
        self.audit_logger = logging.getLogger("security.audit")

    async def dispatch(self, request: Request, call_next):
        """Process the request and log security events."""
        start_time = time.time()

        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log security events
        self._log_security_event(
            request=request,
            response=response,
            client_ip=client_ip,
            user_agent=user_agent,
            processing_time=processing_time,
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _log_security_event(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        processing_time: float,
    ) -> None:
        """Log security audit events."""
        # Determine if this is a security-relevant event
        is_security_event = (
            response.status_code >= 400
            or request.url.path.startswith("/auth")
            or request.url.path.startswith("/admin")
            or "authorization" in request.headers.get("authorization", "").lower()
        )

        if is_security_event:
            audit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "processing_time": processing_time,
                "headers": dict(request.headers),
            }

            self.audit_logger.warning(f"Security event: {audit_data}")

        # Log all requests for debugging (if enabled)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Request: {request.method} {request.url.path} "
                f"from {client_ip} - {response.status_code} "
                f"({processing_time:.3f}s)"
            )
