"""
Second Brain Application Version Information
"""

__version__ = "2.4.1"
__version_info__ = (2, 4, 1)
__build__ = "stable"
__release_date__ = "2025-07-18"

# Roadmap metadata for cognitive architecture evolution
COGNITIVE_ROADMAP = {
    "v2.0.0": {
        "codename": "Phoenix",
        "focus": "Complete System Refactor",
        "features": [
            "90_percent_code_reduction",
            "single_postgresql_database",
            "pgvector_similarity_search",
            "simplified_dependencies",
            "direct_sql_access",
            "clean_architecture"
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
            "temporal_decay_modeling"
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
            "network_analysis"
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
            "professional_standards"
        ],
        "status": "current",
        "release_date": "2025-07-17",
    },
    
    "v2.4.0": {
        "codename": "Performance",
        "focus": "Advanced Analytics & Optimization",
        "features": [
            "real_time_analytics_dashboard",
            "performance_optimization",
            "ai_powered_insights",
            "large_dataset_handling",
            "caching_strategies"
        ],
        "status": "current",
        "release_date": "2025-07-17",
    },
    
    "v2.5.0": {
        "codename": "Collaboration",
        "focus": "Multi-user & Mobile Support",
        "features": [
            "real_time_collaboration",
            "mobile_interface",
            "advanced_migration_system",
            "shared_memory_spaces",
            "offline_capabilities"
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
            "automated_memory_consolidation"
        ],
        "status": "future",
        "release_date": "2026-01-31",
    }
}

# Version metadata
VERSION_METADATA = {
    "version": __version__,
    "version_info": __version_info__,
    "build": __build__,
    "release_date": __release_date__,
    "codename": "Cognitive",  # v2.2.0 Performance & Security focus
    "stability": "stable",
    "api_version": "v1",
    "next_major_feature": "Cognitive Memory Architecture",
    "roadmap": COGNITIVE_ROADMAP,
}


def get_version_info():
    """Get formatted version information."""
    return {
        "version": __version__,
        "build": __build__,
        "release_date": __release_date__,
        "codename": VERSION_METADATA["codename"],
        "api_version": VERSION_METADATA["api_version"],
    }
