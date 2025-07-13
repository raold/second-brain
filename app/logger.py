# app/logger.py
from loguru import logger
import os
from pathlib import Path

# Ensure logs directory exists
logs_path = Path(__file__).parent.parent / "logs"
logs_path.mkdir(parents=True, exist_ok=True)

# Configure Loguru
logger.add(
    logs_path / "processor.log",
    rotation="1 MB",           # Rotate after 1MB
    retention="10 days",       # Keep 10 days of logs
    enqueue=True,              # Async logging
    backtrace=True,            # Show tracebacks
    diagnose=True              # Include variable states
)
