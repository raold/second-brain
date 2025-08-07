"""
Service layer for V2 API only.
Clean, minimal services that work with the excellent V2 API.
"""

# Only include services we actually use in V2 API
from .memory_service import MemoryService

__all__ = ["MemoryService"]
