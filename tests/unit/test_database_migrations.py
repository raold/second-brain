"""
Test suite for database migrations module.
Tests the comprehensive database migration system with schema and data migrations.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.database_migrations import (
    AddImportanceScoreToMemories,
    DatabaseSchemaMigration,
)
from app.migration_framework import (
    MigrationConfig,
    MigrationMetadata,
    MigrationResult,
    MigrationStatus,
    MigrationType,
)


class TestDatabaseSchemaMigration:
    """Test DatabaseSchemaMigration base class."""

    def setup_method(self):
        self.mock_pool = AsyncMock()
        self.mock_conn = AsyncMock()
        self.mock_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.mock_pool.acquire.return_value.__aexit__.return_value = None

    def test_init_requires_metadata_override(self):
        """Test that initialization requires metadata override."""
        with pytest.raises(NotImplementedError):
            DatabaseSchemaMigration(self.mock_pool)

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self):
        """Test successful precondition validation."""
        # Create a concrete implementation
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration",
                    name="Test Migration",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="test_checksum"
                )

            def get_required_extensions(self):
                return ["vector"]

            async def _validate_custom_preconditions(self, conn):
                return True

            async def get_forward_statements(self):
                return ["CREATE TABLE test (id SERIAL PRIMARY KEY);"]

            async def get_rollback_statements(self):
                return ["DROP TABLE test;"]

        migration = TestMigration(self.mock_pool)

        # Mock database responses
        self.mock_conn.fetchval.side_effect = [1, True]  # Connection check, extension exists

        result = await migration.validate_preconditions()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_preconditions_missing_extension(self):
        """Test precondition validation with missing extension."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration_2",
                    name="Test Migration 2",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="test_checksum_2"
                )

            def get_required_extensions(self):
                return ["missing_extension"]

            async def get_forward_statements(self):
                return ["CREATE TABLE test (id SERIAL PRIMARY KEY);"]

        migration = TestMigration(self.mock_pool)

        # Mock extension not found
        self.mock_conn.fetchval.side_effect = [1, False]

        result = await migration.validate_preconditions()
        assert result is False

    @pytest.mark.asyncio
    async def test_apply_migration_success(self):
        """Test successful migration application."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration_3",
                    name="Test Migration 3",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="test_checksum_3"
                )

            async def get_forward_statements(self):
                return [
                    "CREATE TABLE test (id SERIAL PRIMARY KEY);",
                    "CREATE INDEX idx_test_id ON test(id);"
                ]

            async def get_rollback_statements(self):
                return ["DROP TABLE test;"]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        # Mock transaction and execution
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock successful execution
        self.mock_conn.execute.return_value = "CREATE TABLE 1"

        result = await migration.apply(config)

        assert isinstance(result, MigrationResult)
        assert result.migration_id == "test_migration_3"
        assert result.status == MigrationStatus.COMPLETED
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_apply_migration_dry_run(self):
        """Test migration dry run mode."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration_4",
                    name="Test Migration 4",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="test_checksum_4"
                )

            async def get_forward_statements(self):
                return ["CREATE TABLE test (id SERIAL PRIMARY KEY);"]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=True)

        result = await migration.apply(config)

        assert result.status == MigrationStatus.COMPLETED
        # Should not execute statements in dry run
        self.mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_migration_success(self):
        """Test successful migration rollback."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration_5",
                    name="Test Migration 5",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="test_checksum_5"
                )

            async def get_rollback_statements(self):
                return ["DROP TABLE test;"]

        migration = TestMigration(self.mock_pool)

        # Mock transaction and execution
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock successful rollback
        self.mock_conn.execute.return_value = "DROP TABLE"

        result = await migration.rollback()

        assert isinstance(result, MigrationResult)
        assert result.status == MigrationStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_non_reversible_migration(self):
        """Test rollback of non-reversible migration."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="test_migration_6",
                    name="Test Migration 6",
                    description="Test migration",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=False,
                    checksum="test_checksum_6"
                )

        migration = TestMigration(self.mock_pool)

        with pytest.raises(ValueError, match="Migration is not reversible"):
            await migration.rollback()


