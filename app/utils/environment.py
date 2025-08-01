"""
Environment utilities for configuration and setup.
"""

import os
from pathlib import Path
from typing import Optional

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Get environment variable with optional default and validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        Environment variable value or default
        
    Raises:
        ValueError: If required variable is not found
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable {key} not found")
    
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Boolean value
    """
    value = os.getenv(key, "").lower()
    
    if not value:
        return default
    
    return value in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Integer value
    """
    value = os.getenv(key)
    
    if not value:
        return default
    
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {value}, using default: {default}")
        return default


def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve()
    
    # Walk up until we find a directory with key project files
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    
    # Fallback to 2 levels up from this file
    return Path(__file__).resolve().parent.parent.parent


def load_env_file(env_file: Optional[Path] = None) -> None:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to .env file (defaults to project root/.env)
    """
    if env_file is None:
        env_file = get_project_root() / ".env"
    
    if not env_file.exists():
        logger.debug(f"Environment file not found: {env_file}")
        return
    
    try:
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"Loaded {key} from {env_file}")
    
    except Exception as e:
        logger.error(f"Error loading environment file {env_file}: {e}")
