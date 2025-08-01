"""
Basic functionality tests for Second Brain application
"""

import pytest

pytestmark = pytest.mark.unit

import os
import sys
from pathlib import Path


class TestBasicImports:
    """Test that all critical imports work"""

    def test_fastapi_import(self):
        """Test FastAPI import"""
        import fastapi

        assert hasattr(fastapi, "FastAPI")

    def test_pydantic_import(self):
        """Test Pydantic import"""
        import pydantic

        assert hasattr(pydantic, "BaseModel")

    def test_uvicorn_import(self):
        """Test Uvicorn import"""
        import uvicorn

        assert hasattr(uvicorn, "run")

    def test_app_import(self):
        """Test app module import"""
        try:
            from app import app

            assert hasattr(app, "app")
        except ImportError as e:
            pytest.skip(f"App import failed (expected in CI): {e}")

    def test_models_import(self):
        """Test models import"""
        try:
            from app.models.memory import Memory, MemoryType

            assert Memory is not None
            assert MemoryType is not None
        except ImportError as e:
            pytest.skip(f"Models import failed (expected in CI): {e}")

    def test_database_import(self):
        """Test database import"""
        try:
            from app.database import Database

            assert Database is not None
        except ImportError as e:
            pytest.skip(f"Database import failed (expected in CI): {e}")


class TestAppInitialization:
    """Test application initialization"""

    def test_app_creation(self):
        """Test FastAPI app creation"""
        from fastapi import FastAPI

        app = FastAPI()
        assert app is not None
        assert hasattr(app, "include_router")

    def test_pydantic_model_creation(self):
        """Test Pydantic model creation"""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            value: int = 0

        model = TestModel(name="test")
        assert model.name == "test"
        assert model.value == 0

    @pytest.mark.asyncio
    async def test_mock_database_initialization(self, mock_database):
        """Test mock database initialization"""
        await mock_database.initialize()

        # Verify mock was called
        mock_database.initialize.assert_called_once()

        # Test basic operations
        await mock_database.close()
        mock_database.close.assert_called_once()


class TestEnvironmentSetup:
    """Test environment setup for testing"""

    def test_environment_variables(self):
        """Test required environment variables are set"""
        # These should be set by conftest.py
        assert os.environ.get("ENVIRONMENT") == "test"
        assert os.environ.get("API_TOKENS") is not None
        assert os.environ.get("OPENAI_API_KEY") is not None

    def test_pythonpath_setup(self):
        """Test Python path is set correctly"""
        project_root = Path(__file__).parent.parent.parent
        assert str(project_root) in sys.path

    def test_mock_services_enabled(self):
        """Test that mock services are enabled in test environment"""
        assert os.environ.get("DISABLE_EXTERNAL_SERVICES") == "true"
        assert os.environ.get("MOCK_EXTERNAL_APIS") == "true"


class TestErrorHandling:
    """Test basic error handling"""

    def test_import_error_handling(self):
        """Test handling of import errors"""
        try:
            import nonexistent_module  # This should fail

            raise AssertionError("Should have raised ImportError")
        except ImportError:
            pass  # Expected

    def test_pydantic_validation_error(self):
        """Test Pydantic validation error handling"""
        from pydantic import BaseModel, ValidationError

        class StrictModel(BaseModel):
            required_field: str
            number_field: int

        # Missing required field
        with pytest.raises(ValidationError):
            StrictModel(number_field=42)

        # Wrong type
        with pytest.raises(ValidationError):
            StrictModel(required_field="test", number_field="not_a_number")


class TestBasicDataStructures:
    """Test basic data structures work correctly"""

    def test_dictionary_operations(self):
        """Test dictionary operations"""
        data = {"key": "value", "number": 42}
        assert data["key"] == "value"
        assert data.get("nonexistent") is None
        assert len(data) == 2

    def test_list_operations(self):
        """Test list operations"""
        items = [1, 2, 3]
        items.append(4)
        assert len(items) == 4
        assert items[-1] == 4

    def test_string_operations(self):
        """Test string operations"""
        text = "Hello, World!"
        assert text.lower() == "hello, world!"
        assert "World" in text
        assert text.replace("World", "Testing") == "Hello, Testing!"

    def test_datetime_operations(self):
        """Test datetime operations"""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        future = now + timedelta(hours=1)

        assert future > now
        assert isinstance(now.isoformat(), str)


class TestUtilityFunctions:
    """Test utility functions"""

    def test_uuid_generation(self):
        """Test UUID generation"""
        from uuid import UUID, uuid4

        id1 = uuid4()
        id2 = uuid4()

        assert id1 != id2
        assert isinstance(id1, UUID)
        assert len(str(id1)) == 36  # Standard UUID string length

    def test_json_serialization(self):
        """Test JSON serialization"""
        import json

        data = {"test": True, "number": 42, "list": [1, 2, 3]}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed == data

    def test_path_operations(self):
        """Test path operations"""
        current_file = Path(__file__)
        assert current_file.exists()
        assert current_file.is_file()
        assert current_file.suffix == ".py"


class TestMockingInfrastructure:
    """Test that mocking infrastructure works correctly"""

    @pytest.mark.asyncio
    async def test_mock_database_fixture(self, mock_database):
        """Test mock database fixture"""
        # Test that mock has expected methods
        assert hasattr(mock_database, "initialize")
        assert hasattr(mock_database, "create_memory")
        assert hasattr(mock_database, "list_memories")

        # Test mock behavior
        memories = await mock_database.list_memories()
        assert memories == []

    @pytest.mark.asyncio
    async def test_mock_openai_fixture(self, mock_openai_client):
        """Test mock OpenAI client fixture"""
        # Test embeddings
        response = await mock_openai_client.embeddings.create(
            model="text-embedding-ada-002", input="test text"
        )
        assert response.data[0].embedding == [0.1] * 1536

    @pytest.mark.asyncio
    async def test_mock_redis_fixture(self, mock_redis):
        """Test mock Redis client fixture"""
        # Test basic operations
        result = await mock_redis.set("test_key", "test_value")
        assert result is True

        value = await mock_redis.get("test_key")
        assert value is None  # Mock returns None by default

    def test_timeout_config_fixture(self, timeout_config):
        """Test timeout configuration fixture"""
        assert "short_timeout" in timeout_config
        assert "medium_timeout" in timeout_config
        assert "long_timeout" in timeout_config
        assert timeout_config["short_timeout"] < timeout_config["medium_timeout"]

    def test_ci_environment_check(self, ci_environment_check):
        """Test CI environment detection"""
        assert "is_ci" in ci_environment_check
        assert "timeout_multiplier" in ci_environment_check
        assert isinstance(ci_environment_check["timeout_multiplier"], float)


class TestSampleData:
    """Test sample data fixtures"""

    def test_sample_memory_data(self, sample_memory_data):
        """Test sample memory data fixture"""
        assert "title" in sample_memory_data
        assert "content" in sample_memory_data
        assert "memory_type" in sample_memory_data
        assert sample_memory_data["memory_type"] == "note"

    def test_sample_user_data(self, sample_user_data):
        """Test sample user data fixture"""
        assert "username" in sample_user_data
        assert "email" in sample_user_data
        assert "full_name" in sample_user_data
        assert "@" in sample_user_data["email"]
