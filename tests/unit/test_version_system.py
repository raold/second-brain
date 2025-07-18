"""
Tests for the production-ready version management system
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.version import (
    __version__,
    __version_info__,
    get_version,
    get_version_info,
    get_dashboard_version,
    get_version_for_testing,
    get_version_for_docs,
    increment_version,
    is_version_compatible,
    parse_version,
    get_cognitive_roadmap,
    get_current_codename,
    get_next_planned_version
)


class TestVersionSystem:
    """Test the centralized version management system"""

    def test_basic_version_info(self):
        """Test basic version information is available"""
        assert __version__ is not None
        assert len(__version__.split('.')) == 3
        assert __version_info__ is not None
        assert len(__version_info__) == 3

    def test_get_version(self):
        """Test get_version returns current version"""
        version = get_version()
        assert version == __version__
        assert isinstance(version, str)

    def test_get_version_info(self):
        """Test comprehensive version information"""
        info = get_version_info()
        
        required_fields = [
            "version", "version_info", "build", "release_date",
            "build_timestamp", "git_commit", "environment",
            "version_string", "display_name", "codename", "roadmap_info"
        ]
        
        for field in required_fields:
            assert field in info, f"Missing field: {field}"
        
        assert info["version"] == __version__
        assert info["version_string"] == f"v{__version__}"
        assert info["display_name"] == f"Second Brain v{__version__}"

    def test_get_dashboard_version(self):
        """Test dashboard-specific version information"""
        dashboard_info = get_dashboard_version()
        
        required_fields = [
            "current", "display", "codename", "focus",
            "status", "release_date", "next_version"
        ]
        
        for field in required_fields:
            assert field in dashboard_info, f"Missing dashboard field: {field}"
        
        assert dashboard_info["current"] == f"v{__version__}"
        assert dashboard_info["display"] == f"v{__version__}"

    def test_get_version_for_testing(self):
        """Test testing-specific version information"""
        test_info = get_version_for_testing()
        
        required_fields = ["version", "version_tuple", "is_stable", "environment", "build_date"]
        
        for field in required_fields:
            assert field in test_info, f"Missing test field: {field}"
        
        assert test_info["version"] == __version__
        assert test_info["version_tuple"] == __version_info__
        assert isinstance(test_info["is_stable"], bool)

    def test_get_version_for_docs(self):
        """Test documentation-specific version information"""
        docs_info = get_version_for_docs()
        
        required_fields = [
            "version", "version_display", "full_title", "subtitle",
            "codename", "release_date", "status", "badge_version"
        ]
        
        for field in required_fields:
            assert field in docs_info, f"Missing docs field: {field}"
        
        assert docs_info["version"] == __version__
        assert docs_info["version_display"] == f"v{__version__}"
        assert docs_info["full_title"] == f"Second Brain v{__version__}"
        assert "%2E" in docs_info["badge_version"]  # URL encoded dots

    def test_parse_version(self):
        """Test version string parsing"""
        test_cases = [
            ("1.2.3", (1, 2, 3)),
            ("v1.2.3", (1, 2, 3)),
            ("2.0.0", (2, 0, 0)),
            ("v10.5.2", (10, 5, 2))
        ]
        
        for version_str, expected in test_cases:
            result = parse_version(version_str)
            assert result == expected, f"Failed to parse {version_str}"

    def test_increment_version(self):
        """Test version increment functionality"""
        test_cases = [
            ("patch", "2.4.2"),
            ("minor", "2.5.0"),
            ("major", "3.0.0")
        ]
        
        for bump_type, expected in test_cases:
            result = increment_version(bump_type)
            assert result == expected, f"Failed {bump_type} increment"

    def test_increment_version_invalid(self):
        """Test invalid version increment raises error"""
        with pytest.raises(ValueError):
            increment_version("invalid")

    def test_is_version_compatible(self):
        """Test version compatibility checking"""
        test_cases = [
            ("2.4.0", True),   # Same minor, earlier patch
            ("2.4.1", True),   # Exact match
            ("2.3.0", True),   # Earlier minor
            ("2.5.0", False),  # Later minor
            ("3.0.0", False),  # Later major
            ("1.9.9", False),  # Earlier major
        ]
        
        for required_version, expected in test_cases:
            result = is_version_compatible(required_version)
            assert result == expected, f"Compatibility check failed for {required_version}"

    def test_get_cognitive_roadmap(self):
        """Test roadmap information"""
        roadmap = get_cognitive_roadmap()
        
        assert isinstance(roadmap, dict)
        assert len(roadmap) > 0
        
        # Check current version exists in roadmap
        current_key = f"v{__version__}"
        assert current_key in roadmap, f"Current version {current_key} not in roadmap"
        
        # Check roadmap structure
        for version, info in roadmap.items():
            required_fields = ["codename", "focus", "features", "status", "release_date"]
            for field in required_fields:
                assert field in info, f"Missing roadmap field {field} in {version}"

    def test_get_current_codename(self):
        """Test current version codename"""
        codename = get_current_codename()
        assert isinstance(codename, str)
        assert len(codename) > 0

    def test_get_next_planned_version(self):
        """Test next planned version detection"""
        next_version = get_next_planned_version()
        assert isinstance(next_version, str)
        assert next_version.startswith("v")
        
        # Should be a valid version format
        version_part = next_version[1:]  # Remove 'v'
        parts = version_part.split('.')
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    @patch.dict('os.environ', {'GIT_COMMIT': 'abc123def456'})
    def test_environment_variables(self):
        """Test environment variable integration"""
        info = get_version_info()
        assert info["git_commit"] == "abc123def456"

    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_environment_production(self):
        """Test production environment detection"""
        info = get_version_info()
        assert info["environment"] == "production"


class TestVersionEndpoint:
    """Test the version API endpoint functionality"""

    def test_version_endpoint_structure(self):
        """Test that version endpoint returns proper structure"""
        # This would be tested in integration tests with actual API calls
        # Here we just test the data structure
        from app.version import get_dashboard_version, get_version_info
        
        version_info = get_version_info()
        dashboard_info = get_dashboard_version()
        
        expected_response = {
            "version": version_info["version"],
            "version_string": version_info["version_string"],
            "display_name": version_info["display_name"],
            "codename": version_info["codename"],
            "release_date": version_info["release_date"],
            "build": version_info["build"],
            "environment": version_info["environment"],
            "git_commit": version_info["git_commit"],
            "build_timestamp": version_info["build_timestamp"],
            "dashboard": dashboard_info,
            "roadmap": version_info["roadmap_info"]
        }
        
        # Verify all required fields are present
        for field in expected_response:
            assert field in expected_response
        
        # Verify data types
        assert isinstance(expected_response["version"], str)
        assert isinstance(expected_response["dashboard"], dict)
        assert isinstance(expected_response["roadmap"], dict)


class TestVersionBumpIntegration:
    """Test version bump script integration"""

    def test_version_patterns(self):
        """Test that version patterns work with current version"""
        from scripts.version_bump import ProductionVersionBumper
        
        bumper = ProductionVersionBumper()
        current_version = bumper.get_current_version()
        
        assert current_version == __version__
        
        # Test version calculations
        new_patch = bumper.calculate_new_version("patch")
        new_minor = bumper.calculate_new_version("minor") 
        new_major = bumper.calculate_new_version("major")
        
        # Verify proper increments
        current_parts = __version__.split('.')
        major, minor, patch = map(int, current_parts)
        
        assert new_patch == f"{major}.{minor}.{patch + 1}"
        assert new_minor == f"{major}.{minor + 1}.0"
        assert new_major == f"{major + 1}.0.0"


if __name__ == "__main__":
    pytest.main([__file__]) 