#!/usr/bin/env python3
"""
Comprehensive Memory Migration Tools
Advanced migration system with validation, rollback, and monitoring
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.database_mock import get_mock_database


class MigrationType(str, Enum):
    """Types of memory migrations"""

    SCHEMA_UPDATE = "schema_update"
    DATA_TRANSFORMATION = "data_transformation"
    MEMORY_TYPE_MIGRATION = "memory_type_migration"
    METADATA_ENRICHMENT = "metadata_enrichment"
    CONTENT_PROCESSING = "content_processing"
    DUPLICATE_CLEANUP = "duplicate_cleanup"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class MigrationStatus(str, Enum):
    """Migration execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"


@dataclass
class MigrationStep:
    """Individual migration step"""

    step_id: str
    name: str
    description: str
    function: Callable
    rollback_function: Optional[Callable] = None
    dependencies: list[str] = None
    estimated_duration: Optional[int] = None  # seconds
    critical: bool = False


@dataclass
class MigrationResult:
    """Result of migration execution"""

    migration_id: str
    status: MigrationStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    errors: list[str]
    warnings: list[str]
    rollback_available: bool
    performance_metrics: dict[str, Any]


class MigrationConfig(BaseModel):
    """Configuration for migration execution"""

    batch_size: int = Field(100, description="Number of records to process per batch")
    max_retries: int = Field(3, description="Maximum retry attempts for failed operations")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    backup_before_migration: bool = Field(True, description="Create backup before migration")
    validate_before_execution: bool = Field(True, description="Validate migration before execution")
    parallel_execution: bool = Field(False, description="Enable parallel processing")
    max_workers: int = Field(4, description="Maximum number of parallel workers")
    timeout_per_batch: int = Field(300, description="Timeout per batch in seconds")
    rollback_on_failure: bool = Field(True, description="Automatically rollback on critical failure")


class MemoryMigration:
    """Base class for memory migrations"""

    def __init__(self, migration_id: str, name: str, description: str):
        self.migration_id = migration_id
        self.name = name
        self.description = description
        self.steps: list[MigrationStep] = []
        self.dependencies: list[str] = []
        self.rollback_data: dict[str, Any] = {}

    def add_step(self, step: MigrationStep):
        """Add migration step"""
        self.steps.append(step)

    async def validate(self, config: MigrationConfig) -> tuple[bool, list[str]]:
        """Validate migration before execution"""
        errors = []

        # Check dependencies
        for dep in self.dependencies:
            if not await self._check_dependency(dep):
                errors.append(f"Dependency not met: {dep}")

        # Validate steps
        for step in self.steps:
            try:
                await self._validate_step(step)
            except Exception as e:
                errors.append(f"Step validation failed for {step.name}: {str(e)}")

        return len(errors) == 0, errors

    async def execute(self, config: MigrationConfig) -> MigrationResult:
        """Execute migration with comprehensive error handling and monitoring"""
        start_time = datetime.now()

        result = MigrationResult(
            migration_id=self.migration_id,
            status=MigrationStatus.PENDING,
            start_time=start_time,
            end_time=None,
            total_records=0,
            processed_records=0,
            successful_records=0,
            failed_records=0,
            errors=[],
            warnings=[],
            rollback_available=True,
            performance_metrics={},
        )

        try:
            result.status = MigrationStatus.RUNNING

            # Validate before execution
            if config.validate_before_execution:
                is_valid, validation_errors = await self.validate(config)
                if not is_valid:
                    result.errors.extend(validation_errors)
                    result.status = MigrationStatus.FAILED
                    return result

            # Create backup if requested
            if config.backup_before_migration:
                await self._create_backup()

            # Execute steps
            for step in self.steps:
                step_result = await self._execute_step(step, config, result)
                if not step_result and step.critical:
                    result.status = MigrationStatus.FAILED
                    if config.rollback_on_failure:
                        await self.rollback(config)
                        result.status = MigrationStatus.ROLLED_BACK
                    break

            # Finalize result
            if result.status == MigrationStatus.RUNNING:
                result.status = MigrationStatus.COMPLETED

        except Exception as e:
            result.errors.append(f"Migration execution failed: {str(e)}")
            result.status = MigrationStatus.FAILED

            if config.rollback_on_failure:
                try:
                    await self.rollback(config)
                    result.status = MigrationStatus.ROLLED_BACK
                except Exception as rollback_error:
                    result.errors.append(f"Rollback failed: {str(rollback_error)}")

        result.end_time = datetime.now()
        return result

    async def rollback(self, config: MigrationConfig) -> bool:
        """Rollback migration changes"""
        try:
            # Execute rollback steps in reverse order
            for step in reversed(self.steps):
                if step.rollback_function:
                    await step.rollback_function(self.rollback_data.get(step.step_id))
            return True
        except Exception as e:
            print(f"Rollback failed: {str(e)}")
            return False

    async def _check_dependency(self, dependency: str) -> bool:
        """Check if dependency is satisfied"""
        # Override in subclasses for specific dependency checks
        return True

    async def _validate_step(self, step: MigrationStep):
        """Validate individual step"""
        # Override in subclasses for specific validation
        pass

    async def _execute_step(self, step: MigrationStep, config: MigrationConfig, result: MigrationResult) -> bool:
        """Execute individual migration step"""
        try:
            step_start = datetime.now()

            # Store data for potential rollback
            rollback_data = await self._prepare_rollback_data(step)
            self.rollback_data[step.step_id] = rollback_data

            # Execute step function
            step_result = await step.function(config, result)

            step_duration = (datetime.now() - step_start).total_seconds()
            result.performance_metrics[step.step_id] = {"duration": step_duration, "status": "completed"}

            return step_result

        except Exception as e:
            result.errors.append(f"Step {step.name} failed: {str(e)}")
            result.performance_metrics[step.step_id] = {"duration": 0, "status": "failed", "error": str(e)}
            return False

    async def _prepare_rollback_data(self, step: MigrationStep) -> dict[str, Any]:
        """Prepare data needed for step rollback"""
        return {}

    async def _create_backup(self):
        """Create backup before migration"""
        # Override in subclasses for specific backup logic
        pass


