#!/usr/bin/env python3
"""
Wait for database to be ready before starting the application
"""
import asyncio
import os
import sys
import time

import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


async def wait_for_postgres():
    """Wait for PostgreSQL to be ready"""
    database_url = os.getenv("DATABASE_URL", "postgresql://secondbrain:changeme@localhost:5432/secondbrain")

    # Convert to asyncpg format
    if database_url.startswith("postgresql://"):
        asyncpg_url = database_url.replace("postgresql://", "postgresql://")
    elif database_url.startswith("postgresql+asyncpg://"):
        asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        asyncpg_url = database_url

    max_retries = 30
    retry_interval = 2

    for attempt in range(max_retries):
        try:
            # Try to connect
            conn = await asyncpg.connect(asyncpg_url)
            await conn.execute("SELECT 1")
            await conn.close()
            print("✓ Database is ready!")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(retry_interval)
            else:
                print(f"✗ Database failed to become ready after {max_retries} attempts")
                return False

    return False


def wait_for_postgres_sync():
    """Synchronous version for compatibility"""
    database_url = os.getenv("DATABASE_URL", "postgresql://secondbrain:changeme@localhost:5432/secondbrain")

    # Convert to SQLAlchemy format
    if not database_url.startswith("postgresql+"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")

    max_retries = 30
    retry_interval = 2

    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            engine.dispose()
            print("✓ Database is ready!")
            return True
        except OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Database not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_interval)
            else:
                print(f"✗ Database failed to become ready after {max_retries} attempts")
                return False

    return False


def main():
    """Main entry point"""
    try:
        # Try async first
        if asyncio.run(wait_for_postgres()):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception:
        # Fall back to sync
        if wait_for_postgres_sync():
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
