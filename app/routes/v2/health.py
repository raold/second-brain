"""
Health and system status router
Provides health checks, readiness probes, and system metrics
"""

from datetime import datetime, timezone
from typing import Dict, Any
import os
import psutil
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["System"],
    responses={
        503: {"description": "Service unavailable"}
    }
)


# ==================== Models ====================

class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"


class HealthCheck(BaseModel):
    """Health check response"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ReadinessCheck(BaseModel):
    """Readiness check response"""
    ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: Dict[str, bool]
    message: str


class SystemMetrics(BaseModel):
    """System metrics response"""
    cpu_percent: float
    memory_usage_mb: float
    memory_percent: float
    disk_usage_percent: float
    open_connections: int
    memories_loaded: int
    container_id: str


# ==================== Helper Functions ====================

def get_uptime() -> float:
    """Get application uptime in seconds"""
    # This would normally track from app start
    # For now, use process uptime
    try:
        process = psutil.Process(os.getpid())
        return datetime.now().timestamp() - process.create_time()
    except:
        return 0.0


def check_memory_service() -> Dict[str, Any]:
    """Check memory service health"""
    try:
        from app.services.memory_service import MemoryService
        service = MemoryService()
        # Basic check - service can be instantiated
        return {
            "status": "healthy",
            "type": "in-memory",
            "persistence": os.path.exists("/data") if os.getenv("MEMORY_PERSIST_PATH") else False
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_storage() -> Dict[str, Any]:
    """Check storage health"""
    try:
        persist_path = os.getenv("MEMORY_PERSIST_PATH", "/data")
        if os.path.exists(persist_path):
            stat = os.statvfs(persist_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            used_percent = ((total_gb - free_gb) / total_gb) * 100
            
            return {
                "status": "healthy" if used_percent < 90 else "degraded",
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 2)
            }
        else:
            return {
                "status": "healthy",
                "type": "memory-only",
                "message": "No persistent storage configured"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ==================== Endpoints ====================

@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Comprehensive health check for monitoring"
)
async def health_check():
    """
    Perform comprehensive health check.
    
    Returns overall status and individual service checks.
    Used by monitoring systems and load balancers.
    """
    checks = {
        "memory_service": check_memory_service(),
        "storage": check_storage()
    }
    
    # Add degradation status
    try:
        from app.core.degradation import get_degradation_manager
        degradation_manager = get_degradation_manager()
        await degradation_manager.perform_health_checks()
        degradation_status = degradation_manager.get_status()
        checks["degradation"] = {
            "status": "healthy" if degradation_status["level"] == "FULL" else "degraded",
            "level": degradation_status["level"],
            "features_disabled": degradation_status["features_disabled"]
        }
    except:
        pass
    
    # Determine overall status
    if all(check.get("status") == "healthy" for check in checks.values()):
        overall_status = HealthStatus.HEALTHY
    elif any(check.get("status") == "unhealthy" for check in checks.values()):
        overall_status = HealthStatus.UNHEALTHY
    else:
        overall_status = HealthStatus.DEGRADED
    
    return HealthCheck(
        status=overall_status,
        version="4.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        uptime_seconds=get_uptime(),
        checks=checks
    )


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes"
)
async def liveness_probe():
    """
    Simple liveness probe for Kubernetes.
    
    Returns 200 if the process is alive and responding.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get(
    "/health/ready",
    response_model=ReadinessCheck,
    summary="Readiness probe",
    description="Check if service is ready to accept traffic"
)
async def readiness_probe():
    """
    Readiness probe for Kubernetes.
    
    Checks if all required services are available and ready.
    Returns 503 if not ready.
    """
    services = {
        "memory_service": check_memory_service().get("status") == "healthy",
        "storage": check_storage().get("status") in ["healthy", "degraded"]
    }
    
    is_ready = all(services.values())
    
    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    return ReadinessCheck(
        ready=is_ready,
        services=services,
        message="All services operational"
    )


@router.get(
    "/metrics",
    response_model=SystemMetrics,
    summary="System metrics",
    description="Get system resource metrics"
)
async def get_metrics():
    """
    Get system resource metrics.
    
    Useful for monitoring resource usage and capacity planning.
    """
    try:
        # CPU and Memory metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage("/")
        
        # Network connections
        connections = len(psutil.net_connections())
        
        # Container ID (from hostname in K8s)
        container_id = os.environ.get("HOSTNAME", "local")
        
        # Memory count (would come from app.state in real app)
        memories_loaded = 0  # Placeholder
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_usage_mb=memory.used / (1024**2),
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            open_connections=connections,
            memories_loaded=memories_loaded,
            container_id=container_id
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


@router.get(
    "/degradation",
    summary="Degradation status",
    description="Get current service degradation status"
)
async def get_degradation_status():
    """
    Get detailed degradation status.
    
    Shows which services are failing and what features are disabled.
    """
    try:
        from app.core.degradation import get_degradation_manager
        degradation_manager = get_degradation_manager()
        await degradation_manager.perform_health_checks()
        return degradation_manager.get_status()
    except Exception as e:
        return {
            "error": str(e),
            "level": "UNKNOWN",
            "features_disabled": []
        }


@router.get(
    "/info",
    summary="System information",
    description="Get detailed system information"
)
async def get_system_info():
    """
    Get detailed system information.
    
    Returns version, environment, and configuration details.
    """
    return {
        "application": {
            "name": "Second Brain",
            "version": "4.1.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "false").lower() == "true"
        },
        "runtime": {
            "python_version": os.sys.version,
            "platform": os.sys.platform,
            "pid": os.getpid(),
            "uptime_seconds": get_uptime()
        },
        "container": {
            "id": os.environ.get("HOSTNAME", "local"),
            "memory_limit": os.environ.get("MEMORY_LIMIT", "N/A"),
            "cpu_limit": os.environ.get("CPU_LIMIT", "N/A")
        },
        "features": {
            "websocket": True,
            "bulk_operations": True,
            "analytics": True,
            "export_import": True,
            "real_time_updates": True,
            "vector_search": False,  # Not yet implemented
            "sqlite_persistence": False  # Not yet implemented
        }
    }