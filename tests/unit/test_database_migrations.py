"""Test database migrations - working version."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.database_migrations import AddImportanceScoreToMemories


class TestDatabaseMigrationsWorking:
    """Working database migration tests for coverage."""

    def test_migration_metadata(self):
        """Test migration metadata is properly configured."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        assert migration.metadata.id == "add_importance_score_001"
        assert migration.metadata.name == "Add importance score to memories"
        assert migration.metadata.reversible is True
        assert migration.metadata.author == "system"
        assert migration.metadata.version == "2.5.0"

    @pytest.mark.asyncio
    async def test_get_forward_statements(self):
        """Test forward migration statements."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        statements = await migration.get_forward_statements()

        assert len(statements) == 2
        assert any("importance_score" in stmt and "ADD COLUMN" in stmt for stmt in statements)
        assert any("idx_memories_importance" in stmt and "CREATE INDEX" in stmt for stmt in statements)

    @pytest.mark.asyncio
    async def test_get_rollback_statements(self):
        """Test rollback migration statements."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        statements = await migration.get_rollback_statements()

        assert len(statements) == 2
        assert any("DROP INDEX" in stmt for stmt in statements)
        assert any("DROP COLUMN" in stmt for stmt in statements)

    def test_migration_metadata_properties(self):
        """Test all migration metadata properties."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        # Test all required metadata fields are present
        assert hasattr(migration.metadata, 'id')
        assert hasattr(migration.metadata, 'name')
        assert hasattr(migration.metadata, 'description')
        assert hasattr(migration.metadata, 'version')
        assert hasattr(migration.metadata, 'migration_type')
        assert hasattr(migration.metadata, 'author')
        assert hasattr(migration.metadata, 'created_at')
        assert hasattr(migration.metadata, 'dependencies')
        assert hasattr(migration.metadata, 'reversible')
        assert hasattr(migration.metadata, 'checksum')

    def test_required_extensions(self):
        """Test required extensions check."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        extensions = migration.get_required_extensions()
        assert isinstance(extensions, list)
        assert len(extensions) == 0  # No special extensions required

    def test_migration_inheritance(self):
        """Test migration inheritance structure."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        # Test inheritance
        from app.database_migrations import DatabaseSchemaMigration
        assert isinstance(migration, DatabaseSchemaMigration)

        # Test metadata type
        from app.migration_framework import MigrationMetadata, MigrationType
        assert isinstance(migration.metadata, MigrationMetadata)
        assert migration.metadata.migration_type == MigrationType.DATABASE_SCHEMA

    def test_applied_statements_tracking(self):
        """Test applied statements tracking functionality."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        # Test initial state
        assert hasattr(migration, 'applied_statements')
        assert isinstance(migration.applied_statements, list)
        assert len(migration.applied_statements) == 0

    @pytest.mark.asyncio
    async def test_get_statements_content(self):
        """Test the actual content of migration statements."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        # Test forward statements
        forward_statements = await migration.get_forward_statements()
        assert "DECIMAL(5,4)" in forward_statements[0]
        assert "DEFAULT 0.5" in forward_statements[0]
        assert "importance_score DESC" in forward_statements[1]

        # Test rollback statements
        rollback_statements = await migration.get_rollback_statements()
        assert "idx_memories_importance" in rollback_statements[0]
        assert "importance_score" in rollback_statements[1]

    def test_migration_checksum_uniqueness(self):
        """Test migration checksum is properly set."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        assert migration.metadata.checksum == "a1b2c3d4e5f6"
        assert len(migration.metadata.checksum) > 0

    def test_migration_dependencies(self):
        """Test migration dependencies configuration."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        assert isinstance(migration.metadata.dependencies, list)
        assert len(migration.metadata.dependencies) == 0  # No dependencies for this migration

    def test_migration_description(self):
        """Test migration description is informative."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        description = migration.metadata.description
        assert "importance_score" in description
        assert "column" in description
        assert "ranking" in description

    def test_migration_creation_time(self):
        """Test migration created_at timestamp."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        assert isinstance(migration.metadata.created_at, datetime)
        # Should be recent (within last day)
        assert (datetime.now() - migration.metadata.created_at).days < 1

    def test_migration_pool_assignment(self):
        """Test database pool assignment."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        assert migration.pool is mock_pool

    @pytest.mark.asyncio
    async def test_custom_precondition_validation(self):
        """Test custom precondition validation."""
        mock_pool = AsyncMock()
        migration = AddImportanceScoreToMemories(mock_pool)

        # Test method exists
        assert hasattr(migration, '_validate_custom_preconditions')

        # Mock connection
        mock_conn = AsyncMock()
        result = await migration._validate_custom_preconditions(mock_conn)
        assert result is True  # Default implementation returns True