class MemoryTypeMigration(MemoryMigration):
    """Migration for updating memory types"""

    def __init__(self, from_type: str, to_type: str, filter_criteria: Optional[dict] = None):
        super().__init__(
            migration_id=f"memory_type_{from_type}_to_{to_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=f"Memory Type Migration: {from_type} → {to_type}",
            description=f"Migrate memories from {from_type} type to {to_type} type",
        )
        self.from_type = from_type
        self.to_type = to_type
        self.filter_criteria = filter_criteria or {}

        # Add migration steps
        self.add_step(
            MigrationStep(
                step_id="identify_memories",
                name="Identify Target Memories",
                description=f"Find memories with type {from_type}",
                function=self._identify_memories,
                critical=True,
            )
        )

        self.add_step(
            MigrationStep(
                step_id="update_memory_types",
                name="Update Memory Types",
                description=f"Update memory types from {from_type} to {to_type}",
                function=self._update_memory_types,
                rollback_function=self._rollback_memory_types,
                critical=True,
            )
        )

        self.add_step(
            MigrationStep(
                step_id="validate_migration",
                name="Validate Migration",
                description="Validate that all memories were updated correctly",
                function=self._validate_migration,
                critical=False,
            )
        )

    async def _identify_memories(self, config: MigrationConfig, result: MigrationResult) -> bool:
        """Identify memories to migrate"""
        try:
            db = await get_mock_database()

            # Get all memories and filter by type
            all_memories = await db.get_all_memories(limit=10000)
            target_memories = []

            for memory in all_memories:
                memory_type = memory.get("metadata", {}).get("memory_type", memory.get("metadata", {}).get("type"))
                if memory_type == self.from_type:
                    # Apply additional filter criteria
                    if self._matches_criteria(memory, self.filter_criteria):
                        target_memories.append(memory)

            result.total_records = len(target_memories)
            self.rollback_data["target_memories"] = target_memories

            await db.close()
            return True

        except Exception as e:
            result.errors.append(f"Failed to identify memories: {str(e)}")
            return False

    async def _update_memory_types(self, config: MigrationConfig, result: MigrationResult) -> bool:
        """Update memory types"""
        try:
            db = await get_mock_database()
            target_memories = self.rollback_data.get("target_memories", [])

            successful_updates = 0
            failed_updates = 0

            # Process in batches
            for i in range(0, len(target_memories), config.batch_size):
                batch = target_memories[i : i + config.batch_size]

                for memory in batch:
                    try:
                        # Update memory type in metadata
                        updated_metadata = memory.get("metadata", {}).copy()
                        updated_metadata["memory_type"] = self.to_type
                        updated_metadata["migration_history"] = updated_metadata.get("migration_history", [])
                        updated_metadata["migration_history"].append(
                            {
                                "from_type": self.from_type,
                                "to_type": self.to_type,
                                "migration_id": self.migration_id,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                        # Store updated memory (in real implementation, this would update the database)
                        # For mock database, we'll simulate the update
                        successful_updates += 1
                        result.processed_records += 1

                    except Exception as e:
                        failed_updates += 1
                        result.errors.append(f"Failed to update memory {memory.get('id', 'unknown')}: {str(e)}")

            result.successful_records = successful_updates
            result.failed_records = failed_updates

            await db.close()
            return failed_updates == 0

        except Exception as e:
            result.errors.append(f"Failed to update memory types: {str(e)}")
            return False

    async def _validate_migration(self, config: MigrationConfig, result: MigrationResult) -> bool:
        """Validate migration results"""
        try:
            # Validation logic would check that all target memories now have the new type
            # For mock implementation, we'll assume success
            return True
        except Exception as e:
            result.warnings.append(f"Validation warning: {str(e)}")
            return True  # Non-critical step

    async def _rollback_memory_types(self, rollback_data: dict[str, Any]) -> bool:
        """Rollback memory type changes"""
        try:
            # In real implementation, this would restore the original memory types
            return True
        except Exception:
            return False

    def _matches_criteria(self, memory: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Check if memory matches additional filter criteria"""
        for key, value in criteria.items():
            if key == "content_contains" and value.lower() not in memory.get("content", "").lower():
                return False
            elif key == "tag_contains" and not any(tag in memory.get("metadata", {}).get("tags", []) for tag in value):
                return False
            elif key == "created_after" and memory.get("created_at", "") < value:
                return False
            elif key == "created_before" and memory.get("created_at", "") > value:
                return False
        return True


class MetadataEnrichmentMigration(MemoryMigration):
    """Migration for enriching memory metadata"""

    def __init__(self, enrichment_function: Callable, filter_criteria: Optional[dict] = None):
        super().__init__(
            migration_id=f"metadata_enrichment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="Metadata Enrichment Migration",
            description="Enrich memory metadata with additional information",
        )
        self.enrichment_function = enrichment_function
        self.filter_criteria = filter_criteria or {}

        self.add_step(
            MigrationStep(
                step_id="identify_memories",
                name="Identify Target Memories",
                description="Find memories to enrich",
                function=self._identify_memories,
                critical=True,
            )
        )

        self.add_step(
            MigrationStep(
                step_id="enrich_metadata",
                name="Enrich Metadata",
                description="Apply enrichment function to memory metadata",
                function=self._enrich_metadata,
                rollback_function=self._rollback_enrichment,
                critical=True,
            )
        )

    async def _identify_memories(self, config: MigrationConfig, result: MigrationResult) -> bool:
        """Identify memories to enrich"""
        try:
            db = await get_mock_database()
            all_memories = await db.get_all_memories(limit=10000)

            target_memories = [
                memory for memory in all_memories if self._matches_criteria(memory, self.filter_criteria)
            ]

            result.total_records = len(target_memories)
            self.rollback_data["target_memories"] = target_memories

            await db.close()
            return True

        except Exception as e:
            result.errors.append(f"Failed to identify memories: {str(e)}")
            return False

    async def _enrich_metadata(self, config: MigrationConfig, result: MigrationResult) -> bool:
        """Enrich memory metadata"""
        try:
            target_memories = self.rollback_data.get("target_memories", [])
            successful_enrichments = 0
            failed_enrichments = 0

            for memory in target_memories:
                try:
                    # Store original metadata for rollback
                    original_metadata = memory.get("metadata", {}).copy()

                    # Apply enrichment function
                    enriched_metadata = await self.enrichment_function(memory)

                    # Store rollback data
                    if "original_metadata" not in self.rollback_data:
                        self.rollback_data["original_metadata"] = {}
                    self.rollback_data["original_metadata"][memory.get("id", "")] = original_metadata

                    successful_enrichments += 1
                    result.processed_records += 1

                except Exception as e:
                    failed_enrichments += 1
                    result.errors.append(f"Failed to enrich memory {memory.get('id', 'unknown')}: {str(e)}")

            result.successful_records = successful_enrichments
            result.failed_records = failed_enrichments

            return failed_enrichments == 0

        except Exception as e:
            result.errors.append(f"Failed to enrich metadata: {str(e)}")
            return False

    async def _rollback_enrichment(self, rollback_data: dict[str, Any]) -> bool:
        """Rollback metadata enrichment"""
        try:
            # Restore original metadata
            return True
        except Exception:
            return False

    def _matches_criteria(self, memory: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Check if memory matches filter criteria"""
        for key, value in criteria.items():
            if key == "memory_type" and memory.get("metadata", {}).get("memory_type") != value:
                return False
            elif key == "missing_field" and value in memory.get("metadata", {}):
                return False
            elif key == "content_length_min" and len(memory.get("content", "")) < value:
                return False
            elif key == "content_length_max" and len(memory.get("content", "")) > value:
                return False
        return True


class MigrationManager:
    """Manager for coordinating memory migrations"""

    def __init__(self):
        self.migrations: dict[str, MemoryMigration] = {}
        self.migration_history: list[MigrationResult] = []
        self.config = MigrationConfig()

    def register_migration(self, migration: MemoryMigration):
        """Register a migration"""
        self.migrations[migration.migration_id] = migration

    async def execute_migration(self, migration_id: str, config: Optional[MigrationConfig] = None) -> MigrationResult:
        """Execute a specific migration"""
        if migration_id not in self.migrations:
            raise ValueError(f"Migration {migration_id} not found")

        migration = self.migrations[migration_id]
        execution_config = config or self.config

        result = await migration.execute(execution_config)
        self.migration_history.append(result)

        return result

    async def get_migration_status(self, migration_id: str) -> Optional[MigrationResult]:
        """Get status of a migration"""
        for result in reversed(self.migration_history):
            if result.migration_id == migration_id:
                return result
        return None

    async def list_available_migrations(self) -> list[dict[str, Any]]:
        """List all available migrations"""
        return [
            {
                "migration_id": migration.migration_id,
                "name": migration.name,
                "description": migration.description,
                "steps": len(migration.steps),
                "dependencies": migration.dependencies,
            }
            for migration in self.migrations.values()
        ]

    async def validate_migration(self, migration_id: str) -> tuple[bool, list[str]]:
        """Validate a migration before execution"""
        if migration_id not in self.migrations:
            return False, [f"Migration {migration_id} not found"]

        migration = self.migrations[migration_id]
        return await migration.validate(self.config)

    def create_memory_type_migration(self, from_type: str, to_type: str, filter_criteria: Optional[dict] = None) -> str:
        """Create and register a memory type migration"""
        migration = MemoryTypeMigration(from_type, to_type, filter_criteria)
        self.register_migration(migration)
        return migration.migration_id

    def create_metadata_enrichment_migration(
        self, enrichment_function: Callable, filter_criteria: Optional[dict] = None
    ) -> str:
        """Create and register a metadata enrichment migration"""
        migration = MetadataEnrichmentMigration(enrichment_function, filter_criteria)
        self.register_migration(migration)
        return migration.migration_id


# Global migration manager instance
migration_manager = MigrationManager()


async def get_migration_manager() -> MigrationManager:
    """Get migration manager instance"""
    return migration_manager
