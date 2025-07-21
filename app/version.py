"""
Second Brain Application Version Information
Centralized version management system for production deployment
"""

import os
from datetime import datetime
from typing import Any

# Core version information
__version__ = "2.6.0-dev"
__version_info__ = (2, 6, 0)
__build__ = "development"
__release_date__ = "2025-07-20"

# Build and environment information
__build_timestamp__ = datetime.now().isoformat()
__git_commit__ = os.getenv("GIT_COMMIT", "unknown")
__environment__ = os.getenv("ENVIRONMENT", "development")


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> dict[str, Any]:
    """Get comprehensive version information for dashboard and API."""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "build": __build__,
        "release_date": __release_date__,
        "build_timestamp": __build_timestamp__,
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),  # Read dynamically for testing
        "environment": os.getenv("ENVIRONMENT", "development"),  # Read dynamically for testing
        "version_string": f"v{__version__}",
        "display_name": f"Second Brain v{__version__}",
        "codename": get_current_codename(),
        "roadmap_info": get_current_roadmap_info(),
    }


def get_dashboard_version() -> dict[str, Any]:
    """Get version information specifically formatted for dashboard display."""
    current_info = get_current_roadmap_info()
    return {
        "current": f"v{__version__}",
        "display": f"v{__version__}",
        "codename": current_info.get("codename", "Unknown"),
        "focus": current_info.get("focus", "Development"),
        "status": current_info.get("status", "current"),
        "release_date": __release_date__,
        "next_version": get_next_planned_version(),
    }


def get_current_codename() -> str:
    """Get the codename for the current version."""
    info = get_current_roadmap_info()
    return info.get("codename", "Unknown")


def get_current_roadmap_info() -> dict[str, Any]:
    """Get roadmap information for the current version."""
    roadmap = get_cognitive_roadmap()
    current_key = f"v{__version__}"

    # Try with full version first
    if current_key in roadmap:
        return roadmap[current_key]

    # Try without suffix (e.g., 2.5.2-RC -> 2.5.2, 2.6.0-dev -> 2.6.0)
    if "-" in __version__:
        base_version = __version__.split("-")[0]
        base_key = f"v{base_version}"
        if base_key in roadmap:
            return roadmap[base_key]

    return {}


def get_next_planned_version() -> str:
    """Get the next planned version from roadmap."""
    roadmap = get_cognitive_roadmap()

    # Find versions that are planned but not completed
    planned_versions = []
    for version, info in roadmap.items():
        if info.get("status") in ["planned", "future"]:
            planned_versions.append(version)

    # Sort and return the first planned version
    if planned_versions:
        # Simple version sorting (assumes v.x.y.z format)
        planned_versions.sort(key=lambda v: tuple(map(int, v[1:].split("."))))
        return planned_versions[0]

    # Default increment
    major, minor, patch = __version_info__
    return f"v{major}.{minor + 1}.0"


def parse_version(version_string: str) -> tuple[int, int, int]:
    """Parse version string to tuple."""
    # Remove 'v' prefix if present
    version = version_string.lstrip("v")

    # Remove any suffix like -RC, -dev, etc
    if "-" in version:
        version = version.split("-")[0]

    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def increment_version(bump_type: str = "patch") -> str:
    """Increment version based on semantic versioning."""
    major, minor, patch = __version_info__

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def get_version_for_testing() -> dict[str, Any]:
    """Get version information formatted for testing frameworks."""
    return {
        "version": __version__,
        "version_tuple": __version_info__,
        "is_stable": __build__ == "stable",
        "environment": os.getenv("ENVIRONMENT", "development"),  # Read dynamically for testing
        "build_date": __release_date__,
    }


def get_version_for_docs() -> dict[str, Any]:
    """Get version information formatted for documentation."""
    current_info = get_current_roadmap_info()
    return {
        "version": __version__,
        "version_display": f"v{__version__}",
        "full_title": f"Second Brain v{__version__}",
        "subtitle": current_info.get("focus", "AI Memory System"),
        "codename": current_info.get("codename", "Unknown"),
        "release_date": __release_date__,
        "status": current_info.get("status", "current"),
        "badge_version": __version__.replace(".", "%2E"),  # URL encoded for badges
    }


def is_version_compatible(required_version: str) -> bool:
    """Check if current version is compatible with required version."""
    current = parse_version(__version__)
    required = parse_version(required_version)

    # Major version must match, minor version must be >= required
    return current[0] == required[0] and (
        current[1] > required[1] or (current[1] == required[1] and current[2] >= required[2])
    )


