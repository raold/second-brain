import logging
import sys

from app.utils.logging_config import get_logger

"""
DEPRECATED: Legacy logger utility for Second Brain application.

This module is deprecated. Please use:
    from app.utils.logging_config import get_logger
    logger = get_logger(__name__)

For new code, use the modern structured logging system.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "app.utils.logger is deprecated. Use app.utils.logging_config instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy configuration for backward compatibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("second-brain")

# Re-export modern logger functions for migration
try:
    from app.utils.logging_config import (
        LogContext,
        PerformanceLogger,
        configure_logging,
        get_logger,
    )

    # Provide migration path
    def get_modern_logger(name: str = "second-brain"):
        """Get modern structured logger. Preferred over legacy logger."""
        return get_logger(name)

except ImportError:
    # Fallback if new logging not available yet
    def get_modern_logger(name: str = "second-brain"):
        return logging.getLogger(name)

    LogContext = None
    PerformanceLogger = None

    def configure_logging():
        return None
