"""
Health Service - Handles health check and system status business logic.
Provides system health information and diagnostics.
"""

import logging
import os
from datetime import datetime
from typing import Any

import psutil

from app.database import Database
from app.database_mock import MockDatabase
from app.version import get_version_info

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service layer for health and status operations.
    Monitors system health, database status, and performance metrics.
    """

    def __init__(self, database: Database | MockDatabase):
        self.db = database
        self.logger = logger
        self.start_time = datetime.utcnow()

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get basic health status of the system.

        Returns:
            Health status information
        """
        try:
            version_info = get_version_info()

            return {
                "status": "healthy",
                "version": version_info["version"],
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "environment": os.getenv("ENVIRONMENT", "development"),
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def get_system_status(self) -> dict[str, Any]:
        """
        Get comprehensive system status including database and performance metrics.

        Returns:
            Detailed system status
        """
        try:
            # Get database status
            db_status = await self._get_database_status()

            # Get system metrics
            system_metrics = self._get_system_metrics()

            # Get index statistics
            index_stats = await self.db.get_index_stats()

            # Generate recommendations
            recommendations = self._generate_recommendations(index_stats)

            return {
                "database": db_status["status"],
                "database_details": db_status,
                "index_status": index_stats,
                "system_metrics": system_metrics,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            raise

    async def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get detailed performance metrics.

        Returns:
            Performance metrics and statistics
        """
        try:
            # Get database performance metrics
            db_metrics = await self._get_database_performance_metrics()

            # Get system resource usage
            resource_usage = self._get_resource_usage()

            # Get API performance stats if available
            api_stats = self._get_api_performance_stats()

            return {
                "database_performance": db_metrics,
                "resource_usage": resource_usage,
                "api_performance": api_stats,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            raise

    async def run_diagnostics(self) -> dict[str, Any]:
        """
        Run comprehensive system diagnostics.

        Returns:
            Diagnostic results and any issues found
        """
        try:
            diagnostics = {
                "timestamp": datetime.utcnow().isoformat(),
                "checks": [],
                "issues": [],
                "overall_status": "healthy",
            }

            # Check database connectivity
            db_check = await self._check_database_connectivity()
            diagnostics["checks"].append(db_check)
            if not db_check["passed"]:
                diagnostics["issues"].append(db_check["error"])

            # Check memory usage
            memory_check = self._check_memory_usage()
            diagnostics["checks"].append(memory_check)
            if not memory_check["passed"]:
                diagnostics["issues"].append(memory_check["error"])

            # Check disk space
            disk_check = self._check_disk_space()
            diagnostics["checks"].append(disk_check)
            if not disk_check["passed"]:
                diagnostics["issues"].append(disk_check["error"])

            # Check index health
            index_check = await self._check_index_health()
            diagnostics["checks"].append(index_check)
            if not index_check["passed"]:
                diagnostics["issues"].append(index_check["error"])

            # Set overall status
            if diagnostics["issues"]:
                diagnostics["overall_status"] = "degraded" if len(diagnostics["issues"]) < 2 else "critical"

            return diagnostics

        except Exception as e:
            self.logger.error(f"Diagnostics failed: {e}")
            raise

    async def _get_database_status(self) -> dict[str, Any]:
        """Get database connection and health status."""
        try:
            # Check if using mock database - use class name to be more robust
            is_mock = (
                isinstance(self.db, MockDatabase)
                or self.db.__class__.__name__ == "MockDatabase"
                or str(type(self.db)).find("MockDatabase") != -1
            )

            if is_mock:
                return {"status": "connected", "type": "mock", "healthy": True, "latency_ms": 0.1}

            # For real database, check connection
            start_time = datetime.utcnow()

            # Simple query to test connection
            if hasattr(self.db, "pool") and self.db.pool:
                async with self.db.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

                latency = (datetime.utcnow() - start_time).total_seconds() * 1000

                return {
                    "status": "connected",
                    "type": "postgresql",
                    "healthy": True,
                    "latency_ms": round(latency, 2),
                    "pool_size": self.db.pool.get_size() if hasattr(self.db.pool, "get_size") else "unknown",
                }

            return {
                "status": "disconnected",
                "type": "postgresql",
                "healthy": False,
                "error": "No database pool available",
            }

        except Exception as e:
            return {"status": "error", "healthy": False, "error": str(e)}

    def _get_system_metrics(self) -> dict[str, Any]:
        """Get system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu": {"usage_percent": cpu_percent, "cores": psutil.cpu_count()},
                "memory": {
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                "disk": {
                    "usage_percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return {}

    def _generate_recommendations(self, index_stats: dict[str, Any]) -> dict[str, Any]:
        """Generate system recommendations based on current state."""
        recommendations = {
            "create_index": False,
            "index_type": "None",
            "performance_notes": [],
            "optimization_tips": [],
        }

        # Check if index should be created
        total_memories = index_stats.get("total_memories", 0)
        embeddings_count = index_stats.get("memories_with_embeddings", 0)
        index_ready = index_stats.get("index_ready", False)

        if embeddings_count >= 1000 and not index_ready:
            recommendations["create_index"] = True
            recommendations["index_type"] = "HNSW (recommended for 1000+ vectors)"
            recommendations["performance_notes"].append(
                "Creating an HNSW index will significantly improve search performance"
            )
        elif embeddings_count < 1000:
            recommendations["performance_notes"].append(
                f"Index creation recommended after 1000 memories (current: {embeddings_count})"
            )

        # Add optimization tips
        if total_memories > 10000:
            recommendations["optimization_tips"].append(
                "Consider implementing memory archival for older, less-accessed memories"
            )

        if index_stats.get("hnsw_index_exists", False):
            recommendations["index_type"] = "HNSW (active)"
        elif index_stats.get("ivf_index_exists", False):
            recommendations["index_type"] = "IVFFlat (active)"

        return recommendations

    async def _get_database_performance_metrics(self) -> dict[str, Any]:
        """Get database performance metrics."""
        try:
            if isinstance(self.db, MockDatabase):
                return {"type": "mock", "query_performance": "instant", "connection_pool": "not applicable"}

            # Get real database metrics
            metrics = {}

            # Test query performance
            start_time = datetime.utcnow()
            await self.db.get_index_stats()
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            metrics["average_query_time_ms"] = round(query_time, 2)
            metrics["connection_pool_status"] = "active" if hasattr(self.db, "pool") and self.db.pool else "inactive"

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get database performance metrics: {e}")
            return {"error": str(e)}

    def _get_resource_usage(self) -> dict[str, Any]:
        """Get current resource usage."""
        try:
            process = psutil.Process(os.getpid())

            return {
                "process_memory_mb": round(process.memory_info().rss / (1024**2), 2),
                "process_cpu_percent": process.cpu_percent(interval=0.1),
                "thread_count": process.num_threads(),
                "open_files": len(process.open_files()) if hasattr(process, "open_files") else "unknown",
            }
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            return {}

    def _get_api_performance_stats(self) -> dict[str, Any]:
        """Get API performance statistics."""
        # This would integrate with actual API monitoring
        # For now, return placeholder data
        return {
            "endpoints": {
                "/memories": {"avg_response_ms": 25, "success_rate": 0.99},
                "/memories/search": {"avg_response_ms": 35, "success_rate": 0.98},
                "/health": {"avg_response_ms": 5, "success_rate": 1.0},
            }
        }

    async def _check_database_connectivity(self) -> dict[str, Any]:
        """Check database connectivity."""
        try:
            status = await self._get_database_status()
            return {
                "check": "database_connectivity",
                "passed": status.get("healthy", False),
                "details": status,
                "error": status.get("error"),
            }
        except Exception as e:
            return {"check": "database_connectivity", "passed": False, "error": str(e)}

    def _check_memory_usage(self) -> dict[str, Any]:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            passed = memory.percent < 90  # Fail if > 90% usage

            return {
                "check": "memory_usage",
                "passed": passed,
                "details": {"usage_percent": memory.percent, "available_gb": round(memory.available / (1024**3), 2)},
                "error": "High memory usage detected" if not passed else None,
            }
        except Exception as e:
            return {"check": "memory_usage", "passed": False, "error": str(e)}

    def _check_disk_space(self) -> dict[str, Any]:
        """Check available disk space."""
        try:
            disk = psutil.disk_usage("/")
            passed = disk.percent < 85  # Fail if > 85% usage

            return {
                "check": "disk_space",
                "passed": passed,
                "details": {"usage_percent": disk.percent, "free_gb": round(disk.free / (1024**3), 2)},
                "error": "Low disk space" if not passed else None,
            }
        except Exception as e:
            return {"check": "disk_space", "passed": False, "error": str(e)}

    async def _check_index_health(self) -> dict[str, Any]:
        """Check vector index health."""
        try:
            stats = await self.db.get_index_stats()
            index_ready = stats.get("index_ready", False)

            # Check if index should exist but doesn't
            should_have_index = stats.get("memories_with_embeddings", 0) >= 1000
            passed = not should_have_index or index_ready

            return {
                "check": "index_health",
                "passed": passed,
                "details": stats,
                "error": "Index missing for large dataset" if not passed else None,
            }
        except Exception as e:
            return {"check": "index_health", "passed": False, "error": str(e)}
