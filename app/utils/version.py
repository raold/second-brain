"""
Version information utility for Second Brain
"""

import os
from typing import Any


def get_version_info() -> dict[str, Any]:
    """
    Get version information for the application

    Returns:
        Dictionary containing version information
    """
    return {
        "version": os.getenv("APP_VERSION", "3.0.0"),
        "environment": os.getenv("SECOND_BRAIN_ENV", "development"),
        "build": os.getenv("BUILD_NUMBER", "local"),
        "commit": os.getenv("GIT_COMMIT", "unknown")
    }
