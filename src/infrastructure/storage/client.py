"""
MinIO/S3-compatible storage client.

Handles object storage operations.
"""

import hashlib
import io
import os
from datetime import datetime, timedelta
from typing import AsyncIterator, Optional
from uuid import uuid4

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager

from src.infrastructure.logging import get_logger
from src.infrastructure.storage.models import StorageMetadata, StorageObject

logger = get_logger(__name__)


class StorageClient:
    """S3-compatible object storage client."""
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
        region: str = "us-east-1",
    ):
        """
        Initialize storage client.
        
        Args:
            endpoint: S3 endpoint URL
            access_key: Access key ID
            secret_key: Secret access key
            secure: Use HTTPS
            region: AWS region
        """
        # Parse endpoint
        if endpoint.startswith("http://"):
            endpoint = endpoint[7:]
            secure = False
        elif endpoint.startswith("https://"):
            endpoint = endpoint[8:]
            secure = True
        
        # Create MinIO client
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
            http_client=PoolManager(
                timeout=30,
                maxsize=10,
                retries=3,
            ),
        )
        
        self.endpoint = endpoint
        self.secure = secure
    
    async def create_bucket(
        self,
        bucket_name: str,
        location: Optional[str] = None,
    ) -> bool:
        """
        Create a bucket if it doesn't exist.
        
        Args:
            bucket_name: Name of the bucket
            location: Bucket location
            
        Returns:
            Success boolean
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name, location=location)
                logger.info(f"Created bucket: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False
    
    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> Optional[StorageObject]:
        """
        Upload an object to storage.
        
        Args:
            bucket: Bucket name
            key: Object key
            data: Object data
            content_type: MIME type
            metadata: Custom metadata
            
        Returns:
            StorageObject or None on error
        """
        try:
            # Ensure bucket exists
            await self.create_bucket(bucket)
            
            # Calculate checksum
            checksum = hashlib.md5(data).hexdigest()
            
            # Prepare metadata
            custom_metadata = metadata or {}
            custom_metadata["checksum"] = checksum
            
            # Upload object
            self.client.put_object(
                bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=custom_metadata,
            )
            
            # Create storage object
            storage_metadata = StorageMetadata(
                content_type=content_type,
                size=len(data),
                checksum=checksum,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                custom_metadata=custom_metadata,
            )
            
            storage_object = StorageObject(
                key=key,
                bucket=bucket,
                data=data,
                metadata=storage_metadata,
                url=self.get_url(bucket, key),
            )
            
            logger.info(f"Uploaded object: {bucket}/{key}")
            return storage_object
            
        except S3Error as e:
            logger.error(f"Failed to upload {bucket}/{key}: {e}")
            return None
    
    async def download(
        self,
        bucket: str,
        key: str,
    ) -> Optional[StorageObject]:
        """
        Download an object from storage.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            StorageObject or None if not found
        """
        try:
            # Get object
            response = self.client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            
            # Get object info
            stat = self.client.stat_object(bucket, key)
            
            # Create metadata
            storage_metadata = StorageMetadata(
                content_type=stat.content_type,
                size=stat.size,
                checksum=stat.metadata.get("x-amz-meta-checksum", ""),
                created_at=stat.last_modified,
                modified_at=stat.last_modified,
                custom_metadata=stat.metadata,
            )
            
            # Create storage object
            storage_object = StorageObject(
                key=key,
                bucket=bucket,
                data=data,
                metadata=storage_metadata,
                url=self.get_url(bucket, key),
            )
            
            logger.info(f"Downloaded object: {bucket}/{key}")
            return storage_object
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"Object not found: {bucket}/{key}")
            else:
                logger.error(f"Failed to download {bucket}/{key}: {e}")
            return None
    
    async def delete(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        """
        Delete an object from storage.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            Success boolean
        """
        try:
            self.client.remove_object(bucket, key)
            logger.info(f"Deleted object: {bucket}/{key}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete {bucket}/{key}: {e}")
            return False
    
    async def list_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        recursive: bool = False,
    ) -> AsyncIterator[str]:
        """
        List objects in a bucket.
        
        Args:
            bucket: Bucket name
            prefix: Object key prefix
            recursive: List recursively
            
        Yields:
            Object keys
        """
        try:
            objects = self.client.list_objects(
                bucket,
                prefix=prefix,
                recursive=recursive,
            )
            
            for obj in objects:
                yield obj.object_name
                
        except S3Error as e:
            logger.error(f"Failed to list objects in {bucket}: {e}")
    
    async def exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        """
        Check if an object exists.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            Existence boolean
        """
        try:
            self.client.stat_object(bucket, key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"Failed to check {bucket}/{key}: {e}")
            return False
    
    def get_url(
        self,
        bucket: str,
        key: str,
        expires: Optional[timedelta] = None,
    ) -> str:
        """
        Get object URL.
        
        Args:
            bucket: Bucket name
            key: Object key
            expires: URL expiration time
            
        Returns:
            Object URL
        """
        if expires:
            # Generate presigned URL
            return self.client.presigned_get_object(
                bucket,
                key,
                expires=expires,
            )
        else:
            # Generate permanent URL
            protocol = "https" if self.secure else "http"
            return f"{protocol}://{self.endpoint}/{bucket}/{key}"
    
    def generate_key(
        self,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
    ) -> str:
        """
        Generate a unique object key.
        
        Args:
            prefix: Key prefix
            suffix: Key suffix (e.g., file extension)
            
        Returns:
            Object key
        """
        # Generate timestamp and UUID
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        unique_id = str(uuid4())
        
        # Build key parts
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(timestamp)
        parts.append(unique_id)
        
        # Join parts
        key = "/".join(parts)
        
        # Add suffix
        if suffix:
            key = f"{key}{suffix}"
        
        return key


# Singleton instance
_storage_client: Optional[StorageClient] = None


def get_storage_client(
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> StorageClient:
    """
    Get or create storage client instance.
    
    Args:
        endpoint: S3 endpoint
        access_key: Access key
        secret_key: Secret key
        
    Returns:
        Storage client instance
    """
    global _storage_client
    
    if _storage_client is None:
        # Get from environment if not provided
        endpoint = endpoint or os.getenv("STORAGE_ENDPOINT", "http://localhost:9000")
        access_key = access_key or os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
        secret_key = secret_key or os.getenv("STORAGE_SECRET_KEY", "minioadmin")
        
        _storage_client = StorageClient(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
        )
        
        logger.info(f"Created storage client for {endpoint}")
    
    return _storage_client