def get_cognitive_roadmap() -> dict[str, dict[str, Any]]:
    """Get the cognitive architecture evolution roadmap."""
    return {
        "v2.0.0": {
            "codename": "Phoenix",
            "focus": "Complete System Refactor",
            "features": [
                "90_percent_code_reduction",
                "single_postgresql_database",
                "pgvector_similarity_search",
                "simplified_dependencies",
                "direct_sql_access",
                "clean_architecture",
            ],
            "status": "completed",
            "release_date": "2024-11-30",
        },
        "v2.1.0": {
            "codename": "Cognitive",
            "focus": "Memory Type Classification",
            "features": [
                "memory_type_classification",
                "semantic_episodic_procedural",
                "intelligent_classification_engine",
                "contextual_search",
                "temporal_decay_modeling",
            ],
            "status": "completed",
            "release_date": "2024-12-15",
        },
        "v2.2.0": {
            "codename": "Visualization",
            "focus": "Interactive Memory Graphs",
            "features": [
                "memory_relationship_graphs",
                "d3js_visualizations",
                "advanced_search_interface",
                "analytics_insights",
                "network_analysis",
            ],
            "status": "completed",
            "release_date": "2025-01-17",
        },
        "v2.3.0": {
            "codename": "Organization",
            "focus": "Repository Structure & Testing",
            "features": [
                "repository_reorganization",
                "folder_structure_optimization",
                "comprehensive_testing",
                "vestigial_cleanup",
                "professional_standards",
            ],
            "status": "completed",
            "release_date": "2025-07-17",
        },
        "v2.4.0": {
            "codename": "Operations",
            "focus": "Advanced Bulk Operations",
            "features": [
                "bulk_import_export",
                "memory_deduplication",
                "batch_classification",
                "migration_tools",
                "performance_optimization",
            ],
            "status": "completed",
            "release_date": "2025-07-17",
        },
        "v2.4.1": {
            "codename": "Quality",
            "focus": "Documentation & Quality Improvements",
            "features": [
                "documentation_enhancement",
                "badge_accuracy",
                "version_consistency",
                "professional_standards",
                "license_compliance",
            ],
            "status": "released",
            "release_date": "2025-07-18",
        },
        "v2.4.2": {
            "codename": "Testing",
            "focus": "Legacy Cleanup & Testing Enhancement",
            "features": [
                "legacy_version_bump_removal",
                "centralized_version_management",
                "enhanced_testing_framework",
                "pr_validation_automation",
                "production_readiness_validation",
            ],
            "status": "completed",
            "release_date": "2025-07-19",
        },
        "v2.5.0": {
            "codename": "Intelligence",
            "focus": "AI-Powered Insights & Sophisticated Ingestion",
            "features": [
                "ai_powered_insights_engine",
                "pattern_detection_system",
                "memory_clustering_algorithms",
                "knowledge_gap_analysis",
                "entity_extraction_ner",
                "topic_modeling_classification",
                "relationship_detection",
                "intent_recognition",
                "automatic_embeddings",
                "structured_data_extraction",
            ],
            "status": "current",
            "release_date": "2025-07-21",
        },
        "v2.6.0": {
            "codename": "Collaboration",
            "focus": "Multi-user & Mobile Support",
            "features": [
                "real_time_collaboration",
                "mobile_interface",
                "advanced_migration_system",
                "shared_memory_spaces",
                "offline_capabilities",
            ],
            "status": "planned",
            "release_date": "2025-10-31",
        },
        "v3.0.0": {
            "codename": "Intelligence",
            "focus": "Next Generation AI",
            "features": [
                "gpt4_integration",
                "federated_learning",
                "enterprise_features",
                "natural_language_queries",
                "automated_memory_consolidation",
            ],
            "status": "future",
            "release_date": "2026-01-31",
        },
    }


# Legacy compatibility functions
def get_version_tuple() -> tuple[int, int, int]:
    """Get version as tuple (legacy compatibility)."""
    return __version_info__


def get_build_info() -> str:
    """Get build information (legacy compatibility)."""
    return __build__


def get_release_date() -> str:
    """Get release date (legacy compatibility)."""
    return __release_date__


# Export commonly used functions
__all__ = [
    "__version__",
    "__version_info__",
    "__build__",
    "__release_date__",
    "get_version",
    "get_version_info",
    "get_dashboard_version",
    "get_version_for_testing",
    "get_version_for_docs",
    "get_cognitive_roadmap",
    "increment_version",
    "is_version_compatible",
]
