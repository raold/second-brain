"""
Object storage infrastructure for file attachments.

Provides MinIO/S3-compatible object storage.
"""

from .client import StorageClient, get_storage_client
from .models import StorageObject, StorageMetadata

__all__ = [
    "StorageClient",
    "get_storage_client",
    "StorageObject",
    "StorageMetadata",
]