class TestAddImportanceScoreToMemories:
    """Test AddImportanceScoreToMemories concrete migration."""

    def setup_method(self):
        self.mock_pool = AsyncMock()
        self.mock_conn = AsyncMock()
        self.mock_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.mock_pool.acquire.return_value.__aexit__.return_value = None

    def test_migration_metadata(self):
        """Test migration metadata is properly configured."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        assert migration.metadata.id == "add_importance_score_001"
        assert migration.metadata.name == "Add importance score to memories"
        assert migration.metadata.migration_type == MigrationType.DATABASE_SCHEMA
        assert migration.metadata.reversible is True

    @pytest.mark.asyncio
    async def test_get_forward_statements(self):
        """Test forward migration statements."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        statements = await migration.get_forward_statements()

        assert len(statements) == 2
        assert any("importance_score" in stmt and "ADD COLUMN" in stmt for stmt in statements)
        assert any("idx_memories_importance" in stmt and "CREATE INDEX" in stmt for stmt in statements)

    @pytest.mark.asyncio
    async def test_get_rollback_statements(self):
        """Test rollback migration statements."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        statements = await migration.get_rollback_statements()

        assert len(statements) == 2
        assert any("DROP INDEX" in stmt for stmt in statements)
        assert any("DROP COLUMN" in stmt for stmt in statements)

    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self):
        """Test successful precondition validation."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        # Mock database check - no extensions required
        self.mock_conn.fetchval.return_value = 1

        result = await migration.validate_preconditions()
        assert result is True

    @pytest.mark.asyncio
    async def test_apply_migration_complete_flow(self):
        """Test complete migration application flow."""
        migration = AddImportanceScoreToMemories(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        # Mock transaction and execution
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock successful execution
        self.mock_conn.execute.return_value = "ALTER TABLE"

        result = await migration.apply(config)

        assert result.status == MigrationStatus.COMPLETED
        assert result.migration_id == "add_importance_score_001"

    @pytest.mark.asyncio
    async def test_rollback_migration_complete_flow(self):
        """Test complete migration rollback flow."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        # Mock transaction and execution
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock successful rollback
        self.mock_conn.execute.return_value = "DROP INDEX"

        result = await migration.rollback()

        assert result.status == MigrationStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_validate_postconditions(self):
        """Test postcondition validation."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        # Mock column exists check
        self.mock_conn.fetchval.return_value = True

        result = await migration.validate_postconditions()
        assert result is True


class TestMigrationEdgeCases:
    """Test migration edge cases and error scenarios."""

    def setup_method(self):
        self.mock_pool = AsyncMock()
        self.mock_conn = AsyncMock()
        self.mock_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.mock_pool.acquire.return_value.__aexit__.return_value = None

    @pytest.mark.asyncio
    async def test_migration_with_errors_continue_on_error(self):
        """Test migration with execution errors and continue_on_error=True."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="error_recovery_test",
                    name="Error Recovery Test",
                    description="Test error recovery",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="error_test_checksum"
                )

            async def get_forward_statements(self):
                return [
                    "CREATE TABLE valid_table (id SERIAL);",
                    "INVALID SQL STATEMENT;",
                    "CREATE TABLE another_table (id SERIAL);"
                ]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False, continue_on_error=True)

        # Mock transaction
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock mixed success/failure
        self.mock_conn.execute.side_effect = [
            "CREATE TABLE",
            Exception("SQL Error"),
            "CREATE TABLE"
        ]

        result = await migration.apply(config)

        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) == 1
        assert "SQL Error" in str(result.errors[0])

    @pytest.mark.asyncio
    async def test_migration_with_errors_stop_on_error(self):
        """Test migration with execution errors and continue_on_error=False."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="stop_on_error_test",
                    name="Stop on Error Test",
                    description="Test stop on error",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="stop_error_checksum"
                )

            async def get_forward_statements(self):
                return [
                    "CREATE TABLE valid_table (id SERIAL);",
                    "INVALID SQL STATEMENT;"
                ]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False, continue_on_error=False)

        # Mock transaction
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock first success, second failure
        self.mock_conn.execute.side_effect = [
            "CREATE TABLE",
            Exception("SQL Error")
        ]

        result = await migration.apply(config)

        assert result.status == MigrationStatus.FAILED

    @pytest.mark.asyncio
    async def test_migration_checkpoint_functionality(self):
        """Test migration checkpoint system."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="checkpoint_test",
                    name="Checkpoint Test",
                    description="Test checkpointing",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="checkpoint_checksum"
                )

            async def get_forward_statements(self):
                # Return many statements to trigger checkpointing
                return [f"CREATE TABLE test_{i} (id SERIAL);" for i in range(25)]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        # Mock transaction
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock successful execution
        self.mock_conn.execute.return_value = "CREATE TABLE"

        result = await migration.apply(config)

        assert result.status == MigrationStatus.COMPLETED
        assert result.performance_metrics["statements_executed"] == 25

    @pytest.mark.asyncio
    async def test_migration_performance_metrics(self):
        """Test migration performance metrics collection."""
        migration = AddImportanceScoreToMemories(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        # Mock transaction
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock execution with timing
        self.mock_conn.execute.return_value = "ALTER TABLE"

        result = await migration.apply(config)

        assert "statements_executed" in result.performance_metrics
        assert "total_statements" in result.performance_metrics
        assert result.end_time is not None
        assert result.start_time is not None
        if result.end_time and result.start_time:
            assert result.end_time >= result.start_time

    @pytest.mark.asyncio
    async def test_required_extensions_check(self):
        """Test required extensions validation."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        # Test that this migration doesn't require special extensions
        extensions = migration.get_required_extensions()
        assert isinstance(extensions, list)
        assert len(extensions) == 0

    @pytest.mark.asyncio
    async def test_validate_preconditions_connection_error(self):
        """Test precondition validation with connection error."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

        # Mock connection error
        self.mock_conn.fetchval.side_effect = Exception("Connection failed")

        result = await migration.validate_preconditions()
        assert result is False

    def test_migration_metadata_immutability(self):
        """Test that migration metadata is properly set and immutable."""
        migration = AddImportanceScoreToMemories(self.mock_pool)

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

    @pytest.mark.asyncio
    async def test_empty_statements_handling(self):
        """Test handling of migrations with no statements."""
        class EmptyMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="empty_migration",
                    name="Empty Migration",
                    description="Migration with no statements",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="empty_checksum"
                )

            async def get_forward_statements(self):
                return []

        migration = EmptyMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        result = await migration.apply(config)

        assert result.status == MigrationStatus.COMPLETED
        assert result.affected_items == 0
        assert result.performance_metrics["statements_executed"] == 0

    @pytest.mark.asyncio
    async def test_migration_statement_parsing(self):
        """Test SQL statement result parsing for affected rows."""
        class TestMigration(DatabaseSchemaMigration):
            def _get_metadata(self):
                return MigrationMetadata(
                    id="parse_test",
                    name="Parse Test",
                    description="Test statement parsing",
                    version="1.0.0",
                    migration_type=MigrationType.DATABASE_SCHEMA,
                    author="test_author",
                    created_at=datetime.now(),
                    dependencies=[],
                    reversible=True,
                    checksum="parse_checksum"
                )

            async def get_forward_statements(self):
                return ["UPDATE table SET col = 1;"]

        migration = TestMigration(self.mock_pool)
        config = MigrationConfig(dry_run=False)

        # Mock transaction
        mock_transaction = AsyncMock()
        self.mock_conn.transaction.return_value = mock_transaction
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None

        # Mock UPDATE result with affected rows
        self.mock_conn.execute.return_value = "UPDATE 5"

        result = await migration.apply(config)

        assert result.status == MigrationStatus.COMPLETED
        assert result.affected_items == 5
