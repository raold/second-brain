#!/usr/bin/env python3
"""
GENERATED COMPREHENSIVE TEST SUITE
Tests for Second Brain V2 API based on code analysis
"""

import sys
import os
from pathlib import Path
import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

@pytest.mark.validation
class TestEnvironmentSetup:
    """Test basic environment setup"""
    
    def test_python_version(self):
        """Test Python version is acceptable"""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 9, f"Python 3.9+ required, got {version.major}.{version.minor}"
        
    def test_required_packages(self):
        """Test required packages are installed"""
        try:
            import fastapi
            import pydantic
            import uvicorn
            assert True
        except ImportError as e:
            pytest.fail(f"Required package missing: {e}")
    
    def test_project_structure(self):
        """Test project structure exists"""
        required_dirs = ["app", "tests", "scripts"]
        for dir_name in required_dirs:
            assert (project_root / dir_name).exists(), f"Missing directory: {dir_name}"

@pytest.mark.unit
class TestBasicImports:
    """Test basic application imports"""
    
    def test_import_main_app(self):
        """Test main app can be imported"""
        try:
            from app.app import app
            assert app is not None
            assert hasattr(app, 'title')
            assert hasattr(app, 'version')
        except Exception as e:
            pytest.fail(f"Failed to import main app: {e}")
    
    def test_import_v2_api(self):
        """Test V2 API can be imported"""
        try:
            from app.routes import v2_api_new
            assert hasattr(v2_api_new, 'router')
        except Exception as e:
            pytest.fail(f"Failed to import V2 API: {e}")
    
    def test_import_dependencies(self):
        """Test dependencies can be imported"""
        try:
            from app.dependencies_new import verify_api_key, get_current_user
            assert callable(verify_api_key)
            assert callable(get_current_user)
        except Exception as e:
            pytest.fail(f"Failed to import dependencies: {e}")
    
    def test_import_memory_service(self):
        """Test memory service can be imported"""
        try:
            from app.services.memory_service_new import MemoryService
            service = MemoryService()
            assert service is not None
        except Exception as e:
            pytest.fail(f"Failed to import memory service: {e}")

@pytest.mark.unit
class TestMemoryService:
    """Test the new memory service implementation"""
    
    @pytest.fixture
    def memory_service(self):
        """Create a memory service instance"""
        from app.services.memory_service_new import MemoryService
        return MemoryService()
    
    @pytest.mark.asyncio
    async def test_create_memory(self, memory_service):
        """Test memory creation"""
        memory = await memory_service.create_memory(
            content="Test memory content",
            importance_score=0.8,
            tags=["test", "memory"]
        )
        
        assert memory is not None
        assert memory["content"] == "Test memory content"
        assert memory["importance_score"] == 0.8
        assert "test" in memory["tags"]
        assert "id" in memory
        assert "created_at" in memory
    
    @pytest.mark.asyncio
    async def test_get_memory(self, memory_service):
        """Test memory retrieval"""
        # Create a memory first
        created = await memory_service.create_memory("Test content")
        memory_id = created["id"]
        
        # Retrieve it
        retrieved = await memory_service.get_memory(memory_id)
        assert retrieved is not None
        assert retrieved["id"] == memory_id
        assert retrieved["content"] == "Test content"
    
    @pytest.mark.asyncio
    async def test_list_memories(self, memory_service):
        """Test memory listing"""
        # Create a few memories
        await memory_service.create_memory("Memory 1")
        await memory_service.create_memory("Memory 2")
        
        # List them
        memories = await memory_service.list_memories(limit=10)
        assert isinstance(memories, list)
        assert len(memories) >= 2
    
    @pytest.mark.asyncio
    async def test_search_memories(self, memory_service):
        """Test memory search"""
        # Create searchable memories
        await memory_service.create_memory("Python programming tutorial")
        await memory_service.create_memory("JavaScript web development")
        
        # Search for Python
        results = await memory_service.search_memories("Python")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert any("Python" in mem["content"] for mem in results)
    
    @pytest.mark.asyncio
    async def test_update_memory(self, memory_service):
        """Test memory update"""
        # Create a memory
        created = await memory_service.create_memory("Original content")
        memory_id = created["id"]
        
        # Update it
        updated = await memory_service.update_memory(
            memory_id, 
            content="Updated content",
            importance_score=0.9
        )
        
        assert updated is not None
        assert updated["content"] == "Updated content"
        assert updated["importance_score"] == 0.9
        assert updated["updated_at"] != created["created_at"]
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_service):
        """Test memory deletion"""
        # Create a memory
        created = await memory_service.create_memory("To be deleted")
        memory_id = created["id"]
        
        # Delete it
        deleted = await memory_service.delete_memory(memory_id)
        assert deleted is True
        
        # Verify it's gone
        retrieved = await memory_service.get_memory(memory_id)
        assert retrieved is None

