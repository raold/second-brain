"""
Tests for enhanced dashboard module.
Simple tests focusing on import, instantiation, and basic functionality.
"""

import pytest
from datetime import datetime
from app.enhanced_dashboard import EnhancedDashboardData


class TestEnhancedDashboardData:
    """Test EnhancedDashboardData class."""

    def test_initialization(self):
        dashboard = EnhancedDashboardData()
        
        assert dashboard.project_root is not None
        assert isinstance(dashboard.timestamp, datetime)

    def test_get_comprehensive_dashboard_data_structure(self):
        dashboard = EnhancedDashboardData()
        
        data = dashboard.get_comprehensive_dashboard_data()
        
        # Check that all expected top-level keys are present
        expected_keys = {
            "meta", "version", "environment", "api_status", 
            "build_metrics", "timeline", "woodchipper", 
            "documentation", "roadmap", "changelog", "quality_metrics"
        }
        
        assert isinstance(data, dict)
        assert set(data.keys()) == expected_keys

    def test_meta_info_structure(self):
        dashboard = EnhancedDashboardData()
        
        meta = dashboard._get_meta_info()
        
        assert isinstance(meta, dict)
        assert "dashboard_version" in meta
        assert "generated_at" in meta
        assert "last_updated" in meta
        assert meta["dashboard_version"] == "2.5.2-RC-enhanced"

    def test_version_info_structure(self):
        dashboard = EnhancedDashboardData()
        
        version_info = dashboard._get_version_info()
        
        assert isinstance(version_info, dict)

    def test_environment_info_structure(self):
        dashboard = EnhancedDashboardData()
        
        env_info = dashboard._get_environment_info()
        
        assert isinstance(env_info, dict)

    def test_api_status_structure(self):
        dashboard = EnhancedDashboardData()
        
        api_status = dashboard._get_api_status()
        
        assert isinstance(api_status, dict)

    def test_build_metrics_structure(self):
        dashboard = EnhancedDashboardData()
        
        build_metrics = dashboard._get_build_metrics()
        
        assert isinstance(build_metrics, dict)

    def test_timeline_data_structure(self):
        dashboard = EnhancedDashboardData()
        
        timeline = dashboard._get_timeline_data()
        
        assert isinstance(timeline, dict)

    def test_woodchipper_data_structure(self):
        dashboard = EnhancedDashboardData()
        
        woodchipper = dashboard._get_woodchipper_data()
        
        assert isinstance(woodchipper, dict)

    def test_documentation_status_structure(self):
        dashboard = EnhancedDashboardData()
        
        docs = dashboard._get_documentation_status()
        
        assert isinstance(docs, dict)

    def test_roadmap_progress_structure(self):
        dashboard = EnhancedDashboardData()
        
        roadmap = dashboard._get_roadmap_progress()
        
        assert isinstance(roadmap, dict)

    def test_changelog_info_structure(self):
        dashboard = EnhancedDashboardData()
        
        changelog = dashboard._get_changelog_info()
        
        assert isinstance(changelog, dict)

    def test_quality_metrics_structure(self):
        dashboard = EnhancedDashboardData()
        
        quality = dashboard._get_quality_metrics()
        
        assert isinstance(quality, dict)

    def test_timestamp_consistency(self):
        dashboard = EnhancedDashboardData()
        
        # The timestamp should be set during initialization
        initial_timestamp = dashboard.timestamp
        
        # Getting data should use the same timestamp
        data = dashboard.get_comprehensive_dashboard_data()
        meta = data["meta"]
        
        assert meta["generated_at"] == initial_timestamp.isoformat()
        assert meta["last_updated"] == initial_timestamp.isoformat()
