#!/usr/bin/env python3
"""
Fix database schema for v2.0.0.
"""

import asyncio
import os

import asyncpg


async def fix_schema():
    """Fix the database schema for v2.0.0."""
    db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'secondbrain')}"

    conn = await asyncpg.connect(db_url)

    # Drop the old table
    await conn.execute("DROP TABLE IF EXISTS memories")
    print("✅ Dropped old memories table")

    # Create the new table with correct v2.0.0 schema
    await conn.execute("""
        CREATE TABLE memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            embedding vector(1536),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created new memories table with v2.0.0 schema")

    # Try to create the index
    try:
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS memories_embedding_idx
            ON memories USING ivfflat (embedding vector_cosine_ops)
        """)
        print("✅ Created vector index")
    except Exception as e:
        print(f"⚠️  Index creation skipped: {e}")

    await conn.close()
    print("✅ Database schema fixed for v2.0.0")


if __name__ == "__main__":
    asyncio.run(fix_schema())
