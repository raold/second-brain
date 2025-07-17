"""
Test the mock database functionality.
"""
import asyncio

from app.database_mock import get_mock_database


async def test_mock_database():
    """Test mock database functionality."""
    # Get database
    db = await get_mock_database()

    # Store a memory
    content = "This is a test memory"
    metadata = {"type": "test", "priority": "high"}

    memory_id = await db.store_memory(content, metadata)
    print(f"✅ Stored memory with ID: {memory_id}")

    # Retrieve the memory
    retrieved = await db.get_memory(memory_id)
    print(f"✅ Retrieved memory: {retrieved}")

    # Search for memories
    results = await db.search_memories("test", limit=5)
    print(f"✅ Search results: {len(results)} memories found")

    # List all memories
    all_memories = await db.get_all_memories(limit=10)
    print(f"✅ All memories: {len(all_memories)} memories found")

    # Clean up
    await db.close()
    print("✅ Mock database test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_mock_database())
