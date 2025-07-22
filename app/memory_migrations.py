"""
Memory Migration Implementations

Provides concrete implementations for memory data migrations
using the unified migration framework with bulk operations integration.
"""

import logging
from datetime import datetime
from typing import Any

import asyncpg

from .bulk_memory_operations import (
    BulkMemoryEngine,
    BulkMemoryItem,
)
from .bulk_memory_operations import (
    ValidationLevel as BulkValidationLevel,
)
from .migration_framework import (
    Migration,
    MigrationConfig,
    MigrationMetadata,
    MigrationResult,
    MigrationStatus,
    MigrationType,
)

logger = logging.getLogger(__name__)


class MemoryDataMigration(Migration):
    """Base class for memory data migrations using bulk operations."""

    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.bulk_engine = BulkMemoryEngine(connection_pool)
        self.processed_memory_ids = set()
        super().__init__(self._get_metadata())

    def _get_metadata(self) -> MigrationMetadata:
        """Override to provide migration metadata."""
        raise NotImplementedError

    async def validate_preconditions(self) -> bool:
        """Validate migration can be applied."""
        try:
            # Check database connection
            if hasattr(self.pool, "fetchval"):
                await self.pool.fetchval("SELECT 1")

            # Custom validation
            return await self._validate_custom_preconditions()

        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return False

    async def _validate_custom_preconditions(self) -> bool:
        """Override for custom precondition checks."""
        return True

    async def apply(self, config: MigrationConfig) -> MigrationResult:
        """Apply memory migration using bulk operations."""
        start_time = datetime.now()

        try:
            # Prepare bulk operation config
            bulk_config = self._create_bulk_config(config)

            # Get memories to migrate
            memories_to_migrate = await self.get_memories_to_migrate()

            if config.dry_run:
                # Simulate migration
                result = await self._dry_run_migration(memories_to_migrate)
                return MigrationResult(
                    migration_id=self.metadata.id,
                    status=MigrationStatus.COMPLETED,
                    start_time=start_time,
                    end_time=datetime.now(),
                    affected_items=len(memories_to_migrate),
                    errors=[],
                    rollback_available=False,
                    performance_metrics={"dry_run": True},
                )

            # Transform memories
            transformed_memories = []
            errors = []

            for memory in memories_to_migrate:
                try:
                    transformed = await self.transform_memory(memory)
                    if transformed:
                        transformed_memories.append(transformed)
                        self.processed_memory_ids.add(memory["id"])
                except Exception as e:
                    errors.append({"memory_id": str(memory.get("id")), "error": str(e)})
                    if not config.continue_on_error:
                        raise

            # Apply bulk update
            if transformed_memories:
                bulk_result = await self.bulk_engine.bulk_insert_memories(transformed_memories, bulk_config)

                # Merge results
                affected_items = bulk_result.successful_items
                if bulk_result.error_summary:
                    for error_type, count in bulk_result.error_summary.items():
                        errors.append({"error_type": error_type, "count": count})
            else:
                affected_items = 0

            status = MigrationStatus.COMPLETED if not errors else MigrationStatus.FAILED

        except Exception as e:
            logger.error(f"Memory migration failed: {e}")
            status = MigrationStatus.FAILED
            errors = [{"error": str(e)}]
            affected_items = 0

        return MigrationResult(
            migration_id=self.metadata.id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            affected_items=affected_items,
            errors=errors,
            rollback_available=self.metadata.reversible,
            performance_metrics={
                "memories_processed": len(self.processed_memory_ids),
                "transformation_rate": len(self.processed_memory_ids) / (datetime.now() - start_time).total_seconds(),
            },
            checkpoint_data={"processed_ids": list(self.processed_memory_ids)},
        )

    async def rollback(self) -> MigrationResult:
        """Rollback memory changes if possible."""
        if not self.metadata.reversible:
            raise ValueError("Migration is not reversible")

        start_time = datetime.now()
        errors = []

        try:
            # Get original memories from backup
            original_memories = await self.get_original_memories()

            # Restore using bulk operations
            bulk_config = self._create_bulk_config(MigrationConfig())
            bulk_result = await self.bulk_engine.bulk_insert_memories(original_memories, bulk_config)

            status = MigrationStatus.ROLLED_BACK
            affected_items = bulk_result.successful_items
            if bulk_result.error_summary:
                for error_type, count in bulk_result.error_summary.items():
                    errors.append({"error_type": error_type, "count": count})

        except Exception as e:
            status = MigrationStatus.FAILED
            errors = [{"error": str(e)}]
            affected_items = 0

        return MigrationResult(
            migration_id=self.metadata.id,
            status=status,
            start_time=start_time,
            end_time=datetime.now(),
            affected_items=affected_items,
            errors=errors,
            rollback_available=False,
            performance_metrics={},
        )

    def _create_bulk_config(self, migration_config: MigrationConfig):
        """Create bulk operation config from migration config."""
        from .bulk_memory_operations import BulkOperationConfig

        # Map validation levels
        if migration_config.validate_before and migration_config.validate_after:
            validation_level = BulkValidationLevel.STRICT
        elif migration_config.validate_before or migration_config.validate_after:
            validation_level = BulkValidationLevel.STANDARD
        else:
            validation_level = BulkValidationLevel.MINIMAL

        return BulkOperationConfig(
            batch_size=migration_config.batch_size,
            validation_level=validation_level,
            enable_rollback=migration_config.enable_rollback,
            parallel_workers=4 if migration_config.parallel_execution else 1,
            timeout_seconds=migration_config.timeout_seconds,
        )

    async def get_memories_to_migrate(self) -> list[dict[str, Any]]:
        """Get list of memories that need migration."""
        raise NotImplementedError

    async def transform_memory(self, memory: dict[str, Any]) -> BulkMemoryItem | None:
        """Transform a memory according to migration rules."""
        raise NotImplementedError

    async def get_original_memories(self) -> list[BulkMemoryItem]:
        """Get original memories for rollback."""
        raise NotImplementedError

    async def _dry_run_migration(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Simulate migration without changes."""
        sample_transforms = []

        # Transform a sample
        for memory in memories[:5]:  # Sample first 5
            try:
                transformed = await self.transform_memory(memory)
                sample_transforms.append({"original": memory, "transformed": transformed})
            except Exception as e:
                sample_transforms.append({"original": memory, "error": str(e)})

        return {"total_memories": len(memories), "sample_transforms": sample_transforms}


class MemoryStructureMigration(Migration):
    """Base class for memory structure/schema migrations."""

    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        super().__init__(self._get_metadata())

    def _get_metadata(self) -> MigrationMetadata:
        """Override to provide migration metadata."""
        raise NotImplementedError

    async def validate_preconditions(self) -> bool:
        """Check if structure changes can be applied."""
        try:
            async with self.pool.acquire() as conn:
                # Verify current structure
                current_structure = await self.get_current_structure(conn)
                expected_structure = await self.get_expected_structure()

                # Check compatibility
                return self.check_structure_compatibility(current_structure, expected_structure)

        except Exception as e:
            logger.error(f"Structure validation failed: {e}")
            return False

    async def get_current_structure(self, conn: asyncpg.Connection) -> dict[str, Any]:
        """Get current memory structure/schema."""
        raise NotImplementedError

    async def get_expected_structure(self) -> dict[str, Any]:
        """Get expected structure before migration."""
        raise NotImplementedError

    def check_structure_compatibility(self, current: dict[str, Any], expected: dict[str, Any]) -> bool:
        """Check if structures are compatible."""
        return True  # Override for specific checks


# Example concrete migrations
class AddMemoryTypeClassification(MemoryDataMigration):
    """Migration to classify existing memories by type."""

    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="classify_memory_types_001",
            name="Classify memories by cognitive type",
            description="Analyzes and classifies existing memories as semantic, episodic, or procedural",
            version="2.5.0",
            migration_type=MigrationType.MEMORY_DATA,
            author="system",
            created_at=datetime.now(),
            dependencies=[],
            reversible=True,
            checksum="b2c3d4e5f6g7",
        )

    async def get_memories_to_migrate(self) -> list[dict[str, Any]]:
        """Get memories without type classification."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, metadata
                FROM memories
                WHERE memory_type IS NULL
                OR memory_type = 'semantic'  -- Re-classify default semantic
                ORDER BY created_at
            """)
            return [dict(row) for row in rows]

    async def transform_memory(self, memory: dict[str, Any]) -> BulkMemoryItem | None:
        """Classify memory type based on content analysis."""
        # Simple classification based on content patterns
        content = memory["content"].lower()

        if any(word in content for word in ["remember", "happened", "was", "did"]):
            memory_type = "episodic"
        elif any(word in content for word in ["how to", "steps", "process", "procedure"]):
            memory_type = "procedural"
        else:
            memory_type = "semantic"

        # Update metadata with classification confidence
        metadata = memory.get("metadata", {})
        metadata["classification"] = {
            "type": memory_type,
            "confidence": 0.85,
            "migrated_at": datetime.now().isoformat(),
        }

        return BulkMemoryItem(
            memory_id=memory["id"], content=memory["content"], metadata=metadata, memory_type=memory_type
        )

    async def get_original_memories(self) -> list[BulkMemoryItem]:
        """Get original memories for rollback."""
        # In real implementation, would restore from backup
        return []

    async def validate_postconditions(self) -> bool:
        """Validate that classification migration was applied correctly."""
        try:
            # Check that some memories have been classified
            async with self.pool.acquire() as conn:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM memories
                    WHERE memory_type IN ('episodic', 'procedural', 'semantic')
                    AND metadata->>'classification' IS NOT NULL
                """)
                return count > 0
        except Exception:
            return False


