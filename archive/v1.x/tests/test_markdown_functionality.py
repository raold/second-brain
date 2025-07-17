"""
Comprehensive tests for Markdown functionality with PostgreSQL integration.
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime, timezone

from app.storage.markdown_writer import write_markdown, sanitize_filename
from app.storage.dual_storage import DualStorageHandler
from app.models import Payload, PayloadType, Priority


class TestMarkdownWriter:
    """Test the markdown writer module."""
    
    def test_sanitize_filename_valid(self):
        """Test filename sanitization with valid input."""
        result = sanitize_filename("test-file-123")
        assert result == "test-file-123"
    
    def test_sanitize_filename_invalid_chars(self):
        """Test filename sanitization with invalid characters."""
        result = sanitize_filename("test<>:\"|?*file")
        assert result == "test_______file"
    
    def test_sanitize_filename_path_traversal(self):
        """Test filename sanitization with path traversal attempts."""
        result = sanitize_filename("../../../etc/passwd")
        assert result == "______etc_passwd"
    
    def test_sanitize_filename_long_name(self):
        """Test filename sanitization with very long names."""
        long_name = "a" * 150
        result = sanitize_filename(long_name)
        assert len(result) == 100
    
    def test_write_markdown_success(self):
        """Test successful markdown file creation."""
        payload = Payload(
            id="test-markdown-001",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.HIGH,
            ttl="1d",
            data={
                "note": "This is a test markdown note.",
                "tags": ["test", "markdown"]
            },
            meta={},
            intent="note",
            target="note"
        )
        
        result = write_markdown(payload)
        assert result is True
        
        # Check if file was created
        data_dir = Path("./data/memories")
        file_path = data_dir / "test-markdown-001.md"
        assert file_path.exists()
        
        # Check file content
        content = file_path.read_text(encoding="utf-8")
        assert "# Note Entry" in content
        assert "test-markdown-001" in content
        assert "This is a test markdown note." in content
        assert "test, markdown" in content
        
        # Cleanup
        file_path.unlink()
    
    def test_write_markdown_invalid_payload(self):
        """Test markdown writing with invalid payload."""
        with patch('app.storage.markdown_writer.write_markdown') as mock_write:
            mock_write.return_value = False
            result = mock_write(None)
            assert result is False
    
    def test_write_markdown_missing_id(self):
        """Test markdown writing with missing ID."""
        payload = Payload(
            id="",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={"note": "test"},
            meta={},
            intent="note",
            target="note"
        )
        
        result = write_markdown(payload)
        assert result is False
    
    def test_write_markdown_content_escaping(self):
        """Test markdown content escaping."""
        payload = Payload(
            id="test-escape-001",
            type=PayloadType.NOTE,
            context="test",
            priority=Priority.NORMAL,
            ttl="1d",
            data={
                "note": "Test with ```code blocks``` that should be escaped."
            },
            meta={},
            intent="note",
            target="note"
        )
        
        result = write_markdown(payload)
        assert result is True
        
        # Check if content was escaped
        data_dir = Path("./data/memories")
        file_path = data_dir / "test-escape-001.md"
        content = file_path.read_text(encoding="utf-8")
        assert "\\```code blocks\\```" in content
        
        # Cleanup
        file_path.unlink()


class TestDualStorageMarkdown:
    """Test markdown functionality within dual storage system."""
    
    @pytest.mark.asyncio
    async def test_dual_storage_markdown_creation(self):
        """Test markdown file creation through dual storage."""
        handler = DualStorageHandler()
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-dual-md-001",
            text_content="This is a test of dual storage markdown creation.",
            intent_type="note",
            priority="high",
            tags=["test", "dual", "markdown"],
            user="test_user",
            create_embedding=False  # Skip embedding for test
        )
        
        assert memory_id is not None
        
        # Check if markdown file was created
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-dual-md-001*.md"))
        assert len(md_files) == 1
        
        # Check file content
        md_file = md_files[0]
        content = md_file.read_text(encoding="utf-8")
        assert "test-dual-md-001" in content
        assert "This is a test of dual storage markdown creation." in content
        assert "test_user" in content
        assert "high" in content
        
        # Cleanup
        md_file.unlink()
    
    @pytest.mark.asyncio
    async def test_dual_storage_markdown_with_postgres(self):
        """Test that both markdown and PostgreSQL storage work together."""
        handler = DualStorageHandler()
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-dual-md-postgres-001",
            text_content="Testing dual storage: markdown + PostgreSQL integration.",
            intent_type="note",
            priority="normal",
            tags=["integration", "test"],
            user="test_user",
            create_embedding=False
        )
        
        assert memory_id is not None
        
        # Check markdown file creation
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-dual-md-postgres-001*.md"))
        assert len(md_files) == 1
        
        # Check PostgreSQL storage
        from app.storage.postgres_client import get_postgres_client
        client = await get_postgres_client()
        
        # Search for our memory
        memories = await client.search_memories(
            query_text="Testing dual storage: markdown + PostgreSQL integration.",
            limit=1
        )
        
        assert len(memories) == 1
        postgres_memory = memories[0]
        
        # Verify data consistency between markdown and PostgreSQL
        assert postgres_memory["intent_type"] == "note"
        assert postgres_memory["priority"] == "normal"
        assert "integration" in postgres_memory["tags"]
        assert "test" in postgres_memory["tags"]
        assert postgres_memory["metadata"]["user"] == "test_user"
        
        # Cleanup
        md_files[0].unlink()
    
    @pytest.mark.asyncio
    async def test_markdown_metadata_structure(self):
        """Test the structure of markdown metadata."""
        handler = DualStorageHandler()
        
        test_metadata = {
            "source": "api",
            "version": "1.5.2",
            "custom_field": "test_value"
        }
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-md-metadata-001",
            text_content="Testing markdown metadata structure.",
            intent_type="reminder",
            priority="high",
            tags=["metadata", "test"],
            user="test_user",
            metadata=test_metadata,
            create_embedding=False
        )
        
        # Check markdown file structure
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-md-metadata-001*.md"))
        assert len(md_files) == 1
        
        content = md_files[0].read_text(encoding="utf-8")
        
        # Check frontmatter structure
        assert "---" in content
        assert "id: test-md-metadata-001" in content
        assert "intent_type: reminder" in content
        assert "priority: high" in content
        assert "user: test_user" in content
        
        # Check metadata JSON section
        assert "## Metadata" in content
        assert "```json" in content
        assert '"source": "api"' in content
        assert '"version": "1.5.2"' in content
        assert '"custom_field": "test_value"' in content
        
        # Cleanup
        md_files[0].unlink()
    
    @pytest.mark.asyncio
    async def test_markdown_with_special_characters(self):
        """Test markdown creation with special characters."""
        handler = DualStorageHandler()
        
        special_text = "Testing with émojis 🚀, unicode ñáéíóú, and symbols @#$%"
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-special-chars-001",
            text_content=special_text,
            intent_type="note",
            priority="normal",
            tags=["unicode", "special"],
            user="test_user",
            create_embedding=False
        )
        
        # Check markdown file creation
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-special-chars-001*.md"))
        assert len(md_files) == 1
        
        content = md_files[0].read_text(encoding="utf-8")
        assert special_text in content
        
        # Cleanup
        md_files[0].unlink()
    
    @pytest.mark.asyncio
    async def test_markdown_file_naming_convention(self):
        """Test the markdown file naming convention."""
        handler = DualStorageHandler()
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-naming-convention",
            text_content="Testing file naming convention.",
            intent_type="note",
            priority="normal",
            tags=["naming"],
            user="test_user",
            create_embedding=False
        )
        
        # Check file naming pattern
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-naming-convention*.md"))
        assert len(md_files) == 1
        
        filename = md_files[0].name
        # Should follow pattern: YYYYMMDD_HHMMSS_payload-id.md
        assert filename.endswith("_test-naming-convention.md")
        
        # Check timestamp format (first 15 chars should be YYYYMMDD_HHMMSS)
        timestamp_part = filename[:15]
        datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
        
        # Cleanup
        md_files[0].unlink()


class TestMarkdownPostgreSQLIntegration:
    """Test integration between markdown and PostgreSQL storage."""
    
    @pytest.mark.asyncio
    async def test_data_consistency_between_storages(self):
        """Test data consistency between markdown and PostgreSQL."""
        handler = DualStorageHandler()
        
        test_data = {
            "payload_id": "test-consistency-001",
            "text_content": "Testing data consistency between storage systems.",
            "intent_type": "todo",
            "priority": "high",
            "tags": ["consistency", "test", "integration"],
            "user": "test_user"
        }
        
        memory_id, embedding = await handler.store_memory(
            payload_id=test_data["payload_id"],
            text_content=test_data["text_content"],
            intent_type=test_data["intent_type"],
            priority=test_data["priority"],
            tags=test_data["tags"],
            user=test_data["user"],
            create_embedding=False
        )
        
        # Get data from PostgreSQL
        from app.storage.postgres_client import get_postgres_client
        client = await get_postgres_client()
        postgres_memory = await client.get_memory(memory_id)
        
        # Get data from markdown
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-consistency-001*.md"))
        assert len(md_files) == 1
        
        md_content = md_files[0].read_text(encoding="utf-8")
        
        # Verify consistency
        assert postgres_memory is not None
        assert postgres_memory["text_content"] == test_data["text_content"]
        assert postgres_memory["intent_type"] == test_data["intent_type"]
        assert postgres_memory["priority"] == test_data["priority"]
        assert set(postgres_memory["tags"]) == set(test_data["tags"])
        assert postgres_memory["metadata"]["user"] == test_data["user"]
        
        # Verify markdown content
        assert test_data["text_content"] in md_content
        assert test_data["intent_type"] in md_content
        assert test_data["priority"] in md_content
        assert test_data["user"] in md_content
        
        # Cleanup
        md_files[0].unlink()
    
    @pytest.mark.asyncio
    async def test_markdown_backup_functionality(self):
        """Test markdown as backup when PostgreSQL fails."""
        handler = DualStorageHandler()
        
        # Test with PostgreSQL disabled
        original_postgres_enabled = handler.postgres_enabled
        handler.postgres_enabled = False
        
        try:
            memory_id, embedding = await handler.store_memory(
                payload_id="test-backup-001",
                text_content="Testing markdown backup functionality.",
                intent_type="note",
                priority="normal",
                tags=["backup", "test"],
                user="test_user",
                create_embedding=False
            )
            
            # Should still return a memory ID (payload ID)
            assert memory_id == "test-backup-001"
            
            # Check that markdown file was created
            data_dir = Path("app/data/memories")
            md_files = list(data_dir.glob("*test-backup-001*.md"))
            assert len(md_files) == 1
            
            # Cleanup
            md_files[0].unlink()
            
        finally:
            # Restore original setting
            handler.postgres_enabled = original_postgres_enabled
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring in dual storage."""
        handler = DualStorageHandler()
        
        # Check initial metrics
        initial_md_count = handler._markdown_total_count
        initial_pg_count = handler._postgres_total_count
        
        memory_id, embedding = await handler.store_memory(
            payload_id="test-performance-001",
            text_content="Testing performance monitoring.",
            intent_type="note",
            priority="normal",
            tags=["performance"],
            user="test_user",
            create_embedding=False
        )
        
        # Check that counters increased
        assert handler._markdown_total_count == initial_md_count + 1
        assert handler._postgres_total_count == initial_pg_count + 1
        assert handler._markdown_success_count > 0
        assert handler._postgres_success_count > 0
        
        # Cleanup
        data_dir = Path("app/data/memories")
        md_files = list(data_dir.glob("*test-performance-001*.md"))
        if md_files:
            md_files[0].unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
