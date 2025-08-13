"""Version information for the Second Brain application."""

import sys
from typing import Dict

VERSION = "4.2.3"
BUILD_DATE = "2025-08-13"


def get_version_info() -> Dict[str, str]:
    """Get version information for the application."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "python_version": sys.version,
        "platform": sys.platform,
    }


def get_version_string() -> str:
    """Get a formatted version string."""
    return f"Second Brain v{VERSION} ({BUILD_DATE})"
