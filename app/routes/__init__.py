"""
Route handlers for Second Brain API v2.
Clean, minimal implementation using only the excellent V2 API.
"""

# Only import what we need - the excellent V2 API
from .v2_api import router as v2_api_router

__all__ = [
    "v2_api_router",
]
