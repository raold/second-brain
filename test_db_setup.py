#!/usr/bin/env python3
import asyncio
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage.database_setup import DatabaseSetup


async def test_database_setup():
    """Test the database setup method."""
    print("🔧 Testing DatabaseSetup PostgreSQL method...")

    try:
        db_setup = DatabaseSetup()
        print("✅ DatabaseSetup instance created")

        # Test individual components
        print("\n🔍 Testing PostgreSQL setup...")

        # Setup engines manually first
        print("Setting up engines...")
        sync_url = db_setup.config.get_postgres_url().replace('+asyncpg', '')
        async_url = db_setup.config.get_postgres_url()

        print(f"Sync URL: {sync_url}")
        print(f"Async URL: {async_url}")

        from sqlalchemy import create_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        db_setup.postgres_engine = create_engine(sync_url)
        db_setup.postgres_async_engine = create_async_engine(async_url)

        # Test health check directly
        print("\n🔍 Testing PostgreSQL health check...")
        health = await db_setup.check_postgres_health()
        print(f"Health check result: {health}")

        if health:
            print("✅ Health check passed, proceeding with full setup")
            await db_setup.setup_postgres()
            print("✅ PostgreSQL setup completed successfully")
        else:
            print("❌ Health check failed, investigating...")

            # Manual test
            print("Testing manual connection...")
            from sqlalchemy import text
            async with db_setup.postgres_async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar()
                print(f"Manual test result: {value}")

        print("\n🔍 Testing PostgreSQL health check again...")
        health = await db_setup.check_postgres_health()
        print(f"✅ PostgreSQL health check: {health}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_setup())
