"""
Migration Execution Engine

Handles the execution, tracking, and management of migrations with
support for dependencies, rollback, and progress monitoring.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Type, Tuple, Any

import asyncpg

from .migration_framework import (
    Migration, MigrationConfig, MigrationMetadata, MigrationResult,
    MigrationStatus, MigrationType
)

logger = logging.getLogger(__name__)


class MigrationHistory:
    """Tracks migration execution history."""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self._initialized = False
    
    async def initialize(self):
        """Create migration history table if needed."""
        if self._initialized:
            return
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    migration_id VARCHAR(255) UNIQUE NOT NULL,
                    migration_type VARCHAR(50) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    checksum VARCHAR(64) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE,
                    rolled_back_at TIMESTAMP WITH TIME ZONE,
                    execution_time_ms INTEGER,
                    affected_items INTEGER,
                    error_details JSONB,
                    checkpoint_data JSONB,
                    metadata JSONB
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_migration_history_status 
                ON migration_history(status)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_migration_history_version 
                ON migration_history(version)
            """)
        
        self._initialized = True
    
    async def record_migration(self, migration: Migration, result: MigrationResult):
        """Record migration execution in history."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO migration_history (
                    migration_id, migration_type, version, checksum,
                    status, applied_at, execution_time_ms, affected_items,
                    error_details, checkpoint_data, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (migration_id) DO UPDATE SET
                    status = $5,
                    applied_at = $6,
                    execution_time_ms = $7,
                    affected_items = $8,
                    error_details = $9,
                    checkpoint_data = $10
            """, 
                migration.metadata.id,
                migration.metadata.migration_type.value,
                migration.metadata.version,
                migration.metadata.checksum,
                result.status.value,
                result.end_time,
                int((result.end_time - result.start_time).total_seconds() * 1000) if result.end_time else None,
                result.affected_items,
                json.dumps(result.errors) if result.errors else None,
                json.dumps(result.checkpoint_data) if result.checkpoint_data else None,
                json.dumps(migration.metadata.dict())
            )
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of successfully applied migration IDs."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT migration_id FROM migration_history
                WHERE status = 'completed'
                ORDER BY applied_at
            """)
            return [row['migration_id'] for row in rows]
    
    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific migration."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM migration_history
                WHERE migration_id = $1
            """, migration_id)
            return dict(row) if row else None


