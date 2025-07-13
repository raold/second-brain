# app/utils/logger.py

import os
from loguru import logger

LOG_PATH = os.getenv("LOG_PATH", "logs/processor.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger.add(
    LOG_PATH,
    rotation="1 MB",
    retention="10 days",
    level=LOG_LEVEL,
    enqueue=True,
    backtrace=True,
    diagnose=True
)

logger.info(f"Logger initialized. Path: {LOG_PATH}, Level: {LOG_LEVEL}")
