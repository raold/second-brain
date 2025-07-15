# app/utils/logger.py

import logging
import structlog

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Set up root logger for structlog
logging.basicConfig(
    format="%(message)s",
    stream=None,
    level=logging.INFO,
)

def get_logger(name=None):
    return structlog.get_logger(name)

logger = get_logger()
