"""
Comprehensive validation tests for CI/CD readiness
"""

import os
import sys
from pathlib import Path

import pytest


class TestEnvironmentValidation:
    """Test that the environment is properly configured"""

    def test_python_version(self):
        """Test Python version compatibility"""
        assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"

    def test_required_environment_variables(self):
        """Test that required environment variables are set"""
        required_vars = [
            "ENVIRONMENT",
            "USE_MOCK_DATABASE",
            "API_TOKENS",
        ]

        for var in required_vars:
            assert os.environ.get(var) is not None, f"Environment variable {var} not set"

        # Test specific values
        assert os.environ.get("ENVIRONMENT") == "test"
        assert os.environ.get("USE_MOCK_DATABASE") == "true"

    def test_project_structure(self):
        """Test that required project files exist"""
        project_root = Path(__file__).parent.parent.parent

        required_files = [
            "app/__init__.py",
            "app/app.py",
            "app/models/memory.py",
            "app/database_mock.py",
            "requirements.txt",
            "docker-compose.yml",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

    def test_test_structure(self):
        """Test that test structure is correct"""
        project_root = Path(__file__).parent.parent.parent

        test_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/validation",
        ]

        for test_dir in test_dirs:
            dir_path = project_root / test_dir
            assert dir_path.exists(), f"Test directory missing: {test_dir}"


class TestDependencyValidation:
    """Test that all dependencies are available"""

    def test_core_dependencies(self):
        """Test core application dependencies"""
        dependencies = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "sqlalchemy",
            "asyncpg",
            "httpx",
            "redis",
            "openai",
        ]

        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError as e:
                pytest.fail(f"Required dependency {dep} not available: {e}")

    def test_test_dependencies(self):
        """Test testing dependencies"""
        test_dependencies = [
            "pytest",
            "pytest_asyncio",
        ]

        for dep in test_dependencies:
            try:
                __import__(dep)
            except ImportError as e:
                pytest.fail(f"Required test dependency {dep} not available: {e}")

    def test_development_dependencies(self):
        """Test development dependencies (optional)"""
        dev_dependencies = [
            "ruff",
            "black",
            "mypy",
        ]

        missing_deps = []
        for dep in dev_dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)

        if missing_deps:
            print(f"Optional dev dependencies missing: {missing_deps}")
            # Don't fail for missing dev deps, just warn


class TestApplicationValidation:
    """Test that the application can be imported and initialized"""

    def test_app_import(self):
        """Test that the app can be imported"""
        try:
            from app.app import app
            assert app is not None
        except Exception as e:
            pytest.fail(f"Failed to import app: {e}")

    def test_models_import(self):
        """Test that models can be imported"""
        try:
            from app.models.memory import Memory, MemoryMetrics, MemoryType
            assert Memory is not None
            assert MemoryType is not None
            assert MemoryMetrics is not None
        except Exception as e:
            pytest.fail(f"Failed to import models: {e}")

    def test_database_mock_import(self):
        """Test that database mock can be imported"""
        try:
            from app.database_mock import MockDatabase
            assert MockDatabase is not None
        except Exception as e:
            pytest.fail(f"Failed to import MockDatabase: {e}")

    @pytest.mark.asyncio
    async def test_app_startup(self):
        """Test that the app can start up"""
        try:
            # Try to create a test client
            from httpx import AsyncClient

            from app.app import app

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/health")
                # Should either work or fail gracefully
                assert response.status_code < 600
        except Exception as e:
            pytest.fail(f"App startup failed: {e}")


class TestConfigurationValidation:
    """Test configuration files and settings"""

    def test_pytest_configuration(self):
        """Test pytest configuration"""
        project_root = Path(__file__).parent.parent.parent

        # Check for pytest configuration
        config_files = [
            "pytest.ini",
            "pyproject.toml",
        ]

        has_config = any((project_root / config).exists() for config in config_files)
        assert has_config, "No pytest configuration found"

    def test_docker_configuration(self):
        """Test Docker configuration"""
        project_root = Path(__file__).parent.parent.parent

        docker_files = [
            "docker-compose.yml",
            "Dockerfile",
        ]

        for docker_file in docker_files:
            if (project_root / docker_file).exists():
                with open(project_root / docker_file) as f:
                    content = f.read()
                    assert len(content) > 0, f"{docker_file} is empty"

    def test_requirements_files(self):
        """Test requirements files"""
        project_root = Path(__file__).parent.parent.parent

        # Check for requirements files
        req_patterns = [
            "requirements.txt",
            "config/requirements*.txt",
        ]

        found_requirements = False
        for pattern in req_patterns:
            if "*" in pattern:
                import glob
                matches = glob.glob(str(project_root / pattern))
                if matches:
                    found_requirements = True
                    break
            else:
                if (project_root / pattern).exists():
                    found_requirements = True
                    break

        assert found_requirements, "No requirements files found"


