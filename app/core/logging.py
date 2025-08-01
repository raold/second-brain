import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.utils.logging_config import get_logger

"""
Centralized logging configuration for Second Brain v3.0.0

This module provides:
- Structured logging with context
- Performance monitoring
- Request/response logging
- Error tracking
- Audit logging
"""

import traceback
from contextvars import ContextVar
from functools import wraps

import structlog
from fastapi import Request, Response
from fastapi.routing import APIRoute
from pythonjsonlogger import jsonlogger

# Context variables for request tracking
import os
from logging.handlers import RotatingFileHandler

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


class LogConfig(BaseModel):
    """Logging configuration"""

    level: str = "INFO"
    format: str = "json"  # json or text
    enable_console: bool = True
    enable_file: bool = True
    file_path: str = "logs/second-brain.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_performance_logging: bool = True
    enable_audit_logging: bool = True
    enable_request_logging: bool = True
    slow_request_threshold: float = 1.0  # seconds


class StructuredLogger:
    """Structured logger with context support"""

    def __init__(self, name: str, config: LogConfig):
        self.name = name
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.config.level))
        logger.handlers = []  # Clear existing handlers

        # Console handler
        if self.config.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            if self.config.format == "json":
                formatter = jsonlogger.JsonFormatter(
                    "%(timestamp)s %(level)s %(name)s %(message)s",
                    timestamp=lambda: datetime.utcnow().isoformat(),
                )
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler
        if self.config.enable_file:

            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.config.file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = RotatingFileHandler(
                self.config.file_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )

            if self.config.format == "json":
                formatter = jsonlogger.JsonFormatter(
                    "%(timestamp)s %(level)s %(name)s %(message)s",
                    timestamp=lambda: datetime.utcnow().isoformat(),
                )
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _add_context(self, extra: dict[str, Any]) -> dict[str, Any]:
        """Add request context to log data"""
        context = {
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        context.update(extra)
        return context

    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        extra = self._add_context(kwargs)
        self.logger.debug(message, extra={"structured": extra})

    def info(self, message: str, **kwargs):
        """Log info message with context"""
        extra = self._add_context(kwargs)
        self.logger.info(message, extra={"structured": extra})

    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        extra = self._add_context(kwargs)
        self.logger.warning(message, extra={"structured": extra})

    def error(self, message: str, exception: Exception | None = None, **kwargs):
        """Log error message with context and exception details"""
        extra = self._add_context(kwargs)
        if exception:
            extra["error_type"] = type(exception).__name__
            extra["error_message"] = str(exception)
            extra["traceback"] = traceback.format_exc()
        self.logger.error(message, extra={"structured": extra})

    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        extra = self._add_context(kwargs)
        self.logger.critical(message, extra={"structured": extra})


class PerformanceLogger:
    """Context manager for performance logging"""

    def __init__(self, operation: str, logger: StructuredLogger, **kwargs):
        self.operation = operation
        self.logger = logger
        self.extra = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", operation=self.operation, **self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type:
            self.logger.error(
                f"{self.operation} failed",
                exception=exc_val,
                operation=self.operation,
                duration_ms=duration * 1000,
                **self.extra,
            )
        else:
            log_level = "warning" if duration > 1.0 else "debug"
            getattr(self.logger, log_level)(
                f"{self.operation} completed",
                operation=self.operation,
                duration_ms=duration * 1000,
                **self.extra,
            )


class AuditLogger:
    """Logger for audit events"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_event(
        self,
        event_type: str,
        resource: str,
        action: str,
        result: str,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Log an audit event"""
        self.logger.info(
            "Audit event",
            event_type=event_type,
            resource=resource,
            action=action,
            result=result,
            user_id=user_id or user_id_var.get(),
            details=details or {},
            audit=True,
        )


class LoggingRoute(APIRoute):
    """Custom route class that logs requests and responses"""

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def logging_route_handler(request: Request) -> Response:
            # Extract request ID
            request_id = request.headers.get("X-Request-ID", str(time.time()))
            request_id_var.set(request_id)

            # Get logger
            logger = get_logger("api.request")

            # Log request
            start_time = time.time()
            logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params),
                client_host=request.client.host if request.client else None,
            )

            try:
                # Call the actual route
                response = await original_route_handler(request)

                # Log response
                duration = time.time() - start_time
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration * 1000,
                )

                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id

                return response

            except Exception as e:
                # Log error
                duration = time.time() - start_time
                logger.error(
                    "Request failed",
                    exception=e,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration * 1000,
                )
                raise

        return logging_route_handler


# Global logger instances
_loggers: dict[str, StructuredLogger] = {}
_config: LogConfig = LogConfig()


def configure_logging(config: LogConfig):
    """Configure global logging settings"""
    global _config
    _config = config


def get_logger(name: str) -> StructuredLogger:
    """Get or create a logger instance"""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, _config)
    return _loggers[name]


def get_audit_logger() -> AuditLogger:
    """Get the audit logger"""
    return AuditLogger(get_logger("audit"))


def log_function_call(func):
    """Decorator to log function calls"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        with PerformanceLogger(f"{func.__name__}", logger, args=str(args), kwargs=str(kwargs)):
            return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        with PerformanceLogger(f"{func.__name__}", logger, args=str(args), kwargs=str(kwargs)):
            return func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Structured logging with structlog
def setup_structlog():
    """Configure structlog for structured logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Initialize logging on import
setup_structlog()
