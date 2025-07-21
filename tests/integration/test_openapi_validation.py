"""
OpenAPI Documentation Validation Test
Tests comprehensive OpenAPI documentation functionality
"""

import time
from datetime import datetime

import requests

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "test_token"


def test_openapi_endpoints():
    """Test all endpoints for OpenAPI compliance and documentation"""

    print("🔍 Testing OpenAPI Documentation Validation")
    print("=" * 50)

    # Test 1: OpenAPI Schema Availability
    print("\n1. Testing OpenAPI Schema Availability")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        assert response.status_code == 200, f"OpenAPI schema failed: {response.status_code}"
        schema = response.json()
        assert "openapi" in schema, "Missing OpenAPI version"
        assert "info" in schema, "Missing API info"
        assert "paths" in schema, "Missing API paths"
        print("✅ OpenAPI schema available and valid")
    except Exception as e:
        print(f"❌ OpenAPI schema test failed: {e}")
        return False

    # Test 2: Health Endpoint with Response Model
    print("\n2. Testing Health Endpoint Response Model")
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
        data = response.json()
        assert "status" in data, "Missing status field"
        assert "version" in data, "Missing version field"
        assert "timestamp" in data, "Missing timestamp field"
        assert data["status"] == "healthy", "Incorrect status"
        assert data["version"] == "2.5.2-RC", "Incorrect version"
        print("✅ Health endpoint response model working")
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

    # Test 3: Status Endpoint with Authentication
    print("\n3. Testing Status Endpoint with Authentication")
    try:
        response = requests.get(f"{BASE_URL}/status?api_key={API_KEY}")
        assert response.status_code == 200, f"Status endpoint failed: {response.status_code}"
        data = response.json()
        assert "database" in data, "Missing database field"
        assert "index_status" in data, "Missing index_status field"
        assert "recommendations" in data, "Missing recommendations field"
        assert data["database"] == "connected", "Database not connected"
        print("✅ Status endpoint response model working")
    except Exception as e:
        print(f"❌ Status endpoint test failed: {e}")
        return False

    # Test 4: Memory Storage with Request/Response Models
    print("\n4. Testing Memory Storage with Request/Response Models")
    try:
        memory_data = {
            "content": "OpenAPI test memory content",
            "metadata": {"type": "test", "priority": "high", "timestamp": datetime.now().isoformat()},
        }

        response = requests.post(f"{BASE_URL}/memories?api_key={API_KEY}", json=memory_data)
        assert response.status_code == 200, f"Memory storage failed: {response.status_code}"
        data = response.json()
        assert "id" in data, "Missing memory id"
        assert "content" in data, "Missing content field"
        assert "metadata" in data, "Missing metadata field"
        assert data["content"] == memory_data["content"], "Content mismatch"

        memory_id = data["id"]
        print(f"✅ Memory stored with ID: {memory_id}")

        # Test 5: Memory Retrieval
        print("\n5. Testing Memory Retrieval")
        response = requests.get(f"{BASE_URL}/memories/{memory_id}?api_key={API_KEY}")
        assert response.status_code == 200, f"Memory retrieval failed: {response.status_code}"
        data = response.json()
        assert data["id"] == memory_id, "Memory ID mismatch"
        assert data["content"] == memory_data["content"], "Content mismatch"
        print("✅ Memory retrieval working")

        # Test 6: Memory Search
        print("\n6. Testing Memory Search")
        search_data = {"query": "OpenAPI test", "limit": 5}

        response = requests.post(f"{BASE_URL}/memories/search?api_key={API_KEY}", json=search_data)
        assert response.status_code == 200, f"Memory search failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Search results should be a list"
        if data:  # If we have results
            assert "id" in data[0], "Missing id in search results"
            assert "content" in data[0], "Missing content in search results"
            assert "similarity" in data[0], "Missing similarity in search results"
        print("✅ Memory search working")

        # Test 7: Memory List with Pagination
        print("\n7. Testing Memory List with Pagination")
        response = requests.get(f"{BASE_URL}/memories?api_key={API_KEY}&limit=10&offset=0")
        assert response.status_code == 200, f"Memory list failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Memory list should be a list"
        if data:  # If we have memories
            assert "id" in data[0], "Missing id in memory list"
            assert "content" in data[0], "Missing content in memory list"
        print("✅ Memory list with pagination working")

        # Test 8: Memory Deletion
        print("\n8. Testing Memory Deletion")
        response = requests.delete(f"{BASE_URL}/memories/{memory_id}?api_key={API_KEY}")
        assert response.status_code == 200, f"Memory deletion failed: {response.status_code}"
        print("✅ Memory deletion working")

    except Exception as e:
        print(f"❌ Memory operations test failed: {e}")
        return False

    # Test 9: Error Handling and Authentication
    print("\n9. Testing Error Handling and Authentication")
    try:
        # Test missing API key
        response = requests.get(f"{BASE_URL}/status")
        assert response.status_code == 422, f"Expected 422 for missing API key, got {response.status_code}"

        # Test invalid API key
        response = requests.get(f"{BASE_URL}/status?api_key=invalid_key")
        assert response.status_code == 401, f"Expected 401 for invalid API key, got {response.status_code}"

        print("✅ Error handling and authentication working")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

    print("\n🎉 All OpenAPI Documentation Tests Passed!")
    return True


def test_openapi_documentation_completeness():
    """Test that OpenAPI documentation is complete and comprehensive"""

    print("\n🔍 Testing OpenAPI Documentation Completeness")
    print("=" * 50)

    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        schema = response.json()

        # Check for required OpenAPI fields
        assert "info" in schema, "Missing API info"
        assert "title" in schema["info"], "Missing API title"
        assert "version" in schema["info"], "Missing API version"
        assert "description" in schema["info"], "Missing API description"

        # Check for security schemes
        assert "components" in schema, "Missing components section"
        assert "securitySchemes" in schema["components"], "Missing security schemes"

        # Check for tags
        assert "tags" in schema, "Missing tags"
        expected_tags = ["Health", "Memories", "Search"]
        for tag in expected_tags:
            assert any(t["name"] == tag for t in schema["tags"]), f"Missing tag: {tag}"

        # Check for paths
        expected_paths = ["/health", "/status", "/memories", "/memories/search"]
        for path in expected_paths:
            assert path in schema["paths"] or any(p.startswith(path) for p in schema["paths"]), f"Missing path: {path}"

        print("✅ OpenAPI documentation is complete and comprehensive")
        return True

    except Exception as e:
        print(f"❌ OpenAPI documentation completeness test failed: {e}")
        return False


if __name__ == "__main__":
    print("Starting OpenAPI Documentation Validation Tests")
    print("Server should be running at http://127.0.0.1:8000")
    print("Waiting 2 seconds for server to be ready...")
    time.sleep(2)

    success = True
    success &= test_openapi_endpoints()
    success &= test_openapi_documentation_completeness()

    if success:
        print("\n🎉 ALL TESTS PASSED - OpenAPI Documentation is Complete!")
        print("✅ Priority 2 (API Documentation) - COMPLETED")
    else:
        print("\n❌ Some tests failed - Please check the output above")
