"""
Second Brain Application Version Information
"""

__version__ = "2.1.0"
__version_info__ = (2, 1, 0)
__build__ = "stable"
__release_date__ = "2025-07-17"

# Version metadata
VERSION_METADATA = {
    "version": __version__,
    "version_info": __version_info__,
    "build": __build__,
    "release_date": __release_date__,
    "codename": "Phoenix",  # Complete refactor/rebirth
    "stability": "stable",
    "api_version": "v1",
}

def get_version_info():
    """Get formatted version information."""
    return {
        "version": __version__,
        "build": __build__,
        "release_date": __release_date__,
        "codename": VERSION_METADATA["codename"],
        "api_version": VERSION_METADATA["api_version"],
    }