class ConsolidateDuplicateMemories(MemoryDataMigration):
    """Migration to consolidate duplicate or similar memories."""

    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="consolidate_duplicates_001",
            name="Consolidate duplicate memories",
            description="Identifies and merges duplicate or highly similar memories",
            version="2.5.1",
            migration_type=MigrationType.MEMORY_DATA,
            author="system",
            created_at=datetime.now(),
            dependencies=["classify_memory_types_001"],
            reversible=True,
            checksum="c3d4e5f6g7h8",
        )

    async def get_memories_to_migrate(self) -> list[dict[str, Any]]:
        """Find potential duplicate memories."""
        async with self.pool.acquire() as conn:
            # Use vector similarity to find potential duplicates
            rows = await conn.fetch("""
                WITH similarity_pairs AS (
                    SELECT
                        m1.id as id1,
                        m2.id as id2,
                        m1.content as content1,
                        m2.content as content2,
                        m1.metadata as metadata1,
                        m2.metadata as metadata2,
                        1 - (m1.embedding <=> m2.embedding) as similarity
                    FROM memories m1
                    JOIN memories m2 ON m1.id < m2.id
                    WHERE 1 - (m1.embedding <=> m2.embedding) > 0.95
                )
                SELECT * FROM similarity_pairs
                ORDER BY similarity DESC
            """)

            # Group duplicates
            duplicate_groups = []
            processed = set()

            for row in rows:
                if row["id1"] not in processed:
                    group = {
                        "primary_id": row["id1"],
                        "duplicate_ids": [row["id2"]],
                        "contents": [row["content1"], row["content2"]],
                        "metadatas": [row["metadata1"], row["metadata2"]],
                    }
                    processed.add(row["id1"])
                    processed.add(row["id2"])
                    duplicate_groups.append(group)

            return duplicate_groups

    async def transform_memory(self, memory_group: dict[str, Any]) -> BulkMemoryItem | None:
        """Consolidate duplicate memories into one."""
        # Merge contents intelligently
        merged_content = self._merge_contents(memory_group["contents"])

        # Merge metadata
        merged_metadata = {}
        for metadata in memory_group["metadatas"]:
            if metadata:
                merged_metadata.update(metadata)

        merged_metadata["consolidation"] = {
            "merged_from": memory_group["duplicate_ids"],
            "migrated_at": datetime.now().isoformat(),
        }

        return BulkMemoryItem(memory_id=memory_group["primary_id"], content=merged_content, metadata=merged_metadata)

    def _merge_contents(self, contents: list[str]) -> str:
        """Intelligently merge similar contents."""
        # Simple implementation - take longest content
        # Real implementation would use NLP to merge intelligently
        return max(contents, key=len)

    async def get_original_memories(self) -> list[BulkMemoryItem]:
        """Get original memories for rollback."""
        # In real implementation, would restore from backup
        return []

    async def validate_postconditions(self) -> bool:
        """Validate that consolidation migration was applied correctly."""
        try:
            # Check that some duplicate groups have been processed
            return len(self.processed_memory_ids) > 0
        except Exception:
            return False