class MigrationEngine:
    """
    Core engine for executing migrations with dependency resolution,
    rollback support, and progress tracking.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.history = MigrationHistory(connection_pool)
        self.migrations: Dict[str, Type[Migration]] = {}
        self.running_migrations: Dict[str, Migration] = {}
    
    async def initialize(self):
        """Initialize the migration engine."""
        await self.history.initialize()
    
    def register_migration(self, migration_class: Type[Migration]):
        """Register a migration class."""
        # Create instance to get metadata
        instance = migration_class()
        self.migrations[instance.metadata.id] = migration_class
        logger.info(f"Registered migration: {instance.metadata.id}")
    
    async def discover_migrations(self, directory: Path):
        """Auto-discover migrations from a directory."""
        # This would dynamically import migration files
        # For now, migrations must be manually registered
        pass
    
    async def get_pending_migrations(self) -> List[MigrationMetadata]:
        """Get list of migrations that haven't been applied."""
        applied = await self.history.get_applied_migrations()
        pending = []
        
        for migration_id, migration_class in self.migrations.items():
            if migration_id not in applied:
                instance = migration_class()
                pending.append(instance.metadata)
        
        return sorted(pending, key=lambda m: m.version)
    
    def _resolve_dependencies(self, migrations: List[MigrationMetadata]) -> List[MigrationMetadata]:
        """Resolve migration dependencies and return ordered list."""
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        migration_map = {m.id: m for m in migrations}
        
        for migration in migrations:
            for dep in migration.dependencies:
                if dep in migration_map:
                    graph[dep].append(migration.id)
                    in_degree[migration.id] += 1
        
        # Topological sort
        queue = [m.id for m in migrations if in_degree[m.id] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(migration_map[current])
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(migrations):
            raise ValueError("Circular dependency detected in migrations")
        
        return result
    
    async def execute_migration(
        self, 
        migration_id: str, 
        config: MigrationConfig = None
    ) -> MigrationResult:
        """Execute a single migration."""
        if migration_id not in self.migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        if config is None:
            config = MigrationConfig()
        
        migration_class = self.migrations[migration_id]
        migration = migration_class()
        
        # Check if already applied
        status = await self.history.get_migration_status(migration_id)
        if status and status['status'] == 'completed':
            logger.info(f"Migration {migration_id} already applied")
            return MigrationResult(
                migration_id=migration_id,
                status=MigrationStatus.SKIPPED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                affected_items=0,
                errors=[],
                rollback_available=False,
                performance_metrics={}
            )
        
        # Track running migration
        self.running_migrations[migration_id] = migration
        
        try:
            # Validate preconditions
            if config.validate_before:
                if not await migration.validate_preconditions():
                    raise ValueError("Precondition validation failed")
            
            # Execute migration
            if config.dry_run:
                result = await migration.dry_run()
                return MigrationResult(
                    migration_id=migration_id,
                    status=MigrationStatus.COMPLETED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    affected_items=result.get('estimated_changes', {}).get('estimated_items', 0),
                    errors=[],
                    rollback_available=False,
                    performance_metrics={'dry_run': True}
                )
            
            result = await migration.apply(config)
            
            # Validate postconditions
            if config.validate_after:
                if not await migration.validate_postconditions():
                    if config.enable_rollback:
                        logger.warning("Postcondition validation failed, rolling back")
                        await migration.rollback()
                        result.status = MigrationStatus.ROLLED_BACK
                    else:
                        result.status = MigrationStatus.FAILED
                        result.errors.append({"error": "Postcondition validation failed"})
            
            # Record in history
            await self.history.record_migration(migration, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Migration {migration_id} failed: {e}")
            
            # Attempt rollback if enabled
            if config.enable_rollback and migration.metadata.reversible:
                try:
                    await migration.rollback()
                    status = MigrationStatus.ROLLED_BACK
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    status = MigrationStatus.FAILED
            else:
                status = MigrationStatus.FAILED
            
            result = MigrationResult(
                migration_id=migration_id,
                status=status,
                start_time=datetime.now(),
                end_time=datetime.now(),
                affected_items=0,
                errors=[{"error": str(e)}],
                rollback_available=migration.metadata.reversible,
                performance_metrics={}
            )
            
            await self.history.record_migration(migration, result)
            return result
            
        finally:
            # Clean up
            if migration_id in self.running_migrations:
                del self.running_migrations[migration_id]
    
    async def execute_pending_migrations(
        self, 
        config: MigrationConfig = None,
        migration_type: Optional[MigrationType] = None
    ) -> List[MigrationResult]:
        """Execute all pending migrations in order."""
        pending = await self.get_pending_migrations()
        
        # Filter by type if specified
        if migration_type:
            pending = [m for m in pending if m.migration_type == migration_type]
        
        # Resolve dependencies
        ordered = self._resolve_dependencies(pending)
        
        results = []
        for migration_metadata in ordered:
            result = await self.execute_migration(migration_metadata.id, config)
            results.append(result)
            
            # Stop on failure unless continue_on_error is set
            if result.status == MigrationStatus.FAILED and not config.continue_on_error:
                break
        
        return results
    
    async def rollback_migration(self, migration_id: str) -> MigrationResult:
        """Rollback a specific migration."""
        if migration_id not in self.migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        migration_class = self.migrations[migration_id]
        migration = migration_class()
        
        if not migration.metadata.reversible:
            raise ValueError(f"Migration {migration_id} is not reversible")
        
        try:
            result = await migration.rollback()
            result.status = MigrationStatus.ROLLED_BACK
            
            # Update history
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE migration_history 
                    SET status = 'rolled_back', rolled_back_at = $1
                    WHERE migration_id = $2
                """, datetime.now(), migration_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Rollback of {migration_id} failed: {e}")
            return MigrationResult(
                migration_id=migration_id,
                status=MigrationStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                affected_items=0,
                errors=[{"error": f"Rollback failed: {str(e)}"}],
                rollback_available=False,
                performance_metrics={}
            )
    
    def get_running_migrations(self) -> List[str]:
        """Get list of currently running migrations."""
        return list(self.running_migrations.keys())
    
    async def get_migration_progress(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Get progress of a running migration."""
        if migration_id in self.running_migrations:
            migration = self.running_migrations[migration_id]
            checkpoint = migration.get_checkpoint()
            return {
                "migration_id": migration_id,
                "status": "running",
                "checkpoint": checkpoint
            }
        
        # Check history for completed migrations
        return await self.history.get_migration_status(migration_id) 