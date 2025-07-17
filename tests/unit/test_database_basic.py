#!/usr/bin/env python3
import asyncio
import os
import sys
import pytest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Database


@pytest.mark.asyncio
async def test_database_initialization():
    """Test the database initialization."""
    print("🔧 Testing Database initialization...")
    
    try:
        db = Database()
        print("✅ Database instance created")
        
        # Test initialization
        await db.initialize()
        print("✅ Database initialized successfully")
        
        # Test basic functionality
        stats = await db.get_index_stats()
        print(f"✅ Index stats retrieved: {stats}")
        
        # Clean up
        await db.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_database_initialization())
