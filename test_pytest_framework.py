#!/usr/bin/env python3
"""
Test the pytest framework and our test infrastructure without database dependencies.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_pytest_basic():
    """Test that pytest is working correctly"""
    assert True
    assert 1 + 1 == 2
    assert "hello" in "hello world"

def test_mock_functionality():
    """Test that mocking works correctly"""
    mock_func = MagicMock(return_value="mocked")
    result = mock_func("arg")
    assert result == "mocked"
    mock_func.assert_called_once_with("arg")

@pytest.mark.asyncio
async def test_async_functionality():
    """Test async test capabilities"""
    async def async_func():
        await asyncio.sleep(0.01)
        return "async_result"
    
    result = await async_func()
    assert result == "async_result"

def test_parametrize():
    """Test parametrized testing"""
    test_cases = [
        (2, 3, 5),
        (10, 20, 30),
        (-1, 1, 0)
    ]
    
    for a, b, expected in test_cases:
        assert a + b == expected

class TestClassStructure:
    """Test class-based test organization"""
    
    def test_method1(self):
        assert "test" == "test"
    
    def test_method2(self):
        assert [1, 2, 3] == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        result = await asyncio.sleep(0.01, result="done")
        assert result == "done"

def test_test_files_exist():
    """Test that our comprehensive test files exist"""
    test_files = [
        "tests/unit/test_batch_processing.py",
        "tests/unit/test_security_comprehensive.py",
        "tests/unit/test_routes_comprehensive.py",
        "tests/unit/test_core_modules.py"
    ]
    
    existing_files = []
    missing_files = []
    
    for test_file in test_files:
        file_path = Path(test_file)
        if file_path.exists():
            existing_files.append(test_file)
        else:
            missing_files.append(test_file)
    
    print(f"Existing test files: {len(existing_files)}")
    print(f"Missing test files: {len(missing_files)}")
    
    # We should have at least some test files
    assert len(existing_files) > 0, f"No test files found. Missing: {missing_files}"

def test_pytest_ini_exists():
    """Test that pytest.ini configuration exists"""
    pytest_ini = Path("pytest.ini")
    assert pytest_ini.exists(), "pytest.ini should exist for test configuration"
    
    content = pytest_ini.read_text()
    assert "testpaths" in content, "pytest.ini should specify test paths"
    assert "asyncio_mode" in content, "pytest.ini should configure async mode"

def test_test_template_exists():
    """Test that test template exists for consistency"""
    template_path = Path("tests/test_template.py")
    # This is optional but good to have
    if template_path.exists():
        content = template_path.read_text()
        assert "import pytest" in content, "Template should include pytest import"
        assert "@pytest.mark.asyncio" in content, "Template should show async test example"

def test_requirements_for_testing():
    """Test that key testing requirements are met"""
    required_modules = [
        "pytest",
        "pytest_asyncio",
        "httpx",
        "pydantic",
        "fastapi"
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    assert len(missing_modules) == 0, f"Missing required modules: {missing_modules}"

@pytest.mark.asyncio
async def test_mock_database():
    """Test mock database functionality"""
    
    class MockDB:
        def __init__(self):
            self.data = {}
        
        async def create(self, key, value):
            self.data[key] = value
            return key
        
        async def get(self, key):
            return self.data.get(key)
        
        async def list_all(self):
            return list(self.data.values())
    
    db = MockDB()
    
    # Test create
    result = await db.create("key1", {"content": "test"})
    assert result == "key1"
    
    # Test get
    retrieved = await db.get("key1")
    assert retrieved == {"content": "test"}
    
    # Test list
    items = await db.list_all()
    assert len(items) == 1
    assert items[0] == {"content": "test"}

def test_configuration_validation():
    """Test that key configuration files are valid"""
    
    # Check pytest.ini
    pytest_ini = Path("pytest.ini")
    if pytest_ini.exists():
        content = pytest_ini.read_text()
        # Should not have syntax errors when parsed
        import configparser
        config = configparser.ConfigParser()
        config.read_string(content)
        assert "tool:pytest" in config.sections() or "pytest" in config.sections()
    
    # Check if we have test markers defined
    if pytest_ini.exists():
        content = pytest_ini.read_text()
        markers = ["unit", "integration", "performance", "asyncio", "slow"]
        
        found_markers = []
        for marker in markers:
            if marker in content:
                found_markers.append(marker)
        
        print(f"Found test markers: {found_markers}")
        assert len(found_markers) > 0, "Should have test markers defined"

def test_test_data_factories():
    """Test creating test data factories"""
    
    from dataclasses import dataclass
    from typing import List
    import random
    
    @dataclass
    class TestMemory:
        id: str
        content: str
        importance: float
        tags: List[str]
    
    class MemoryFactory:
        @staticmethod
        def create(content=None, importance=None, tags=None):
            return TestMemory(
                id=f"test_{random.randint(1000, 9999)}",
                content=content or "Test memory content",
                importance=importance or random.uniform(5.0, 9.0),
                tags=tags or ["test", "auto"]
            )
        
        @staticmethod
        def create_batch(count=5):
            return [MemoryFactory.create() for _ in range(count)]
    
    # Test single creation
    memory = MemoryFactory.create()
    assert memory.id.startswith("test_")
    assert len(memory.content) > 0
    assert 0 <= memory.importance <= 10
    assert len(memory.tags) > 0
    
    # Test batch creation
    memories = MemoryFactory.create_batch(3)
    assert len(memories) == 3
    assert all(isinstance(m, TestMemory) for m in memories)
    
    # Test custom parameters
    custom_memory = MemoryFactory.create(
        content="Custom content",
        importance=8.5,
        tags=["custom", "specific"]
    )
    assert custom_memory.content == "Custom content"
    assert custom_memory.importance == 8.5
    assert custom_memory.tags == ["custom", "specific"]

if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])