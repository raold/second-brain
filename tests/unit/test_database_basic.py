#!/usr/bin/env python3
import asyncio
import os
import sys

import pytest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database_mock import get_mock_database


@pytest.mark.asyncio
async def test_database_initialization():
    """Test the database initialization with mock database."""
    print("🔧 Testing Mock Database initialization...")

    try:
        db = await get_mock_database()
        print("✅ Mock Database instance created")

        # Test initialization
        await db.initialize()
        print("✅ Mock Database initialized successfully")

        # Test basic functionality - mock database has limited functionality
        # Just verify the instance is working
        assert hasattr(db, "store_memory")
        assert hasattr(db, "search_memories")
        print("✅ Mock Database basic functionality verified")

        # Clean up
        await db.close()
        print("✅ Mock Database connection closed")

    except Exception as e:
        print(f"❌ Mock Database setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_database_initialization())
