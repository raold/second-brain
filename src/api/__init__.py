"""
API layer for Second Brain.

FastAPI-based REST API with best practices.
"""

from .app import create_app
from .middleware import setup_middleware
from .routes import setup_routes

__all__ = [
    "create_app",
    "setup_middleware",
    "setup_routes",
]