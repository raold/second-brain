"""
Migration Dashboard Integration

Provides dashboard widgets and monitoring for the unified migration system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .migration_engine import MigrationEngine
from .migration_framework import MigrationStatus, MigrationType
from .database import get_database

logger = logging.getLogger(__name__)


class MigrationDashboard:
    """Dashboard component for migration monitoring and management."""
    
    def __init__(self):
        self.migration_engine: Optional[MigrationEngine] = None
        self._last_refresh = None
        self._cache_duration = timedelta(minutes=5)
        self._cached_data = {}
    
    async def initialize(self):
        """Initialize migration engine."""
        try:
            db = await get_database()
            if db.pool:
                self.migration_engine = MigrationEngine(db.pool)
                await self.migration_engine.initialize()
        except Exception as e:
            logger.warning(f"Migration engine initialization failed: {e}")
    
    async def get_migration_summary(self) -> Dict[str, Any]:
        """Get overall migration system summary."""
        if not self.migration_engine:
            await self.initialize()
        
        if not self.migration_engine:
            return {
                "status": "unavailable",
                "message": "Migration engine not available",
                "pending_count": 0,
                "running_count": 0,
                "recent_failures": 0
            }
        
        try:
            # Check cache
            if self._is_cache_valid("summary"):
                return self._cached_data["summary"]
            
            # Get pending migrations
            pending = await self.migration_engine.get_pending_migrations()
            
            # Get running migrations
            running = self.migration_engine.get_running_migrations()
            
            # Get recent failures (last 24 hours)
            recent_failures = await self._get_recent_failures()
            
            summary = {
                "status": "ready" if not running else "running",
                "pending_count": len(pending),
                "running_count": len(running),
                "recent_failures": recent_failures,
                "last_update": datetime.now().isoformat(),
                "engine_status": "operational"
            }
            
            # Cache result
            self._cached_data["summary"] = summary
            self._last_refresh = datetime.now()
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get migration summary: {e}")
            return {
                "status": "error",
                "message": str(e),
                "pending_count": 0,
                "running_count": 0,
                "recent_failures": 0
            }
    
    async def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations for dashboard."""
        if not self.migration_engine:
            return []
        
        try:
            pending = await self.migration_engine.get_pending_migrations()
            
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.migration_type.value,
                    "version": m.version,
                    "dependencies": m.dependencies,
                    "reversible": m.reversible,
                    "estimated_duration": m.estimated_duration,
                    "author": m.author,
                    "created_at": m.created_at.isoformat()
                }
                for m in pending[:10]  # Limit to 10 for dashboard
            ]
            
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    async def get_running_migrations(self) -> List[Dict[str, Any]]:
        """Get currently running migrations with progress."""
        if not self.migration_engine:
            return []
        
        try:
            running_ids = self.migration_engine.get_running_migrations()
            running_details = []
            
            for migration_id in running_ids:
                progress = await self.migration_engine.get_migration_progress(migration_id)
                if progress:
                    running_details.append({
                        "id": migration_id,
                        "status": progress["status"],
                        "checkpoint": progress.get("checkpoint", {}),
                        "started_at": datetime.now().isoformat()  # Would need to track this
                    })
            
            return running_details
            
        except Exception as e:
            logger.error(f"Failed to get running migrations: {e}")
            return []
    
    async def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent migration history."""
        if not self.migration_engine:
            return []
        
        try:
            applied_ids = await self.migration_engine.history.get_applied_migrations()
            recent_history = []
            
            for migration_id in applied_ids[-limit:]:
                status = await self.migration_engine.history.get_migration_status(migration_id)
                if status:
                    recent_history.append({
                        "id": migration_id,
                        "status": status["status"],
                        "applied_at": status.get("applied_at", "Unknown"),
                        "execution_time_ms": status.get("execution_time_ms", 0),
                        "affected_items": status.get("affected_items", 0)
                    })
            
            return list(reversed(recent_history))  # Most recent first
            
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    async def get_migration_statistics(self) -> Dict[str, Any]:
        """Get migration system statistics."""
        if not self.migration_engine:
            return {}
        
        try:
            if self._is_cache_valid("stats"):
                return self._cached_data["stats"]
            
            # Get all applied migrations
            applied_ids = await self.migration_engine.history.get_applied_migrations()
            
            # Categorize by type
            type_counts = {}
            success_count = 0
            failure_count = 0
            total_execution_time = 0
            
            for migration_id in applied_ids:
                status = await self.migration_engine.history.get_migration_status(migration_id)
                if status:
                    metadata = status.get("metadata", {})
                    migration_type = metadata.get("migration_type", "unknown")
                    type_counts[migration_type] = type_counts.get(migration_type, 0) + 1
                    
                    if status["status"] == "completed":
                        success_count += 1
                    elif status["status"] == "failed":
                        failure_count += 1
                    
                    execution_time = status.get("execution_time_ms", 0)
                    if execution_time:
                        total_execution_time += execution_time
            
            stats = {
                "total_migrations": len(applied_ids),
                "success_rate": round((success_count / len(applied_ids) * 100) if applied_ids else 0, 1),
                "type_distribution": type_counts,
                "average_execution_time_ms": round(total_execution_time / len(applied_ids)) if applied_ids else 0,
                "successful": success_count,
                "failed": failure_count
            }
            
            # Cache result
            self._cached_data["stats"] = stats
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get migration statistics: {e}")
            return {}
    
    async def _get_recent_failures(self) -> int:
        """Count migrations that failed in the last 24 hours."""
        if not self.migration_engine:
            return 0
            
        try:
            applied_ids = await self.migration_engine.history.get_applied_migrations()
            recent_failures = 0
            cutoff = datetime.now() - timedelta(hours=24)
            
            for migration_id in applied_ids:
                status = await self.migration_engine.history.get_migration_status(migration_id)
                if status and status["status"] == "failed":
                    applied_at = status.get("applied_at")
                    if applied_at and isinstance(applied_at, datetime) and applied_at > cutoff:
                        recent_failures += 1
                    elif applied_at and isinstance(applied_at, str):
                        try:
                            applied_time = datetime.fromisoformat(applied_at.replace('Z', '+00:00'))
                            if applied_time > cutoff:
                                recent_failures += 1
                        except:
                            pass
            
            return recent_failures
            
        except Exception as e:
            logger.error(f"Failed to count recent failures: {e}")
            return 0
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cached_data or not self._last_refresh:
            return False
        
        return datetime.now() - self._last_refresh < self._cache_duration
    
    async def execute_migration_from_dashboard(self, migration_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Execute a migration from the dashboard with safety checks."""
        if not self.migration_engine:
            return {"success": False, "error": "Migration engine not available"}
        
        try:
            from .migration_framework import MigrationConfig
            
            config = MigrationConfig(
                dry_run=dry_run,
                batch_size=500,  # Smaller batches for dashboard execution
                enable_rollback=True,
                validate_before=True,
                validate_after=True
            )
            
            result = await self.migration_engine.execute_migration(migration_id, config)
            
            return {
                "success": result.status.value in ["completed", "skipped"],
                "status": result.status.value,
                "affected_items": result.affected_items,
                "execution_time_seconds": (result.end_time - result.start_time).total_seconds() if result.end_time else 0,
                "errors": result.errors,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Failed to execute migration {migration_id}: {e}")
            return {"success": False, "error": str(e)}


# Global instance
_migration_dashboard = None


def get_migration_dashboard() -> MigrationDashboard:
    """Get or create migration dashboard instance."""
    global _migration_dashboard
    
    if _migration_dashboard is None:
        _migration_dashboard = MigrationDashboard()
    
    return _migration_dashboard 