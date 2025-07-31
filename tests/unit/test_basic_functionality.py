"""
Basic functionality tests for Second Brain application
"""


import pytest


class TestBasicImports:
    """Test that all critical imports work"""

    def test_fastapi_import(self):
        """Test FastAPI import"""
        import fastapi
        assert hasattr(fastapi, 'FastAPI')

    def test_pydantic_import(self):
        """Test Pydantic import"""
        import pydantic
        assert hasattr(pydantic, 'BaseModel')

    def test_uvicorn_import(self):
        """Test Uvicorn import"""
        import uvicorn
        assert hasattr(uvicorn, 'run')

    def test_app_import(self):
        """Test app module import"""
        from app import app
        assert hasattr(app, 'app')

    def test_models_import(self):
        """Test models import"""
        from app.models.memory import Memory, MemoryType
        assert Memory is not None
        assert MemoryType is not None

    def test_database_mock_import(self):
        """Test database mock import"""
        from app.database_mock import MockDatabase
        assert MockDatabase is not None


class TestAppInitialization:
    """Test application initialization"""

    def test_app_creation(self):
        """Test FastAPI app creation"""
        from fastapi import FastAPI
        app = FastAPI()
        assert app is not None
        assert hasattr(app, 'include_router')

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
    async def test_mock_database_initialization(self):
        """Test mock database initialization"""
        from app.database_mock import MockDatabase

        mock_db = MockDatabase()
        await mock_db.initialize()

        assert mock_db.memories == {}
        assert mock_db.users == {}
        assert mock_db.sessions == {}

        await mock_db.close()


class TestEnvironmentSetup:
    """Test environment setup for testing"""

    def test_environment_variables(self):
        """Test required environment variables are set"""
        import os

        # These should be set by conftest.py
        assert os.environ.get("ENVIRONMENT") == "test"
        assert os.environ.get("USE_MOCK_DATABASE") == "true"
        assert os.environ.get("API_TOKENS") is not None

    def test_pythonpath_setup(self):
        """Test Python path is set correctly"""
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        assert str(project_root) in sys.path


class TestErrorHandling:
    """Test basic error handling"""

    def test_import_error_handling(self):
        """Test handling of import errors"""
        try:
            import nonexistent_module
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
        from pathlib import Path

        current_file = Path(__file__)
        assert current_file.exists()
        assert current_file.is_file()
        assert current_file.suffix == ".py"
