"""
Attachment service for handling file uploads.

Manages file attachments for memories.
"""

import mimetypes
from typing import Optional
from uuid import UUID

from src.domain.models.memory import MemoryId
from src.infrastructure.logging import get_logger
from src.infrastructure.storage import StorageClient, get_storage_client

logger = get_logger(__name__)


class AttachmentService:
    """Service for managing memory attachments."""
    
    def __init__(
        self,
        storage_client: Optional[StorageClient] = None,
        bucket_name: str = "secondbrain-attachments",
    ):
        """
        Initialize attachment service.
        
        Args:
            storage_client: Storage client instance
            bucket_name: Bucket for attachments
        """
        self.storage = storage_client or get_storage_client()
        self.bucket_name = bucket_name
    
    async def upload_attachment(
        self,
        memory_id: MemoryId,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload an attachment for a memory.
        
        Args:
            memory_id: Memory ID
            filename: Original filename
            data: File data
            content_type: MIME type
            
        Returns:
            Attachment URL or None on error
        """
        try:
            # Guess content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or "application/octet-stream"
            
            # Generate object key
            suffix = ""
            if "." in filename:
                suffix = "." + filename.split(".")[-1]
            
            key = self.storage.generate_key(
                prefix=f"memories/{memory_id}",
                suffix=suffix,
            )
            
            # Upload to storage
            storage_object = await self.storage.upload(
                bucket=self.bucket_name,
                key=key,
                data=data,
                content_type=content_type,
                metadata={
                    "memory_id": str(memory_id),
                    "original_filename": filename,
                },
            )
            
            if storage_object:
                logger.info(f"Uploaded attachment {key} for memory {memory_id}")
                return storage_object.url
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to upload attachment: {e}")
            return None
    
    async def download_attachment(
        self,
        attachment_url: str,
    ) -> Optional[tuple[bytes, str, str]]:
        """
        Download an attachment.
        
        Args:
            attachment_url: Attachment URL
            
        Returns:
            Tuple of (data, content_type, filename) or None
        """
        try:
            # Extract bucket and key from URL
            # Format: http://endpoint/bucket/key
            parts = attachment_url.split("/")
            if len(parts) < 5:
                logger.error(f"Invalid attachment URL: {attachment_url}")
                return None
            
            bucket = parts[3]
            key = "/".join(parts[4:])
            
            # Download from storage
            storage_object = await self.storage.download(bucket, key)
            
            if storage_object:
                # Get original filename from metadata
                filename = storage_object.metadata.custom_metadata.get(
                    "x-amz-meta-original_filename",
                    key.split("/")[-1]
                )
                
                return (
                    storage_object.data,
                    storage_object.metadata.content_type,
                    filename,
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            return None
    
    async def delete_attachment(
        self,
        attachment_url: str,
    ) -> bool:
        """
        Delete an attachment.
        
        Args:
            attachment_url: Attachment URL
            
        Returns:
            Success boolean
        """
        try:
            # Extract bucket and key from URL
            parts = attachment_url.split("/")
            if len(parts) < 5:
                return False
            
            bucket = parts[3]
            key = "/".join(parts[4:])
            
            # Delete from storage
            return await self.storage.delete(bucket, key)
            
        except Exception as e:
            logger.error(f"Failed to delete attachment: {e}")
            return False
    
    async def list_memory_attachments(
        self,
        memory_id: MemoryId,
    ) -> list[str]:
        """
        List all attachments for a memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            List of attachment URLs
        """
        try:
            prefix = f"memories/{memory_id}/"
            urls = []
            
            async for key in self.storage.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            ):
                url = self.storage.get_url(self.bucket_name, key)
                urls.append(url)
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to list attachments: {e}")
            return []
    
    async def delete_memory_attachments(
        self,
        memory_id: MemoryId,
    ) -> int:
        """
        Delete all attachments for a memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Number of attachments deleted
        """
        try:
            prefix = f"memories/{memory_id}/"
            deleted = 0
            
            # List and delete all objects
            async for key in self.storage.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            ):
                if await self.storage.delete(self.bucket_name, key):
                    deleted += 1
            
            if deleted > 0:
                logger.info(f"Deleted {deleted} attachments for memory {memory_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete attachments: {e}")
            return 0