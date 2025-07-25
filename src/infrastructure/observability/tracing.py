"""
OpenTelemetry tracing configuration.

Sets up distributed tracing for the application.
"""

import os
from typing import Any, Callable, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Global tracer
tracer = trace.get_tracer("secondbrain")


def setup_tracing(
    service_name: str = "secondbrain",
    endpoint: Optional[str] = None,
    environment: str = "development",
) -> None:
    """
    Set up OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service
        endpoint: OTLP endpoint (uses env var if not provided)
        environment: Deployment environment
    """
    # Get endpoint from env if not provided
    if not endpoint:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    
    # Skip setup if no endpoint
    if not endpoint or endpoint == "none":
        logger.info("OpenTelemetry tracing disabled")
        return
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": environment,
        "service.version": os.getenv("VERSION", "3.0.0"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Create OTLP exporter
    try:
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=True,  # Use insecure for local development
        )
        
        # Add span processor
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument libraries
        FastAPIInstrumentor.instrument()
        AsyncPGInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
        AioPikaInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        
        logger.info(f"OpenTelemetry tracing enabled with endpoint: {endpoint}")
        
    except Exception as e:
        logger.warning(f"Failed to set up OpenTelemetry tracing: {e}")


def trace(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable:
    """
    Decorator for tracing functions.
    
    Args:
        name: Span name
        kind: Span kind
        attributes: Additional attributes
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_current_span() -> Optional[Span]:
    """Get the current active span."""
    return trace.get_current_span()