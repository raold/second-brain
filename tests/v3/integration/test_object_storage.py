"""
Integration tests for object storage.
"""

import asyncio
import hashlib
import pytest
from datetime import datetime
from io import BytesIO
from uuid import uuid4

from src.infrastructure.storage import StorageClient
from src.infrastructure.storage.models import StorageObject


@pytest.mark.integration
@pytest.mark.asyncio
class TestStorageClient:
    """Integration tests for StorageClient."""
    
    @pytest.fixture
    async def test_bucket(self, storage_client):
        """Create a test bucket for the test."""
        bucket_name = f"test-{uuid4().hex[:8]}"
        await storage_client.create_bucket(bucket_name)
        yield bucket_name
        # Cleanup
        await storage_client.remove_bucket(bucket_name, force=True)
    
    async def test_bucket_operations(self, storage_client):
        """Test bucket creation, existence check, and removal."""
        # Arrange
        bucket_name = f"test-bucket-{uuid4().hex[:8]}"
        
        # Act & Assert - Create bucket
        await storage_client.create_bucket(bucket_name)
        exists = await storage_client.bucket_exists(bucket_name)
        assert exists is True
        
        # Act & Assert - Remove bucket
        await storage_client.remove_bucket(bucket_name)
        exists = await storage_client.bucket_exists(bucket_name)
        assert exists is False
    
    async def test_bucket_already_exists(self, storage_client, test_bucket):
        """Test creating a bucket that already exists."""
        # Should not raise error (idempotent)
        await storage_client.create_bucket(test_bucket)
        exists = await storage_client.bucket_exists(test_bucket)
        assert exists is True
    
    async def test_upload_and_download(self, storage_client, test_bucket):
        """Test uploading and downloading objects."""
        # Arrange
        key = "test-file.txt"
        content = b"Hello, World! This is test content."
        content_type = "text/plain"
        
        # Act - Upload
        result = await storage_client.upload(
            bucket=test_bucket,
            key=key,
            data=content,
            content_type=content_type,
        )
        
        # Assert upload result
        assert result is not None
        assert isinstance(result, StorageObject)
        assert result.bucket == test_bucket
        assert result.key == key
        assert result.size == len(content)
        assert result.content_type == content_type
        assert result.etag is not None
        
        # Act - Download
        downloaded = await storage_client.download(test_bucket, key)
        
        # Assert download
        assert downloaded == content
    
    async def test_upload_with_metadata(self, storage_client, test_bucket):
        """Test uploading with custom metadata."""
        # Arrange
        key = "file-with-metadata.json"
        content = b'{"data": "test"}'
        metadata = {
            "author": "test-user",
            "version": "1.0",
            "created": datetime.utcnow().isoformat(),
        }
        
        # Act
        result = await storage_client.upload(
            bucket=test_bucket,
            key=key,
            data=content,
            content_type="application/json",
            metadata=metadata,
        )
        
        # Get object info
        obj_info = await storage_client.get_object_info(test_bucket, key)
        
        # Assert
        assert result is not None
        if obj_info and hasattr(obj_info, 'metadata'):
            assert obj_info.metadata.get("author") == "test-user"
            assert obj_info.metadata.get("version") == "1.0"
    
    async def test_large_file_upload(self, storage_client, test_bucket):
        """Test uploading large files."""
        # Arrange
        key = "large-file.bin"
        size_mb = 10
        content = b"x" * (size_mb * 1024 * 1024)  # 10MB
        
        # Act
        result = await storage_client.upload(
            bucket=test_bucket,
            key=key,
            data=content,
        )
        
        # Assert
        assert result is not None
        assert result.size == len(content)
        
        # Download and verify
        downloaded = await storage_client.download(test_bucket, key)
        assert len(downloaded) == len(content)
        assert downloaded[:100] == content[:100]  # Check beginning
        assert downloaded[-100:] == content[-100:]  # Check end
    
    async def test_delete_object(self, storage_client, test_bucket):
        """Test deleting objects."""
        # Arrange
        key = "to-be-deleted.txt"
        content = b"Delete me"
        
        # Upload
        await storage_client.upload(test_bucket, key, content)
        
        # Act - Delete
        deleted = await storage_client.delete(test_bucket, key)
        
        # Assert
        assert deleted is True
        
        # Verify deleted
        downloaded = await storage_client.download(test_bucket, key)
        assert downloaded is None
    
    async def test_delete_nonexistent(self, storage_client, test_bucket):
        """Test deleting non-existent object."""
        # Act
        deleted = await storage_client.delete(test_bucket, "does-not-exist.txt")
        
        # Assert - Should return False or not raise
        assert deleted is False
    
    async def test_list_objects(self, storage_client, test_bucket):
        """Test listing objects in bucket."""
        # Arrange - Upload multiple files
        files = {
            "dir1/file1.txt": b"Content 1",
            "dir1/file2.txt": b"Content 2",
            "dir2/file3.txt": b"Content 3",
            "root-file.txt": b"Root content",
        }
        
        for key, content in files.items():
            await storage_client.upload(test_bucket, key, content)
        
        # Act - List all
        all_objects = await storage_client.list_objects(test_bucket)
        
        # Assert
        assert len(all_objects) == 4
        object_keys = [obj.key for obj in all_objects]
        for key in files.keys():
            assert key in object_keys
        
        # Act - List with prefix
        dir1_objects = await storage_client.list_objects(test_bucket, prefix="dir1/")
        
        # Assert
        assert len(dir1_objects) == 2
        for obj in dir1_objects:
            assert obj.key.startswith("dir1/")
    
    async def test_presigned_urls(self, storage_client, test_bucket):
        """Test generating presigned URLs."""
        # Arrange
        key = "private-file.pdf"
        content = b"Private content"
        
        # Upload
        await storage_client.upload(test_bucket, key, content)
        
        # Act - Get presigned URL
        url = await storage_client.get_presigned_url(
            bucket=test_bucket,
            key=key,
            expires_in=3600,  # 1 hour
        )
        
        # Assert
        assert url is not None
        assert isinstance(url, str)
        assert test_bucket in url
        assert key in url
        
        # In real test, would use httpx to download via URL
        # For now, just verify format
        assert url.startswith("http")
    
    async def test_copy_object(self, storage_client, test_bucket):
        """Test copying objects."""
        # Arrange
        source_key = "source.txt"
        dest_key = "destination.txt"
        content = b"Content to copy"
        
        # Upload source
        await storage_client.upload(test_bucket, source_key, content)
        
        # Act - Copy
        copied = await storage_client.copy_object(
            source_bucket=test_bucket,
            source_key=source_key,
            dest_bucket=test_bucket,
            dest_key=dest_key,
        )
        
        # Assert
        assert copied is True
        
        # Verify both exist
        source_data = await storage_client.download(test_bucket, source_key)
        dest_data = await storage_client.download(test_bucket, dest_key)
        
        assert source_data == content
        assert dest_data == content
    
    async def test_concurrent_uploads(self, storage_client, test_bucket):
        """Test concurrent upload operations."""
        # Arrange
        async def upload_file(index: int) -> StorageObject:
            key = f"concurrent/file-{index}.txt"
            content = f"Content for file {index}".encode()
            return await storage_client.upload(test_bucket, key, content)
        
        # Act - Upload 10 files concurrently
        tasks = [upload_file(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 10
        assert all(r is not None for r in results)
        
        # Verify all uploaded
        objects = await storage_client.list_objects(test_bucket, prefix="concurrent/")
        assert len(objects) == 10
    
    async def test_upload_stream(self, storage_client, test_bucket):
        """Test uploading from stream/file-like object."""
        # Arrange
        key = "stream-upload.dat"
        content = b"Stream content " * 1000
        stream = BytesIO(content)
        
        # Act - Upload from stream
        result = await storage_client.upload_stream(
            bucket=test_bucket,
            key=key,
            stream=stream,
            size=len(content),
        )
        
        # Assert
        assert result is not None
        assert result.size == len(content)
        
        # Verify
        downloaded = await storage_client.download(test_bucket, key)
        assert downloaded == content
    
    async def test_multipart_upload(self, storage_client, test_bucket):
        """Test multipart upload for very large files."""
        # Arrange
        key = "multipart-large.bin"
        part_size = 5 * 1024 * 1024  # 5MB parts
        total_parts = 3
        
        # Create large content
        parts = []
        for i in range(total_parts):
            part_content = f"Part {i} content ".encode() * (part_size // 20)
            parts.append(part_content[:part_size])
        
        # Act - Multipart upload
        upload_id = await storage_client.create_multipart_upload(
            bucket=test_bucket,
            key=key,
        )
        
        part_etags = []
        for i, part_data in enumerate(parts):
            etag = await storage_client.upload_part(
                bucket=test_bucket,
                key=key,
                upload_id=upload_id,
                part_number=i + 1,
                data=part_data,
            )
            part_etags.append((i + 1, etag))
        
        # Complete upload
        result = await storage_client.complete_multipart_upload(
            bucket=test_bucket,
            key=key,
            upload_id=upload_id,
            parts=part_etags,
        )
        
        # Assert
        assert result is not None
        
        # Verify by downloading
        downloaded = await storage_client.download(test_bucket, key)
        expected = b"".join(parts)
        assert len(downloaded) == len(expected)
    
    async def test_storage_lifecycle(self, storage_client, test_bucket):
        """Test complete lifecycle of storage operations."""
        # Arrange
        base_key = "lifecycle-test"
        versions = []
        
        # Act - Upload multiple versions
        for i in range(3):
            key = f"{base_key}-v{i}.txt"
            content = f"Version {i} content".encode()
            
            result = await storage_client.upload(
                bucket=test_bucket,
                key=key,
                data=content,
                metadata={"version": str(i)},
            )
            versions.append((key, result))
        
        # List versions
        objects = await storage_client.list_objects(
            test_bucket,
            prefix=base_key,
        )
        
        # Delete old versions
        for key, _ in versions[:-1]:  # Keep only latest
            await storage_client.delete(test_bucket, key)
        
        # Final listing
        final_objects = await storage_client.list_objects(
            test_bucket,
            prefix=base_key,
        )
        
        # Assert
        assert len(objects) == 3
        assert len(final_objects) == 1
        assert final_objects[0].key == versions[-1][0]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAttachmentService:
    """Integration tests for attachment service."""
    
    async def test_attachment_upload_flow(self, storage_client, test_bucket):
        """Test complete attachment upload flow."""
        from src.application.services.attachment_service import AttachmentService
        
        # Arrange
        service = AttachmentService(storage_client, default_bucket=test_bucket)
        
        user_id = uuid4()
        memory_id = uuid4()
        filename = "test-document.pdf"
        content = b"PDF content here"
        content_type = "application/pdf"
        
        # Act - Upload attachment
        attachment = await service.upload_attachment(
            user_id=user_id,
            memory_id=memory_id,
            filename=filename,
            content=content,
            content_type=content_type,
        )
        
        # Assert
        assert attachment is not None
        assert attachment.filename == filename
        assert attachment.size == len(content)
        assert attachment.content_type == content_type
        assert attachment.storage_key is not None
        
        # Act - Download
        downloaded = await service.download_attachment(
            user_id=user_id,
            attachment_id=attachment.id,
        )
        
        # Assert
        assert downloaded is not None
        assert downloaded["content"] == content
        assert downloaded["filename"] == filename
        assert downloaded["content_type"] == content_type
    
    async def test_attachment_security(self, storage_client, test_bucket):
        """Test attachment access control."""
        from src.application.services.attachment_service import AttachmentService
        
        # Arrange
        service = AttachmentService(storage_client, default_bucket=test_bucket)
        
        user1_id = uuid4()
        user2_id = uuid4()
        memory_id = uuid4()
        
        # User 1 uploads
        attachment = await service.upload_attachment(
            user_id=user1_id,
            memory_id=memory_id,
            filename="private.txt",
            content=b"Private data",
        )
        
        # Act - User 2 tries to download
        with pytest.raises(PermissionError):
            await service.download_attachment(
                user_id=user2_id,
                attachment_id=attachment.id,
            )
        
        # User 1 can download
        downloaded = await service.download_attachment(
            user_id=user1_id,
            attachment_id=attachment.id,
        )
        
        # Assert
        assert downloaded is not None
        assert downloaded["content"] == b"Private data"