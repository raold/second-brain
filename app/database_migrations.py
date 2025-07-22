"""
Database Migration Implementations

Provides concrete implementations for database schema and data migrations
using the unified migration framework.
"""

import logging
from datetime import datetime
from typing import Any

import asyncpg

from .migration_framework import (
    Migration,
    MigrationConfig,
    MigrationMetadata,
    MigrationResult,
    MigrationStatus,
    MigrationType,
)

logger = logging.getLogger(__name__)


class DatabaseSchemaMigration(Migration):
    """Base class for database schema (DDL) migrations."""

    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.applied_statements = []
        super().__init__(self._get_metadata())

    def _get_metadata(self) -> MigrationMetadata:
        """Override to provide migration metadata."""
        raise NotImplementedError

    async def validate_preconditions(self) -> bool:
        """Check if schema changes can be applied."""
        try:
            async with self.pool.acquire() as conn:
                # Check database connection
                await conn.fetchval("SELECT 1")

                # Check for required extensions
                for extension in self.get_required_extensions():
                    exists = await conn.fetchval(
                        """
                        SELECT EXISTS(
                            SELECT 1 FROM pg_extension WHERE extname = $1
                        )
                    """,
                        extension,
                    )
                    if not exists:
                        logger.error(f"Required extension {extension} not found")
                        return False

                # Custom validation
                return await self._validate_custom_preconditions(conn)

        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False

    def get_required_extensions(self) -> list[str]:
        """List of required PostgreSQL extensions."""
        return []

    async def _validate_custom_preconditions(self, conn: asyncpg.Connection) -> bool:
        """Override for custom precondition checks."""
        return True

    async def apply(self, config: MigrationConfig) -> MigrationResult:
        """Apply schema changes."""
        start_time = datetime.now()
        errors = []
        affected_items = 0

        try:
            async with self.pool.acquire() as conn:
                # Start transaction if not dry run
                if not config.dry_run:
                    async with conn.transaction():
                        statements = await self.get_forward_statements()

                        for i, statement in enumerate(statements):
                            try:
                                if config.dry_run:
                                    logger.info(f"[DRY RUN] Would execute: {statement[:100]}...")
                                else:
                                    result = await conn.execute(statement)
                                    self.applied_statements.append(statement)

                                    # Parse affected rows if available
                                    if result and " " in result:
                                        parts = result.split(" ")
                                        if len(parts) > 1 and parts[1].isdigit():
                                            affected_items += int(parts[1])

                                # Checkpoint after each statement
                                if i % 10 == 0:
                                    self.set_checkpoint(
                                        {"last_statement_index": i, "applied_statements": len(self.applied_statements)}
                                    )

                            except Exception as e:
                                error = {"statement_index": i, "statement": statement[:100], "error": str(e)}
                                errors.append(error)

                                if not config.continue_on_error:
                                    raise

                status = MigrationStatus.COMPLETED if not errors else MigrationStatus.FAILED

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            status = MigrationStatus.FAILED
            errors.append({"error": str(e)})

        return MigrationResult(
            migration_id=self.metadata.id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            affected_items=affected_items,
            errors=errors,
            rollback_available=self.metadata.reversible,
            performance_metrics={
                "statements_executed": len(self.applied_statements),
                "total_statements": len(await self.get_forward_statements()),
            },
        )

    async def rollback(self) -> MigrationResult:
        """Rollback schema changes."""
        if not self.metadata.reversible:
            raise ValueError("Migration is not reversible")

        start_time = datetime.now()
        errors = []

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    statements = await self.get_rollback_statements()

                    for statement in statements:
                        try:
                            await conn.execute(statement)
                        except Exception as e:
                            errors.append({"statement": statement[:100], "error": str(e)})

            status = MigrationStatus.ROLLED_BACK if not errors else MigrationStatus.FAILED

        except Exception as e:
            status = MigrationStatus.FAILED
            errors.append({"error": str(e)})

        return MigrationResult(
            migration_id=self.metadata.id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            affected_items=0,
            errors=errors,
            rollback_available=False,
            performance_metrics={},
        )

    async def validate_postconditions(self) -> bool:
        """Validate schema changes were applied correctly."""
        try:
            async with self.pool.acquire() as conn:
                return await self._validate_custom_postconditions(conn)
        except Exception as e:
            logger.error(f"Postcondition validation failed: {e}")
            return False

    async def _validate_custom_postconditions(self, conn: asyncpg.Connection) -> bool:
        """Override for custom postcondition checks."""
        return True

    async def get_forward_statements(self) -> list[str]:
        """Get list of SQL statements to apply."""
        raise NotImplementedError

    async def get_rollback_statements(self) -> list[str]:
        """Get list of SQL statements to rollback."""
        raise NotImplementedError

    async def _estimate_changes(self) -> dict[str, int]:
        """Estimate number of schema objects affected."""
        statements = await self.get_forward_statements()

        # Count different types of operations
        creates = sum(1 for s in statements if "CREATE" in s.upper())
        alters = sum(1 for s in statements if "ALTER" in s.upper())
        drops = sum(1 for s in statements if "DROP" in s.upper())

        return {
            "estimated_items": len(statements),
            "create_operations": creates,
            "alter_operations": alters,
            "drop_operations": drops,
        }


