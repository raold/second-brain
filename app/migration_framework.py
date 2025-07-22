"""
Unified Migration Framework for Second Brain

Provides a consistent migration system for both database schema and memory data
with common patterns for versioning, rollback, validation, and progress tracking.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of migrations supported."""

    DATABASE_SCHEMA = "database_schema"  # DDL changes
    DATABASE_DATA = "database_data"  # DML changes
    MEMORY_STRUCTURE = "memory_structure"  # Memory schema changes
    MEMORY_DATA = "memory_data"  # Memory content changes
    HYBRID = "hybrid"  # Combined changes


class MigrationStatus(Enum):
    """Migration execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class MigrationConfig:
    """Configuration for migration execution."""

    dry_run: bool = False
    batch_size: int = 1000
    enable_rollback: bool = True
    validate_before: bool = True
    validate_after: bool = True
    parallel_execution: bool = False
    checkpoint_frequency: int = 5000
    timeout_seconds: int = 3600
    continue_on_error: bool = False


@dataclass
class MigrationMetadata:
    """Metadata for a migration."""

    id: str
    name: str
    description: str
    version: str
    migration_type: MigrationType
    author: str
    created_at: datetime
    dependencies: list[str]
    reversible: bool
    checksum: str
    estimated_duration: int | None = None


@dataclass
class MigrationResult:
    """Result of a migration execution."""

    migration_id: str
    status: MigrationStatus
    start_time: datetime
    end_time: datetime | None
    affected_items: int
    errors: list[dict[str, Any]]
    rollback_available: bool
    performance_metrics: dict[str, float]
    checkpoint_data: dict[str, Any] | None = None


class Migration(ABC):
    """
    Abstract base class for all migrations.

    Provides common interface for database and memory migrations.
    """

    def __init__(self, metadata: MigrationMetadata):
        self.metadata = metadata
        self.result = None
        self.checkpoint_data = {}

    @abstractmethod
    async def validate_preconditions(self) -> bool:
        """Validate that migration can be applied."""
        pass

    @abstractmethod
    async def apply(self, config: MigrationConfig) -> MigrationResult:
        """Apply the migration."""
        pass

    @abstractmethod
    async def rollback(self) -> MigrationResult:
        """Rollback the migration if possible."""
        pass

    @abstractmethod
    async def validate_postconditions(self) -> bool:
        """Validate that migration was applied correctly."""
        pass

    async def dry_run(self) -> dict[str, Any]:
        """Simulate migration without making changes."""
        return {
            "migration_id": self.metadata.id,
            "can_apply": await self.validate_preconditions(),
            "estimated_changes": await self._estimate_changes(),
            "warnings": await self._check_warnings(),
        }

    async def _estimate_changes(self) -> dict[str, int]:
        """Estimate the scope of changes."""
        return {"estimated_items": 0}

    async def _check_warnings(self) -> list[str]:
        """Check for potential issues."""
        return []

    def get_checkpoint(self) -> dict[str, Any]:
        """Get current checkpoint data for resuming."""
        return self.checkpoint_data

    def set_checkpoint(self, data: dict[str, Any]):
        """Set checkpoint data for resuming."""
        self.checkpoint_data = data
