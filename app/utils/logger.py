# app/utils/logger.py

import os
import sys

from loguru import logger

_log_initialized = False

def get_logger():
    """Initializes and returns the logger instance, avoiding reinitialization."""
    global _log_initialized
    if not _log_initialized:
        try:
            from app.config import Config  # Lazy import to avoid circular dependency

            log_path = Config.LOG_PATH
            log_level = Config.LOG_LEVEL

            # Ensure log directory exists
            log_dir = os.path.dirname(log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            # Remove default handler
            logger.remove()
            
            # Add file handler with rotation
            logger.add(
                log_path,
                rotation="10 MB",
                retention="7 days",
                level=log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
                backtrace=True,
                diagnose=True
            )
            
            # Add console handler for development
            logger.add(
                sys.stderr,
                level=log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
                       "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
                colorize=True
            )

            logger.info(f"Logger initialized. Path: {log_path}, Level: {log_level}")
            _log_initialized = True
            
        except Exception as e:
            # Fallback to basic logging if configuration fails
            logger.remove()
            logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")
            logger.warning(f"Failed to initialize logger with config: {e}. Using fallback configuration.")
            _log_initialized = True

    return logger
