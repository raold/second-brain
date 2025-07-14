# app/utils/logger.py

import os
from loguru import logger
from app.config import Config
from app.utils.logger import get_logger

logger = get_logger()

# Ensure logs directory exists
os.makedirs(os.path.dirname(Config.LOG_PATH), exist_ok=True)

logger.add(
    Config.LOG_PATH,
    rotation="1 MB",
    retention="10 days",
    level=Config.LOG_LEVEL,
    enqueue=True,
    backtrace=True,
    diagnose=True
)

logger.info(f"Logger initialized. Path: {Config.LOG_PATH}, Level: {Config.LOG_LEVEL}")
