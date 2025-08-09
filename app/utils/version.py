import os
from typing import Any

"""
Version information utility for Second Brain
"""


def get_version_info() -> dict[str, Any]:
    """
    Get version information for the application

    Returns:
        Dictionary containing version information
    """
    return {
        "version": os.getenv("APP_VERSION", "4.2.1"),
        "environment": os.getenv("SECOND_BRAIN_ENV", "development"),
        "build": os.getenv("BUILD_NUMBER", "local"),
        "commit": os.getenv("GIT_COMMIT", "unknown"),
    }
