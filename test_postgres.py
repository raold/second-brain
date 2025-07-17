#!/usr/bin/env python3
import asyncio
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

async def test_asyncpg():
    """Test direct asyncpg connection."""
    try:
        conn = await asyncpg.connect(
            'postgresql://postgres:postgres123@localhost:5432/second_brain'
        )
        result = await conn.fetchval('SELECT 1')
        print(f"✅ AsyncPG connection successful: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ AsyncPG connection failed: {e}")
        return False

async def test_sqlalchemy_async():
    """Test SQLAlchemy async connection."""
    try:
        engine = create_async_engine(
            'postgresql+asyncpg://postgres:postgres123@localhost:5432/second_brain'
        )
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"✅ SQLAlchemy async connection successful: {value}")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy async connection failed: {e}")
        return False

def test_sqlalchemy_sync():
    """Test SQLAlchemy sync connection."""
    try:
        engine = create_engine(
            'postgresql://postgres:postgres123@localhost:5432/second_brain'
        )
        with engine.begin() as conn:
            result = conn.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"✅ SQLAlchemy sync connection successful: {value}")
        engine.dispose()
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy sync connection failed: {e}")
        return False

async def main():
    print("🔧 Testing PostgreSQL connections...")
    print("=" * 50)
    
    # Test direct asyncpg
    await test_asyncpg()
    
    # Test SQLAlchemy async
    await test_sqlalchemy_async()
    
    # Test SQLAlchemy sync
    test_sqlalchemy_sync()
    
    print("=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
