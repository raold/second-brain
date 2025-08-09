"""
Modern structured logging configuration for Second Brain.

Provides centralized logging configuration with:
- Environment-specific settings
- Structured JSON logging for production
- Request correlation tracking
- Performance metrics integration
"""

import json
import logging
import logging.config
import logging.handlers
import os
import sys
import time
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

import psutil

# Context variables for request tracing
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
operation_var: ContextVar[str | None] = ContextVar("operation", default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables if available
        if request_id := request_id_var.get():
            log_data["request_id"] = request_id
        if user_id := user_id_var.get():
            log_data["user_id"] = user_id
        if operation := operation_var.get():
            log_data["operation"] = operation

        # Add exception information
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add performance metrics if available
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "memory_mb"):
            log_data["memory_mb"] = record.memory_mb

        return json.dumps(log_data, ensure_ascii=False)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s", datefmt="%H:%M:%S"
        )

    def format(self, record: logging.LogRecord) -> str:
        # Add context to message if available
        context_parts = []
        if request_id := request_id_var.get():
            context_parts.append(f"req:{request_id[:8]}")
        if user_id := user_id_var.get():
            context_parts.append(f"user:{user_id}")
        if operation := operation_var.get():
            context_parts.append(f"op:{operation}")

        if context_parts:
            record.msg = f"[{' | '.join(context_parts)}] {record.msg}"

        return super().format(record)


class SecondBrainLogger:
    """Enhanced logger with context and structured logging support."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: dict[str, Any] = {}

    def with_context(self, **kwargs) -> "SecondBrainLogger":
        """Create logger instance with additional context."""
        new_logger = SecondBrainLogger(self.logger.name)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(self, level: int, message: str, *args, **kwargs):
        """Enhanced logging with context and metrics."""
        extra_data = {**self._context}

        # Extract metrics from kwargs
        if "duration_ms" in kwargs:
            extra_data["duration_ms"] = kwargs.pop("duration_ms")
        if "memory_mb" in kwargs:
            extra_data["memory_mb"] = kwargs.pop("memory_mb")

        # Add any additional context
        extra_data.update(kwargs.pop("extra", {}))

        # Create log record with extra data
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=args,
            exc_info=kwargs.get("exc_info"),
        )
        record.extra_data = extra_data

        self.logger.handle(record)

    def debug(self, message: str, *args, **kwargs):
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        # Get current exception info properly

        exc_info = sys.exc_info()
        if exc_info and exc_info[0] is not None:
            kwargs["exc_info"] = exc_info
        else:
            # If no exception, just log as error
            kwargs.pop("exc_info", None)
        self.error(message, *args, **kwargs)


def configure_logging() -> None:
    """Configure application logging based on environment."""
    # Get configuration from environment directly to avoid circular import
    log_level_str = os.getenv("LOG_LEVEL", "INFO")

    # Determine if we should use structured logging
    use_structured = os.getenv("LOG_FORMAT", "structured").lower() == "structured"
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    # Get log level
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Clear any existing configuration
    logging.getLogger().handlers.clear()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Choose formatter based on environment
    if use_structured or is_production:
        formatter = StructuredFormatter()
    else:
        formatter = DevelopmentFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler for production
    if is_production:
        file_handler = logging.handlers.RotatingFileHandler(
            filename="logs/second-brain.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Set third-party loggers to higher levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log configuration
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level_str,
            "structured": use_structured,
            "environment": os.getenv("ENVIRONMENT", "development"),
        },
    )


def get_logger(name: str) -> SecondBrainLogger:
    """Get enhanced logger instance."""
    return SecondBrainLogger(name)


class LogContext:
    """Context manager for request/operation logging context."""

    def __init__(self, operation: str = None, user_id: str = None, request_id: str = None):
        self.operation = operation
        self.user_id = user_id
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.tokens = []

    def __enter__(self):
        if self.request_id:
            self.tokens.append(request_id_var.set(self.request_id))
        if self.user_id:
            self.tokens.append(user_id_var.set(self.user_id))
        if self.operation:
            self.tokens.append(operation_var.set(self.operation))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in reversed(self.tokens):
            token.var.set(token.old_value)


class PerformanceLogger:
    """Context manager for performance logging."""

    def __init__(self, operation: str, logger: SecondBrainLogger = None):
        self.operation = operation
        self.logger = logger or get_logger(__name__)
        self.start_time = None
        self.start_memory = None

    def __enter__(self):

        self.start_time = time.time()
        try:
            process = psutil.Process()
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            self.start_memory = None

        self.logger.debug(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        duration_ms = (time.time() - self.start_time) * 1000

        extra = {"duration_ms": duration_ms}

        if self.start_memory:
            try:
                process = psutil.Process()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_delta = current_memory - self.start_memory
                extra["memory_mb"] = current_memory
                extra["memory_delta_mb"] = memory_delta
            except Exception:
                pass

        if exc_type:
            self.logger.error(
                f"Operation failed: {self.operation}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra=extra,
            )
        else:
            level = "warning" if duration_ms > 1000 else "info"
            getattr(self.logger, level)(f"Operation completed: {self.operation}", extra=extra)


# Export commonly used functions
__all__ = ["configure_logging", "get_logger", "LogContext", "PerformanceLogger"]