class DatabaseDataMigration(Migration):
    """Base class for database data (DML) migrations."""

    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.processed_ids = set()
        super().__init__(self._get_metadata())

    def _get_metadata(self) -> MigrationMetadata:
        """Override to provide migration metadata."""
        raise NotImplementedError

    async def apply(self, config: MigrationConfig) -> MigrationResult:
        """Apply data changes in batches."""
        start_time = datetime.now()
        errors = []
        affected_items = 0

        try:
            # Get total count for progress tracking
            total_items = await self.get_total_items()

            # Process in batches
            offset = 0
            if self.checkpoint_data:
                offset = self.checkpoint_data.get("last_offset", 0)
                self.processed_ids = set(self.checkpoint_data.get("processed_ids", []))

            while True:
                async with self.pool.acquire() as conn:
                    # Get batch of items
                    items = await self.get_items_batch(conn, config.batch_size, offset)

                    if not items:
                        break

                    # Process batch in transaction
                    async with conn.transaction():
                        for item in items:
                            try:
                                if config.dry_run:
                                    logger.info(f"[DRY RUN] Would process item: {item.get('id')}")
                                else:
                                    await self.process_item(conn, item)
                                    self.processed_ids.add(str(item.get("id")))
                                    affected_items += 1

                            except Exception as e:
                                error = {"item_id": str(item.get("id")), "error": str(e)}
                                errors.append(error)

                                if not config.continue_on_error:
                                    raise

                    # Update checkpoint
                    offset += config.batch_size
                    if offset % config.checkpoint_frequency == 0:
                        self.set_checkpoint(
                            {
                                "last_offset": offset,
                                "processed_ids": list(self.processed_ids),
                                "affected_items": affected_items,
                            }
                        )

                        # Log progress
                        progress = (affected_items / total_items * 100) if total_items > 0 else 0
                        logger.info(f"Migration progress: {progress:.1f}% ({affected_items}/{total_items})")

                # Check timeout
                if (datetime.now() - start_time).total_seconds() > config.timeout_seconds:
                    logger.warning("Migration timeout reached")
                    break

            status = MigrationStatus.COMPLETED if not errors else MigrationStatus.FAILED

        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            status = MigrationStatus.FAILED
            errors.append({"error": str(e)})

        return MigrationResult(
            migration_id=self.metadata.id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            affected_items=affected_items,
            errors=errors,
            rollback_available=self.metadata.reversible,
            performance_metrics={
                "total_items": total_items,
                "items_per_second": affected_items / (datetime.now() - start_time).total_seconds(),
            },
            checkpoint_data=self.checkpoint_data,
        )

    async def get_total_items(self) -> int:
        """Get total number of items to process."""
        raise NotImplementedError

    async def get_items_batch(self, conn: asyncpg.Connection, batch_size: int, offset: int) -> list[dict[str, Any]]:
        """Get batch of items to process."""
        raise NotImplementedError

    async def process_item(self, conn: asyncpg.Connection, item: dict[str, Any]):
        """Process a single item."""
        raise NotImplementedError


# Example concrete migration
class AddImportanceScoreToMemories(DatabaseSchemaMigration):
    """Migration to add importance scoring to memories table."""

    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="add_importance_score_001",
            name="Add importance score to memories",
            description="Adds importance_score column for memory ranking",
            version="2.8.1",
            migration_type=MigrationType.DATABASE_SCHEMA,
            author="system",
            created_at=datetime.now(),
            dependencies=[],
            reversible=True,
            checksum="a1b2c3d4e5f6",
        )

    async def get_forward_statements(self) -> list[str]:
        return [
            """
            ALTER TABLE memories
            ADD COLUMN IF NOT EXISTS importance_score DECIMAL(5,4) DEFAULT 0.5
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_memories_importance
            ON memories(importance_score DESC)
            """,
        ]

    async def get_rollback_statements(self) -> list[str]:
        return [
            "DROP INDEX IF EXISTS idx_memories_importance",
            "ALTER TABLE memories DROP COLUMN IF EXISTS importance_score",
        ]

    async def _validate_custom_postconditions(self, conn: asyncpg.Connection) -> bool:
        """Check that column was added successfully."""
        exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'memories'
                AND column_name = 'importance_score'
            )
        """)
        return bool(exists)
