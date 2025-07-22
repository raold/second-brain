"""
Migration API Routes

Provides REST endpoints for managing database and memory migrations
with unified interface for all migration types.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import get_database
from ..migration_engine import MigrationEngine
from ..migration_framework import MigrationConfig, MigrationStatus, MigrationType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migrations", tags=["migrations"])

# Global migration engine instance
_migration_engine: MigrationEngine | None = None


async def get_migration_engine() -> MigrationEngine:
    """Get or create migration engine instance."""
    global _migration_engine

    if _migration_engine is None:
        db = await get_database()
        if not db.pool:
            raise HTTPException(status_code=500, detail="Database pool not initialized")
        _migration_engine = MigrationEngine(db.pool)
        await _migration_engine.initialize()

    return _migration_engine


# Request/Response Models
class MigrationConfigRequest(BaseModel):
    """Configuration for migration execution."""

    dry_run: bool = Field(False, description="Simulate without applying changes")
    batch_size: int = Field(1000, description="Batch size for data migrations")
    enable_rollback: bool = Field(True, description="Enable rollback on failure")
    validate_before: bool = Field(True, description="Validate preconditions")
    validate_after: bool = Field(True, description="Validate postconditions")
    parallel_execution: bool = Field(False, description="Enable parallel processing")
    continue_on_error: bool = Field(False, description="Continue on individual errors")


class MigrationInfo(BaseModel):
    """Information about a migration."""

    id: str
    name: str
    description: str
    version: str
    migration_type: str
    author: str
    created_at: datetime
    dependencies: list[str]
    reversible: bool
    status: str | None = None
    applied_at: datetime | None = None


class MigrationResultResponse(BaseModel):
    """Response for migration execution."""

    migration_id: str
    status: str
    start_time: datetime
    end_time: datetime | None
    affected_items: int
    errors: list[dict]
    rollback_available: bool
    performance_metrics: dict


class MigrationProgressResponse(BaseModel):
    """Response for migration progress."""

    migration_id: str
    status: str
    progress_percentage: float | None
    estimated_completion: datetime | None
    checkpoint: dict | None


# API Endpoints
@router.get("/pending", response_model=list[MigrationInfo])
async def get_pending_migrations(
    migration_type: MigrationType | None = Query(None, description="Filter by migration type"),
    engine: MigrationEngine = Depends(get_migration_engine),
):
    """Get list of pending migrations."""
    try:
        pending = await engine.get_pending_migrations()

        # Filter by type if specified
        if migration_type:
            pending = [m for m in pending if m.migration_type == migration_type]

        # Convert to response format
        migrations = []
        for metadata in pending:
            # Check if already in progress
            status = None
            if metadata.id in engine.get_running_migrations():
                status = "running"

            migrations.append(
                MigrationInfo(
                    id=metadata.id,
                    name=metadata.name,
                    description=metadata.description,
                    version=metadata.version,
                    migration_type=metadata.migration_type.value,
                    author=metadata.author,
                    created_at=metadata.created_at,
                    dependencies=metadata.dependencies,
                    reversible=metadata.reversible,
                    status=status,
                )
            )

        return migrations

    except Exception as e:
        logger.error(f"Failed to get pending migrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[MigrationInfo])
async def get_migration_history(
    status: MigrationStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum results"),
    engine: MigrationEngine = Depends(get_migration_engine),
):
    """Get migration execution history."""
    try:
        # Get applied migrations
        applied_ids = await engine.history.get_applied_migrations()

        migrations = []
        for migration_id in applied_ids[-limit:]:
            history = await engine.history.get_migration_status(migration_id)
            if history:
                # Filter by status if specified
                if status and history["status"] != status.value:
                    continue

                metadata = history.get("metadata", {})
                migrations.append(
                    MigrationInfo(
                        id=migration_id,
                        name=metadata.get("name", "Unknown"),
                        description=metadata.get("description", ""),
                        version=metadata.get("version", ""),
                        migration_type=metadata.get("migration_type", "unknown"),
                        author=metadata.get("author", "unknown"),
                        created_at=metadata.get("created_at", datetime.now()),
                        dependencies=metadata.get("dependencies", []),
                        reversible=metadata.get("reversible", False),
                        status=history["status"],
                        applied_at=history.get("applied_at"),
                    )
                )

        return migrations

    except Exception as e:
        logger.error(f"Failed to get migration history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/{migration_id}", response_model=MigrationResultResponse)
async def execute_migration(
    migration_id: str,
    config: MigrationConfigRequest = MigrationConfigRequest(),
    engine: MigrationEngine = Depends(get_migration_engine),
):
    """Execute a specific migration."""
    try:
        # Convert request to config
        migration_config = MigrationConfig()
        migration_config.dry_run = config.dry_run
        migration_config.batch_size = config.batch_size
        migration_config.enable_rollback = config.enable_rollback
        migration_config.validate_before = config.validate_before
        migration_config.validate_after = config.validate_after
        migration_config.parallel_execution = config.parallel_execution
        migration_config.continue_on_error = config.continue_on_error

        # Execute migration
        result = await engine.execute_migration(migration_id, migration_config)

        return MigrationResultResponse(
            migration_id=result.migration_id,
            status=result.status.value,
            start_time=result.start_time,
            end_time=result.end_time,
            affected_items=result.affected_items,
            errors=result.errors,
            rollback_available=result.rollback_available,
            performance_metrics=result.performance_metrics,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute migration {migration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-all", response_model=list[MigrationResultResponse])
async def execute_all_pending(
    config: MigrationConfigRequest = MigrationConfigRequest(),
    migration_type: MigrationType | None = Query(None, description="Filter by type"),
    engine: MigrationEngine = Depends(get_migration_engine),
):
    """Execute all pending migrations."""
    try:
        # Convert request to config
        migration_config = MigrationConfig()
        migration_config.dry_run = config.dry_run
        migration_config.batch_size = config.batch_size
        migration_config.enable_rollback = config.enable_rollback
        migration_config.validate_before = config.validate_before
        migration_config.validate_after = config.validate_after
        migration_config.parallel_execution = config.parallel_execution
        migration_config.continue_on_error = config.continue_on_error

        # Execute migrations
        results = await engine.execute_pending_migrations(migration_config, migration_type)

        # Convert to response format
        responses = []
        for result in results:
            responses.append(
                MigrationResultResponse(
                    migration_id=result.migration_id,
                    status=result.status.value,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    affected_items=result.affected_items,
                    errors=result.errors,
                    rollback_available=result.rollback_available,
                    performance_metrics=result.performance_metrics,
                )
            )

        return responses

    except Exception as e:
        logger.error(f"Failed to execute pending migrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/{migration_id}", response_model=MigrationResultResponse)
async def rollback_migration(migration_id: str, engine: MigrationEngine = Depends(get_migration_engine)):
    """Rollback a specific migration."""
    try:
        result = await engine.rollback_migration(migration_id)

        return MigrationResultResponse(
            migration_id=result.migration_id,
            status=result.status.value,
            start_time=result.start_time,
            end_time=result.end_time,
            affected_items=result.affected_items,
            errors=result.errors,
            rollback_available=result.rollback_available,
            performance_metrics=result.performance_metrics,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rollback migration {migration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{migration_id}", response_model=MigrationProgressResponse)
async def get_migration_progress(migration_id: str, engine: MigrationEngine = Depends(get_migration_engine)):
    """Get progress of a running migration."""
    try:
        progress = await engine.get_migration_progress(migration_id)

        if not progress:
            raise HTTPException(status_code=404, detail="Migration not found or not running")

        # Calculate progress percentage if available
        progress_percentage = None
        estimated_completion = None

        if progress.get("checkpoint"):
            checkpoint = progress["checkpoint"]
            if "processed_ids" in checkpoint and "total_items" in checkpoint:
                processed = len(checkpoint["processed_ids"])
                total = checkpoint["total_items"]
                if total > 0:
                    progress_percentage = (processed / total) * 100

        return MigrationProgressResponse(
            migration_id=migration_id,
            status=progress["status"],
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            checkpoint=progress.get("checkpoint"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get migration progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/running", response_model=list[str])
async def get_running_migrations(engine: MigrationEngine = Depends(get_migration_engine)):
    """Get list of currently running migrations."""
    try:
        return engine.get_running_migrations()
    except Exception as e:
        logger.error(f"Failed to get running migrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/{migration_id}")
async def validate_migration(migration_id: str, engine: MigrationEngine = Depends(get_migration_engine)):
    """Validate a migration without executing it."""
    try:
        if migration_id not in engine.migrations:
            raise HTTPException(status_code=404, detail="Migration not found")

        # Create migration instance - it needs pool parameter if it's a database migration
        migration_class = engine.migrations[migration_id]

        # Check if it's a database migration that needs pool
        import inspect

        sig = inspect.signature(migration_class.__init__)
        if "connection_pool" in sig.parameters:
            migration = migration_class(engine.pool)
        else:
            migration = migration_class()

        # Validate preconditions
        can_apply = await migration.validate_preconditions()

        # Dry run
        dry_run_result = await migration.dry_run()

        return {"migration_id": migration_id, "can_apply": can_apply, "dry_run_result": dry_run_result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate migration {migration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
