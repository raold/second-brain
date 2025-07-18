"""
Second Brain Application Version Information
"""

__version__ = "2.4.0"
__version_info__ = (2, 4, 0)
__build__ = "stable"
__release_date__ = "2025-07-17"

# Roadmap metadata for cognitive architecture evolution
COGNITIVE_ROADMAP = {
    "v2.2.0": {
        "codename": "Cognitive",
        "focus": "Security & Optimization",
        "features": [
            "performance_benchmarking",
            "security_hardening",
            "connection_pooling",
            "rate_limiting",
            "input_validation",
            "monitoring_metrics",
        ],
        "status": "completed",
        "release_date": "2025-07-31",
    },
    
    
    "v2.3.0": {
        "codename": "Cognitive",
        "focus": "Memory Type Architecture",
        "features": [
            "semantic_memory",
            "episodic_memory", 
            "procedural_memory",
            "contextual_retrieval",
            "memory_classification",
            "intelligent_metadata",
        ],
        "status": "completed",
        "release_date": "2025-07-17",
    },
    "v3.0.0": {
        "codename": "Cognitive",
        "focus": "Unified Intelligence",
        "features": ["hybrid_search", "advanced_auth", "batch_operations", "analytics_foundation", "api_v2"],
        "target_date": "2025-08-14",
    },
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
