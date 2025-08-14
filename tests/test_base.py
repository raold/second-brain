"""
Base test class with platform and environment awareness

Provides intelligent test behavior based on:
- Platform (Windows, macOS, Linux)
- Environment (CI/CD, local dev)
- Database backend (mock, PostgreSQL)
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from typing import Any, Optional, Dict
from unittest import TestCase

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.platform_context import (
    get_platform_context,
    is_windows,
    is_macos,
    is_linux,
    is_ci,
    is_mock_database,
    PathHelper
)


class PlatformAwareTestCase(TestCase):
    """Base test class with platform awareness"""
    
    @classmethod
    def setUpClass(cls):
        """Setup class with platform context"""
        super().setUpClass()
        cls.context = get_platform_context()
        cls.is_ci = cls.context.is_ci
        cls.is_mock_db = cls.context.use_mock_database
        cls.platform = cls.context.platform_type.value
        
        # Platform-specific test data paths
        cls.test_data_dir = PathHelper.get_test_data_dir()
        cls.temp_dir = PathHelper.get_temp_dir()
        
        # Adjust test behavior based on platform
        if cls.context.is_ci:
            cls.timeout_multiplier = 0.5  # Faster in CI
        elif is_windows():
            cls.timeout_multiplier = 2.0  # Slower on Windows
        else:
            cls.timeout_multiplier = 1.0
    
    def setUp(self):
        """Setup test with context info"""
        super().setUp()
        
        # Skip tests that require real database if using mock
        if hasattr(self, 'requires_real_db') and self.requires_real_db:
            if self.is_mock_db:
                pytest.skip("Test requires real database")
        
        # Skip tests that require internet if not available
        if hasattr(self, 'requires_internet') and self.requires_internet:
            if not self.context.has_internet:
                pytest.skip("Test requires internet connection")
    
    def get_timeout(self, base_timeout: float) -> float:
        """Get platform-adjusted timeout"""
        return base_timeout * self.timeout_multiplier
    
    def get_test_file_path(self, filename: str) -> Path:
        """Get platform-appropriate test file path"""
        return self.test_data_dir / filename
    
    def normalize_line_endings(self, text: str) -> str:
        """Normalize line endings for comparison"""
        if is_windows():
            return text.replace('\n', '\r\n')
        else:
            return text.replace('\r\n', '\n')
    
    def assert_path_equal(self, path1: str, path2: str):
        """Assert paths are equal (platform-aware)"""
        p1 = PathHelper.normalize_path(path1)
        p2 = PathHelper.normalize_path(path2)
        self.assertEqual(str(p1), str(p2))
    
    def skip_on_ci(self, reason: str = "Skipped on CI"):
        """Skip test if running on CI"""
        if self.is_ci:
            pytest.skip(reason)
    
    def skip_on_platform(self, *platforms: str, reason: str = None):
        """Skip test on specific platforms"""
        if self.platform in platforms:
            reason = reason or f"Skipped on {self.platform}"
            pytest.skip(reason)
    
    def require_platform(self, *platforms: str):
        """Require specific platforms for test"""
        if self.platform not in platforms:
            pytest.skip(f"Test requires platform: {', '.join(platforms)}")


class AsyncPlatformAwareTestCase(PlatformAwareTestCase):
    """Async version of platform-aware test case"""
    
    def setUp(self):
        """Setup async test environment"""
        super().setUp()
        
        # Platform-specific event loop policy
        if is_windows():
            # Windows requires special event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        elif is_macos():
            # macOS might need special handling for fork safety
            os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    
    async def async_setUp(self):
        """Async setup hook"""
        pass
    
    async def async_tearDown(self):
        """Async teardown hook"""
        pass
    
    def run_async(self, coro):
        """Run async coroutine with platform-aware event loop"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class DatabaseAwareTestCase(AsyncPlatformAwareTestCase):
    """Test case with database awareness"""
    
    async def async_setUp(self):
        """Setup database connection based on context"""
        await super().async_setUp()
        
        if self.is_mock_db:
            from app.database_mock import MockDatabase
            self.db = MockDatabase()
            self.db.platform_context = self.context
            await self.db.initialize()
        else:
            from app.database import get_database
            self.db = await get_database()
    
    async def async_tearDown(self):
        """Cleanup database connection"""
        if self.is_mock_db and hasattr(self, 'db'):
            await self.db.close()
        await super().async_tearDown()
    
    async def assert_database_connected(self):
        """Assert database is properly connected"""
        if self.is_mock_db:
            self.assertTrue(self.db.is_connected)
        else:
            # Real database check
            result = await self.db.execute("SELECT 1")
            self.assertIsNotNone(result)
    
    def get_database_timeout(self) -> float:
        """Get database operation timeout based on backend"""
        if self.is_mock_db:
            return 1.0  # Fast for mock
        elif self.is_ci:
            return 5.0  # Medium for CI
        else:
            return 10.0  # Generous for local dev


class IntegrationTestCase(DatabaseAwareTestCase):
    """Integration test with full platform awareness"""
    
    @classmethod
    def setUpClass(cls):
        """Setup integration test environment"""
        super().setUpClass()
        
        # Check if integration tests should run
        if cls.context.is_ci and os.getenv("SKIP_INTEGRATION_TESTS") == "true":
            pytest.skip("Integration tests skipped in CI")
        
        # Ensure required services are available
        cls.check_required_services()
    
    @classmethod
    def check_required_services(cls):
        """Check that required services are available"""
        required = []
        
        if hasattr(cls, 'requires_docker') and cls.requires_docker:
            if not cls.context.has_docker:
                required.append("Docker")
        
        if hasattr(cls, 'requires_git') and cls.requires_git:
            if not cls.context.has_git:
                required.append("Git")
        
        if required:
            pytest.skip(f"Required services not available: {', '.join(required)}")
    
    async def create_test_data(self, count: int = 10) -> list:
        """Create test data appropriate for platform"""
        data = []
        
        for i in range(count):
            # Adjust data based on platform
            if is_windows():
                # Windows-specific test data
                path = f"C:\\test\\file_{i}.txt"
            else:
                # Unix-style paths
                path = f"/tmp/test/file_{i}.txt"
            
            data.append({
                "id": i,
                "path": path,
                "content": f"Test content {i}",
                "platform": self.platform
            })
        
        return data


def platform_skip(condition: bool, reason: str):
    """Decorator to skip tests based on platform condition"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if condition:
                pytest.skip(reason)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def requires_real_database(func):
    """Decorator to mark tests that require real database"""
    func.requires_real_db = True
    return func


def requires_internet(func):
    """Decorator to mark tests that require internet"""
    func.requires_internet = True
    return func


def ci_only(func):
    """Decorator to run test only in CI"""
    def wrapper(*args, **kwargs):
        if not is_ci():
            pytest.skip("Test only runs in CI")
        return func(*args, **kwargs)
    return wrapper


def local_only(func):
    """Decorator to run test only in local dev"""
    def wrapper(*args, **kwargs):
        if is_ci():
            pytest.skip("Test only runs in local development")
        return func(*args, **kwargs)
    return wrapper


# Platform-specific test markers
windows_only = pytest.mark.skipif(not is_windows(), reason="Windows only test")
macos_only = pytest.mark.skipif(not is_macos(), reason="macOS only test")
linux_only = pytest.mark.skipif(not is_linux(), reason="Linux only test")
mock_db_only = pytest.mark.skipif(not is_mock_database(), reason="Mock database only test")
real_db_only = pytest.mark.skipif(is_mock_database(), reason="Real database only test")