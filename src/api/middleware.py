"""
API middleware.

Custom middleware for request processing.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import structlog

from src.infrastructure.logging import get_logger
from src.infrastructure.observability import get_metrics_collector

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and tracking metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID and bind to context
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Bind to logging context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Get metrics collector
        metrics = get_metrics_collector()
        
        # Start timer
        start_time = time.time()
        
        # Create span for request
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            kind=trace.SpanKind.SERVER,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname or "localhost",
                "http.target": request.url.path,
                "request.id": request_id,
            },
        ) as span:
            try:
                # Log request
                logger.info(
                    "Request started",
                    method=request.method,
                    path=request.url.path,
                    client=request.client.host if request.client else None,
                )
                
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Update span
                span.set_attribute("http.status_code", response.status_code)
                span.set_status(Status(StatusCode.OK))
                
                # Track metrics
                metrics.track_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code,
                    duration=duration,
                )
                
                # Log response
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration * 1000,
                )
                
                # Add headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{duration * 1000:.2f}"
                
                return response
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                
                # Update span
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                # Track metrics
                metrics.track_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status=500,
                    duration=duration,
                )
                
                # Log error
                logger.error(
                    "Request failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    exc_info=True,
                )
                
                raise
            finally:
                # Clear context
                structlog.contextvars.unbind_contextvars("request_id")


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, rate_limit: int = 100, window: int = 60):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            rate_limit: Maximum requests per window
            window: Time window in seconds
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits and process request."""
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Simple in-memory rate limiting (use Redis in production)
        current_time = time.time()
        
        # Clean old entries
        self.requests = {
            k: v for k, v in self.requests.items()
            if current_time - v["timestamp"] < self.window
        }
        
        # Check rate limit
        if client_id in self.requests:
            client_data = self.requests[client_id]
            if client_data["count"] >= self.rate_limit:
                logger.warning(
                    "Rate limit exceeded",
                    client_id=client_id,
                    limit=self.rate_limit,
                )
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={"Retry-After": str(self.window)},
                )
            client_data["count"] += 1
        else:
            self.requests[client_id] = {
                "count": 1,
                "timestamp": current_time,
            }
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.rate_limit - self.requests[client_id]["count"]
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(self.requests[client_id]["timestamp"] + self.window)
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


def setup_middleware(app: FastAPI) -> None:
    """
    Setup custom middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added is first executed)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)