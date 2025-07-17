#!/usr/bin/env python3
"""
Check database schema.
"""
import asyncio
import os

import asyncpg


async def check_schema():
    """Check the database schema."""
    db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'secondbrain')}"

    conn = await asyncpg.connect(db_url)

    # Check table structure
    result = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'memories'
        ORDER BY ordinal_position
    """)

    print("Current 'memories' table structure:")
    for row in result:
        print(f"  {row['column_name']}: {row['data_type']}")

    # Check if table exists
    exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'memories'
        )
    """)

    print(f"\nTable exists: {exists}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