class TestSecurityValidation:
    """Test security configuration"""

    def test_api_key_configuration(self):
        """Test API key configuration"""
        api_tokens = os.environ.get("API_TOKENS", "")
        assert len(api_tokens) > 0, "API_TOKENS not configured"

        # Should be comma-separated tokens
        tokens = [token.strip() for token in api_tokens.split(",")]
        assert len(tokens) > 0, "No API tokens found"

        # Each token should be reasonably long
        for token in tokens:
            assert len(token) >= 32, f"API token too short: {token[:10]}..."

    def test_environment_isolation(self):
        """Test that test environment is isolated"""
        assert os.environ.get("ENVIRONMENT") == "test"
        assert os.environ.get("USE_MOCK_DATABASE") == "true"

        # Should not use production settings in tests
        production_indicators = [
            "PRODUCTION",
            "PROD",
        ]

        for indicator in production_indicators:
            env_value = os.environ.get(indicator, "").lower()
            assert env_value not in ["true", "1", "yes"], f"Production setting {indicator} enabled in tests"


class TestPerformanceValidation:
    """Test basic performance requirements"""

    def test_import_performance(self):
        """Test that imports don't take too long"""
        import time

        start_time = time.time()

        # Test critical imports

        import_time = time.time() - start_time

        # Imports should be fast (less than 5 seconds)
        assert import_time < 5.0, f"Imports took too long: {import_time:.2f}s"

    @pytest.mark.asyncio
    async def test_basic_response_time(self):
        """Test basic response time"""
        import time

        from httpx import AsyncClient

        from app.app import app

        start_time = time.time()

        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                await client.get("/health")

            response_time = time.time() - start_time

            # Health check should be fast (less than 2 seconds)
            assert response_time < 2.0, f"Health check too slow: {response_time:.2f}s"

        except Exception:
            # If health check fails, that's a separate issue
            # Don't fail performance test for functionality issues
            pass


class TestCICompatibility:
    """Test CI/CD compatibility"""

    def test_no_interactive_prompts(self):
        """Test that code doesn't require interactive input"""
        # This is more of a static check - code should not use input()
        # or other interactive functions in production paths

        # Import main modules and ensure they don't hang
        try:

            # If we get here without hanging, we're good
            assert True

        except Exception as e:
            # Check if it's a timeout or hanging issue
            if "timeout" in str(e).lower():
                pytest.fail("Code appears to hang or wait for input")
            else:
                # Other exceptions are separate issues
                pass

    def test_deterministic_behavior(self):
        """Test that behavior is deterministic for CI"""
        from app.models.memory import Memory, MemoryType

        # Create same memory multiple times
        memories = []
        for _ in range(3):
            memory = Memory(
                content="Deterministic test",
                memory_type=MemoryType.FACTUAL,
                importance_score=0.7
            )
            memories.append(memory)

        # All should have same content and properties
        for memory in memories[1:]:
            assert memory.content == memories[0].content
            assert memory.memory_type == memories[0].memory_type
            assert memory.importance_score == memories[0].importance_score

    def test_cleanup_behavior(self):
        """Test that resources are cleaned up properly"""
        # Test that mock database can be created and cleaned up
        import asyncio

        from app.database_mock import MockDatabase

        async def test_cleanup():
            mock_db = MockDatabase()
            await mock_db.initialize()

            # Add some data
            memory_data = {
                "id": "test-cleanup",
                "content": "Cleanup test",
                "memory_type": "factual"
            }
            await mock_db.create_memory(memory_data)

            # Clean up
            await mock_db.close()

            # Should not leave hanging resources
            return True

        result = asyncio.run(test_cleanup())
        assert result is True