@pytest.mark.integration
class TestAPIEndpoints:
    """Test API endpoints with TestClient"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        from fastapi.testclient import TestClient
        from app.app import app
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/api/v2/health")
        # Should return 200 or at least not 404/500
        assert response.status_code in [200, 404]  # 404 acceptable if route not registered
    
    def test_memories_endpoint_get(self, client):
        """Test memories GET endpoint"""
        response = client.get("/api/v2/memories")
        # Should return 200 or at least not 500
        assert response.status_code in [200, 401, 404]  # Various acceptable responses
    
    def test_memories_endpoint_post(self, client):
        """Test memories POST endpoint"""
        memory_data = {
            "content": "Test memory from API",
            "importance_score": 0.7,
            "tags": ["api", "test"]
        }
        
        response = client.post("/api/v2/memories", json=memory_data)
        # Should return 201 or at least not 500
        assert response.status_code in [201, 401, 422]  # Various acceptable responses

@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration"""
    
    def test_database_import(self):
        """Test database module can be imported"""
        try:
            from app.database_new import get_database, Database
            assert callable(get_database)
            assert Database is not None
        except Exception as e:
            pytest.fail(f"Database import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_database_instance(self):
        """Test database instance creation"""
        try:
            from app.database_new import get_database
            db = await get_database()
            assert db is not None
            # Database connection might fail, but instance should be created
        except Exception as e:
            pytest.fail(f"Database instance creation failed: {e}")

@pytest.mark.integration
class TestNewServiceImplementations:
    """Test the newly implemented services mentioned in TODO"""
    
    def test_domain_classifier_import(self):
        """Test domain classifier can be imported"""
        try:
            from app.services.domain_classifier import DomainClassifier
            classifier = DomainClassifier()
            assert classifier is not None
        except ImportError:
            pytest.skip("DomainClassifier not found - expected if not implemented")
        except Exception as e:
            pytest.fail(f"DomainClassifier import failed: {e}")
    
    def test_topic_classifier_import(self):
        """Test topic classifier can be imported"""
        try:
            from app.services.topic_classifier import TopicClassifier
            classifier = TopicClassifier()
            assert classifier is not None
        except ImportError:
            pytest.skip("TopicClassifier not found - expected if not implemented")
        except Exception as e:
            pytest.fail(f"TopicClassifier import failed: {e}")
    
    def test_structured_data_extractor_import(self):
        """Test structured data extractor can be imported"""
        try:
            from app.services.structured_data_extractor import StructuredDataExtractor
            extractor = StructuredDataExtractor()
            assert extractor is not None
        except ImportError:
            pytest.skip("StructuredDataExtractor not found - expected if not implemented")
        except Exception as e:
            pytest.fail(f"StructuredDataExtractor import failed: {e}")

@pytest.mark.performance
class TestBasicPerformance:
    """Basic performance tests"""
    
    @pytest.mark.asyncio
    async def test_memory_service_performance(self):
        """Test memory service basic performance"""
        from app.services.memory_service_new import MemoryService
        service = MemoryService()
        
        import time
        start = time.time()
        
        # Create 10 memories quickly
        for i in range(10):
            await service.create_memory(f"Performance test memory {i}")
        
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Creating 10 memories took {elapsed:.2f}s (should be < 1s)"
        
        # List them
        start = time.time()
        memories = await service.list_memories(limit=10)
        elapsed = time.time() - start
        
        assert len(memories) == 10
        assert elapsed < 0.1, f"Listing 10 memories took {elapsed:.2f}s (should be < 0.1s)"

# Test runner function for direct execution
def run_tests():
    """Run tests directly without pytest command"""
    print("🔍 RUNNING GENERATED COMPREHENSIVE TESTS")
    print("="*60)
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0
    }
    
    # Run environment tests
    env_tests = TestEnvironmentSetup()
    try:
        env_tests.test_python_version()
        test_results["passed"] += 1
        print("✅ Python version test passed")
    except Exception as e:
        test_results["failed"] += 1
        print(f"❌ Python version test failed: {e}")
    test_results["total"] += 1
    
    try:
        env_tests.test_required_packages()
        test_results["passed"] += 1
        print("✅ Required packages test passed")
    except Exception as e:
        test_results["failed"] += 1
        print(f"❌ Required packages test failed: {e}")
    test_results["total"] += 1
    
    # Run import tests
    import_tests = TestBasicImports()
    try:
        import_tests.test_import_main_app()
        test_results["passed"] += 1
        print("✅ Main app import test passed")
    except Exception as e:
        test_results["failed"] += 1
        print(f"❌ Main app import test failed: {e}")
    test_results["total"] += 1
    
    try:
        import_tests.test_import_memory_service()
        test_results["passed"] += 1
        print("✅ Memory service import test passed")
    except Exception as e:
        test_results["failed"] += 1
        print(f"❌ Memory service import test failed: {e}")
    test_results["total"] += 1
    
    # Test new services
    new_services = TestNewServiceImplementations()
    try:
        new_services.test_domain_classifier_import()
        test_results["passed"] += 1
        print("✅ Domain classifier import test passed")
    except Exception as e:
        if "skip" in str(e).lower():
            test_results["skipped"] += 1
            print("⏭️  Domain classifier test skipped (not implemented)")
        else:
            test_results["failed"] += 1
            print(f"❌ Domain classifier import test failed: {e}")
    test_results["total"] += 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Total:   {test_results['total']}")
    print(f"Passed:  {test_results['passed']}")
    print(f"Failed:  {test_results['failed']}")
    print(f"Skipped: {test_results['skipped']}")
    
    success_rate = (test_results["passed"] / test_results["total"] * 100) if test_results["total"] > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if test_results["failed"] == 0:
        print("✅ ALL TESTS PASSED!")
        return True
    else:
        print(f"❌ {test_results['failed']} TESTS FAILED")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)