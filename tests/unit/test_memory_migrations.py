"""
Focused tests for memory migrations module.

Tests key functionality of memory migration system using the actual class interfaces.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.bulk_memory_operations import BulkMemoryItem
from app.memory_migrations import (
    AddMemoryTypeClassification,
    ConsolidateDuplicateMemories,
)
from app.migration_framework import MigrationType


@pytest.fixture
def mock_pool():
    """Mock database connection pool."""
    pool = AsyncMock()

    # Create mock connection
    mock_conn = AsyncMock()

    # Mock the acquire method to return an async context manager
    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    pool.acquire = mock_acquire
    pool._mock_conn = mock_conn  # Store for easy access in tests
    return pool


class TestAddMemoryTypeClassification:
    """Test the AddMemoryTypeClassification concrete migration."""

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_get_metadata(self, mock_engine_class, mock_pool):
        """Test migration metadata creation."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        metadata = migration._get_metadata()

        assert metadata.id == "classify_memory_types_001"
        assert metadata.name == "Classify memories by cognitive type"
        assert metadata.migration_type == MigrationType.MEMORY_DATA
        assert metadata.reversible is True
        assert metadata.author == "system"
        assert isinstance(metadata.created_at, datetime)

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_get_memories_to_migrate(self, mock_engine_class, mock_pool):
        """Test retrieving memories that need classification."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        # Use the mock connection from the fixture
        mock_pool._mock_conn.fetch.return_value = [
            {"id": 1, "content": "Remember when we went to the park", "metadata": {}},
            {"id": 2, "content": "How to bake a cake", "metadata": {}},
        ]

        result = await migration.get_memories_to_migrate()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

        # Verify SQL query was called
        mock_pool._mock_conn.fetch.assert_called_once()
        call_args = mock_pool._mock_conn.fetch.call_args[0][0]
        assert "memory_type IS NULL" in call_args
        assert "ORDER BY created_at" in call_args

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_transform_memory_episodic(self, mock_engine_class, mock_pool):
        """Test episodic memory classification."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        memory = {
            "id": 1,
            "content": "Remember when I was at the beach yesterday",
            "metadata": {"location": "beach"},
        }

        result = await migration.transform_memory(memory)

        assert isinstance(result, BulkMemoryItem)
        assert result.memory_id == 1
        assert result.content == memory["content"]
        assert result.memory_type == "episodic"
        assert result.metadata["classification"]["type"] == "episodic"
        assert result.metadata["classification"]["confidence"] == 0.85
        assert result.metadata["location"] == "beach"  # Original metadata preserved

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_transform_memory_procedural(self, mock_engine_class, mock_pool):
        """Test procedural memory classification."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        memory = {
            "id": 2,
            "content": "How to change a tire: steps to follow the procedure",
            "metadata": {},
        }

        result = await migration.transform_memory(memory)

        assert result.memory_type == "procedural"
        assert result.metadata["classification"]["type"] == "procedural"
        assert result.metadata["classification"]["confidence"] == 0.85

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_transform_memory_semantic(self, mock_engine_class, mock_pool):
        """Test semantic memory classification (default)."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        memory = {
            "id": 3,
            "content": "Paris is the capital of France",
            "metadata": {},
        }

        result = await migration.transform_memory(memory)

        assert result.memory_type == "semantic"
        assert result.metadata["classification"]["type"] == "semantic"

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_get_original_memories_empty(self, mock_engine_class, mock_pool):
        """Test getting original memories for rollback."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        # Current implementation returns empty list
        result = await migration.get_original_memories()
        assert result == []


class TestConsolidateDuplicateMemories:
    """Test the ConsolidateDuplicateMemories concrete migration."""

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_get_metadata(self, mock_engine_class, mock_pool):
        """Test migration metadata creation."""
        mock_engine_class.return_value = AsyncMock()

        migration = ConsolidateDuplicateMemories.__new__(ConsolidateDuplicateMemories)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        metadata = migration._get_metadata()

        assert metadata.id == "consolidate_duplicates_001"
        assert metadata.name == "Consolidate duplicate memories"
        assert metadata.migration_type == MigrationType.MEMORY_DATA
        assert metadata.dependencies == ["classify_memory_types_001"]
        assert metadata.reversible is True
        assert metadata.version == "2.5.1"

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_get_memories_to_migrate(self, mock_engine_class, mock_pool):
        """Test retrieving duplicate memory groups."""
        mock_engine_class.return_value = AsyncMock()

        migration = ConsolidateDuplicateMemories.__new__(ConsolidateDuplicateMemories)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        # Use the mock connection from the fixture
        mock_pool._mock_conn.fetch.return_value = [
            {
                "id1": 1,
                "id2": 2,
                "content1": "Paris is the capital of France",
                "content2": "Paris is France's capital city",
                "metadata1": {"source": "book"},
                "metadata2": {"source": "web"},
                "similarity": 0.97,
            },
            {
                "id1": 3,
                "id2": 4,
                "content1": "How to bake a cake",
                "content2": "Steps for baking cake",
                "metadata1": {},
                "metadata2": {"difficulty": "easy"},
                "similarity": 0.96,
            },
        ]

        result = await migration.get_memories_to_migrate()

        assert len(result) == 2

        # Check first group
        group1 = result[0]
        assert group1["primary_id"] == 1
        assert group1["duplicate_ids"] == [2]
        assert len(group1["contents"]) == 2
        assert len(group1["metadatas"]) == 2

        # Verify SQL query for similarity was called
        mock_pool._mock_conn.fetch.assert_called_once()
        call_args = mock_pool._mock_conn.fetch.call_args[0][0]
        assert "similarity_pairs" in call_args
        assert "embedding" in call_args
        assert "0.95" in call_args

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_transform_memory_consolidation(self, mock_engine_class, mock_pool):
        """Test memory consolidation transformation."""
        mock_engine_class.return_value = AsyncMock()

        migration = ConsolidateDuplicateMemories.__new__(ConsolidateDuplicateMemories)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        memory_group = {
            "primary_id": 1,
            "duplicate_ids": [2, 3],
            "contents": [
                "Short content",
                "This is a much longer and more detailed content that should be selected",
                "Medium content here",
            ],
            "metadatas": [
                {"source": "book", "confidence": 0.9},
                {"source": "web", "author": "expert"},
                {"difficulty": "easy"},
            ],
        }

        result = await migration.transform_memory(memory_group)

        assert isinstance(result, BulkMemoryItem)
        assert result.memory_id == 1
        # Should select longest content
        assert result.content == "This is a much longer and more detailed content that should be selected"

        # Check merged metadata
        assert result.metadata["source"] == "web"  # Later values override
        assert result.metadata["confidence"] == 0.9
        assert result.metadata["author"] == "expert"
        assert result.metadata["difficulty"] == "easy"

        # Check consolidation metadata
        assert result.metadata["consolidation"]["merged_from"] == [2, 3]
        assert "migrated_at" in result.metadata["consolidation"]

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_merge_contents_selects_longest(self, mock_engine_class, mock_pool):
        """Test content merging selects longest content."""
        mock_engine_class.return_value = AsyncMock()

        migration = ConsolidateDuplicateMemories.__new__(ConsolidateDuplicateMemories)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        contents = [
            "Short",
            "This is the longest content that should be selected for merging",
            "Medium length content",
        ]

        result = migration._merge_contents(contents)
        assert result == "This is the longest content that should be selected for merging"

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_merge_contents_single_content(self, mock_engine_class, mock_pool):
        """Test content merging with single content."""
        mock_engine_class.return_value = AsyncMock()

        migration = ConsolidateDuplicateMemories.__new__(ConsolidateDuplicateMemories)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        contents = ["Only one content"]

        result = migration._merge_contents(contents)
        assert result == "Only one content"


class TestMemoryDataMigrationIntegration:
    """Integration tests for key memory migration methods."""

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_create_bulk_config_validation_levels(self, mock_engine_class, mock_pool):
        """Test bulk config creation with different validation levels."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        # Test strict validation
        from app.bulk_memory_operations import ValidationLevel
        from app.migration_framework import MigrationConfig

        strict_config = MigrationConfig(
            validate_before=True,
            validate_after=True,
            batch_size=100,
            enable_rollback=True,
            parallel_execution=True,
            timeout_seconds=300,
        )

        with patch('app.bulk_memory_operations.BulkOperationConfig') as mock_config_class:
            _bulk_config = migration._create_bulk_config(strict_config)

            # Verify the call was made with correct parameters
            assert mock_config_class.called
            call_kwargs = mock_config_class.call_args[1]
            assert call_kwargs['validation_level'] == ValidationLevel.STRICT
            assert call_kwargs['parallel_workers'] == 4

    @patch('app.memory_migrations.BulkMemoryEngine')
    def test_create_bulk_config_minimal_validation(self, mock_engine_class, mock_pool):
        """Test bulk config creation with minimal validation."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        from app.bulk_memory_operations import ValidationLevel
        from app.migration_framework import MigrationConfig

        minimal_config = MigrationConfig(
            validate_before=False,
            validate_after=False,
            parallel_execution=False,
        )

        with patch('app.bulk_memory_operations.BulkOperationConfig') as mock_config_class:
            _bulk_config = migration._create_bulk_config(minimal_config)

            # Verify minimal validation and single worker
            call_kwargs = mock_config_class.call_args[1]
            assert call_kwargs['validation_level'] == ValidationLevel.MINIMAL
            assert call_kwargs['parallel_workers'] == 1

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_dry_run_migration_sample(self, mock_engine_class, mock_pool):
        """Test dry run migration samples first 5 memories."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        # Test with more than 5 memories to verify sampling
        memories = [
            {"id": i, "content": f"Memory {i}"}
            for i in range(10)
        ]

        result = await migration._dry_run_migration(memories)

        assert result["total_memories"] == 10
        assert len(result["sample_transforms"]) == 5  # Only first 5 sampled

    @patch('app.memory_migrations.BulkMemoryEngine')
    @pytest.mark.asyncio
    async def test_classification_types_comprehensive(self, mock_engine_class, mock_pool):
        """Test all memory type classifications comprehensively."""
        mock_engine_class.return_value = AsyncMock()

        migration = AddMemoryTypeClassification.__new__(AddMemoryTypeClassification)
        migration.pool = mock_pool
        migration.bulk_engine = AsyncMock()
        migration.processed_memory_ids = set()

        test_cases = [
            # Episodic memories
            ("I remember going to the store yesterday", "episodic"),
            ("When I was young, I did this", "episodic"),
            ("That happened last week", "episodic"),

            # Procedural memories
            ("How to tie your shoes: follow these steps", "procedural"),
            ("The process for making coffee", "procedural"),
            ("Procedure for starting the car", "procedural"),

            # Semantic memories (default)
            ("Paris is the capital of France", "semantic"),
            ("Mathematics is a science", "semantic"),
            ("The sky appears blue", "semantic"),
        ]

        for content, expected_type in test_cases:
            memory = {"id": 1, "content": content, "metadata": {}}
            result = await migration.transform_memory(memory)

            assert result.memory_type == expected_type, f"Failed for content: {content}"
            assert result.metadata["classification"]["type"] == expected_type
            assert result.metadata["classification"]["confidence"] == 0.85
