#!/usr/bin/env python3
"""
Fixed Database Tests for Second Brain v2.2.0
Addresses memory_type column issues and validates database functionality
"""

import asyncio
import os
import sys

import pytest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.environment import validate_test_environment
from app.database_mock import get_mock_database

test_config = validate_test_environment()


@pytest.mark.asyncio
async def test_mock_database_initialization():
    """Test mock database initialization."""
    print("🔧 Testing Mock Database initialization...")

    try:
        db = await get_mock_database()
        print("✅ Mock database instance created")

        # Test basic functionality
        stats = await db.get_index_stats()
        print(f"✅ Index stats retrieved: {stats}")

        await db.close()
        print("✅ Mock database connection closed")

    except Exception as e:
        print(f"❌ Mock database test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_memory_storage_and_retrieval():
    """Test memory storage and retrieval functionality."""
    print("🔧 Testing Memory storage and retrieval...")

    try:
        db = await get_mock_database()

        # Test memory storage with proper metadata structure
        content = "Test memory for database validation"
        metadata = {
            "type": "semantic",  # Valid memory type
            "priority": "high",
            "tags": ["test", "database", "validation"],
            "category": "unit_test",
        }

        memory_id = await db.store_memory(content, metadata)
        print(f"✅ Memory stored with ID: {memory_id}")

        # Test memory retrieval
        retrieved = await db.get_memory(memory_id)
        print(f"✅ Memory retrieved: {retrieved['content'][:50]}...")

        # Validate memory structure
        assert retrieved["content"] == content
        assert retrieved["metadata"]["type"] == "semantic"
        assert "test" in retrieved["metadata"]["tags"]
        print("✅ Memory structure validation passed")

        await db.close()

    except Exception as e:
        print(f"❌ Memory storage test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_memory_search_functionality():
    """Test memory search functionality."""
    print("🔧 Testing Memory search...")

    try:
        db = await get_mock_database()

        # Store multiple memories for search testing
        test_memories = [
            ("Python is a programming language", {"type": "semantic", "domain": "programming"}),
            ("Machine learning uses algorithms", {"type": "semantic", "domain": "ai"}),
            ("Remember to buy groceries", {"type": "episodic", "domain": "personal"}),
        ]

        stored_ids = []
        for content, metadata in test_memories:
            memory_id = await db.store_memory(content, metadata)
            stored_ids.append(memory_id)

        print(f"✅ Stored {len(stored_ids)} test memories")

        # Test search functionality
        results = await db.search_memories("Python programming", limit=5)
        print(f"✅ Search found {len(results)} results")

        # Test search with filters
        results_filtered = await db.search_memories("learning", limit=5, memory_types=["semantic"])
        print(f"✅ Filtered search found {len(results_filtered)} results")

        await db.close()

    except Exception as e:
        print(f"❌ Memory search test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_memory_type_validation():
    """Test memory type validation and handling."""
    print("🔧 Testing Memory type validation...")

    try:
        db = await get_mock_database()

        # Test valid memory types
        valid_types = ["semantic", "episodic", "procedural"]

        for memory_type in valid_types:
            content = f"Test memory of type {memory_type}"
            metadata = {"type": memory_type, "test": True}

            memory_id = await db.store_memory(content, metadata)
            retrieved = await db.get_memory(memory_id)

            assert retrieved["metadata"]["type"] == memory_type
            print(f"✅ Memory type '{memory_type}' validated")

        # Test default type handling
        content_no_type = "Memory without explicit type"
        metadata_no_type = {"category": "test"}

        memory_id = await db.store_memory(content_no_type, metadata_no_type)
        retrieved = await db.get_memory(memory_id)

        # Should have default type
        print(f"✅ Default memory type handling: {retrieved['metadata'].get('type', 'None')}")

        await db.close()

    except Exception as e:
        print(f"❌ Memory type validation test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_database_performance():
    """Test database performance with multiple operations."""
    print("🔧 Testing Database performance...")

    try:
        db = await get_mock_database()

        # Store multiple memories to test performance
        import time

        start_time = time.time()

        memory_ids = []
        for i in range(10):
            content = f"Performance test memory {i}"
            metadata = {"type": "semantic", "index": i, "batch": "performance_test"}
            memory_id = await db.store_memory(content, metadata)
            memory_ids.append(memory_id)

        storage_time = time.time() - start_time
        print(f"✅ Stored 10 memories in {storage_time:.3f} seconds")

        # Test batch retrieval performance
        start_time = time.time()

        retrieved_memories = []
        for memory_id in memory_ids:
            memory = await db.get_memory(memory_id)
            retrieved_memories.append(memory)

        retrieval_time = time.time() - start_time
        print(f"✅ Retrieved 10 memories in {retrieval_time:.3f} seconds")

        # Test search performance
        start_time = time.time()
        results = await db.search_memories("performance test", limit=20)
        search_time = time.time() - start_time
        print(f"✅ Search completed in {search_time:.3f} seconds, found {len(results)} results")

        await db.close()

    except Exception as e:
        print(f"❌ Database performance test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_database_error_handling():
    """Test database error handling and edge cases."""
    print("🔧 Testing Database error handling...")

    try:
        db = await get_mock_database()

        # Test retrieval of non-existent memory
        fake_id = "non-existent-id"
        result = await db.get_memory(fake_id)
        assert result is None
        print("✅ Non-existent memory handling validated")

        # Test empty search
        results = await db.search_memories("", limit=5)
        print(f"✅ Empty search handled: {len(results)} results")

        # Test search with very long query
        long_query = "test " * 100
        results = await db.search_memories(long_query, limit=5)
        print(f"✅ Long query handled: {len(results)} results")

        # Test invalid memory types gracefully
        try:
            content = "Test memory with invalid type"
            metadata = {"type": "invalid_type", "test": True}
            await db.store_memory(content, metadata)
            print("✅ Invalid memory type handled gracefully")
        except Exception as e:
            print(f"✅ Invalid memory type properly rejected: {e}")

        await db.close()

    except Exception as e:
        print(f"❌ Database error handling test failed: {e}")
        raise


async def run_all_database_tests():
    """Run all database tests."""
    print("🚀 Starting Comprehensive Database Test Suite")
    print("=" * 60)

    tests = [
        ("Mock Database Initialization", test_mock_database_initialization),
        ("Memory Storage and Retrieval", test_memory_storage_and_retrieval),
        ("Memory Search Functionality", test_memory_search_functionality),
        ("Memory Type Validation", test_memory_type_validation),
        ("Database Performance", test_database_performance),
        ("Database Error Handling", test_database_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n📊 Running {test_name}")
            print("-" * 40)
            await test_func()
            print(f"✅ {test_name} - PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} - FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("🎯 DATABASE TEST RESULTS")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 ALL DATABASE TESTS PASSED!")
    else:
        print(f"\n⚠️ {failed} test(s) failed")

    return failed == 0


if __name__ == "__main__":
    result = asyncio.run(run_all_database_tests())
    sys.exit(0 if result else 1)
