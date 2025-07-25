"""
Storage models for object storage.

Defines data structures for storage operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class StorageMetadata:
    """Metadata for stored objects."""
    
    content_type: str
    size: int
    checksum: str
    created_at: datetime
    modified_at: datetime
    custom_metadata: dict[str, str]


@dataclass
class StorageObject:
    """Represents a stored object."""
    
    key: str
    bucket: str
    data: bytes
    metadata: StorageMetadata
    url: Optional[str] = None
    
    @property
    def full_path(self) -> str:
        """Get full object path."""
        return f"{self.bucket}/{self.key}"