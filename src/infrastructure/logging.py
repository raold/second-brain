"""
Structured logging configuration for Second Brain.

Uses structlog for structured logging with JSON output.
Integrates with OpenTelemetry for distributed tracing.
"""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder
from structlog.stdlib import BoundLogger


def setup_logging(
    level: str = "INFO",
    json_logs: bool = True,
    correlation_id_var: Optional[str] = "correlation_id",
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to output JSON formatted logs
        correlation_id_var: Name of context var for correlation ID
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Structlog processors
    processors = [
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        
        # Add log level
        structlog.stdlib.add_log_level,
        
        # Add logger name
        structlog.stdlib.add_logger_name,
        
        # Add callsite parameters
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),
        
        # Add correlation ID if available
        structlog.contextvars.merge_contextvars,
        
        # Process stdlib logging
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure output format
    if json_logs:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer()
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True)
        )
    
    # Apply formatter to all handlers
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Replace existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


def log_error(logger: BoundLogger, error: Exception, **extra: Any) -> None:
    """
    Log an error with exception information.
    
    Args:
        logger: Logger instance
        error: Exception to log
        **extra: Additional context
    """
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        exc_info=True,
        **extra
    )


def log_request(
    logger: BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra: Any
) -> None:
    """
    Log an HTTP request.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **extra: Additional context
    """
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **extra
    )


def log_database_query(
    logger: BoundLogger,
    query: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    **extra: Any
) -> None:
    """
    Log a database query.
    
    Args:
        logger: Logger instance
        query: SQL query
        duration_ms: Query duration in milliseconds
        rows_affected: Number of rows affected
        **extra: Additional context
    """
    logger.debug(
        "database_query",
        query=query[:200],  # Truncate long queries
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        **extra
    )


def log_event(
    logger: BoundLogger,
    event_type: str,
    aggregate_id: str,
    **extra: Any
) -> None:
    """
    Log a domain event.
    
    Args:
        logger: Logger instance
        event_type: Type of event
        aggregate_id: ID of the aggregate
        **extra: Additional context
    """
    logger.info(
        "domain_event",
        event_type=event_type,
        aggregate_id=aggregate_id,
        **extra
    )


# Create module-level logger
logger = get_logger(__name__)