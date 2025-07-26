"""
Core application infrastructure
"""

from .dependencies import (
    get_dashboard_service,
    get_git_service,
    get_health_service,
    get_memory_service,
    get_session_service,
    get_importance_engine,
    get_metrics_collector,
    get_container,
    initialize_dependencies,
    override_service,
    clear_service_cache,
    reset_dependencies,
    # FastAPI dependencies
    get_dashboard_service_dep,
    get_git_service_dep,
    get_health_service_dep,
    get_memory_service_dep,
    get_session_service_dep,
    get_importance_engine_dep,
    get_metrics_collector_dep,
)

__all__ = [
    "get_dashboard_service",
    "get_git_service", 
    "get_health_service",
    "get_memory_service",
    "get_session_service",
    "get_importance_engine",
    "get_metrics_collector",
    "get_container",
    "initialize_dependencies",
    "override_service",
    "clear_service_cache",
    "reset_dependencies",
    "get_dashboard_service_dep",
    "get_git_service_dep",
    "get_health_service_dep",
    "get_memory_service_dep",
    "get_session_service_dep",
    "get_importance_engine_dep",
    "get_metrics_collector_dep",
]