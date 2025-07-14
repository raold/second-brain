# app/utils/logger.py

import os
from loguru import logger

_log_initialized = False

def get_logger():
    """Initializes and returns the logger instance, avoiding reinitialization."""
    global _log_initialized
    if not _log_initialized:
        from app.config import Config  # Lazy import to avoid circular dependency

        log_path = Config.LOG_PATH
        log_level = Config.LOG_LEVEL

        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        logger.remove()
        logger.add(log_path, rotation="10 MB", retention="7 days", level=log_level)
        logger.add(lambda msg: print(msg, end=""), level=log_level)

        logger.info(f"Logger initialized. Path: {log_path}, Level: {log_level}")
        _log_initialized = True

    return logger
