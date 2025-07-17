#!/usr/bin/env python3
"""
Database setup script for Second Brain.
Creates the database and installs pgvector extension.
"""

import asyncio
import os
import sys

import asyncpg


async def setup_database():
    """Setup database with pgvector extension."""
    # Connection parameters
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    database = os.getenv("POSTGRES_DB", "secondbrain")

    try:
        # Connect to postgres database to create our database
        conn = await asyncpg.connect(host=host, port=port, user=user, password=password, database="postgres")

        # Create database if it doesn't exist
        try:
            await conn.execute(f"CREATE DATABASE {database}")
            print(f"✅ Created database: {database}")
        except asyncpg.DuplicateDatabaseError:
            print(f"ℹ️  Database {database} already exists")

        await conn.close()

        # Connect to our database
        conn = await asyncpg.connect(host=host, port=port, user=user, password=password, database=database)

        # Install pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✅ pgvector extension installed")

        # Create memories table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                embedding vector(1536),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created memories table")

        # Create index for vector similarity search
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_embedding_idx
                ON memories USING ivfflat (embedding vector_cosine_ops)
            """)
            print("✅ Created vector similarity index")
        except Exception as e:
            print(f"⚠️  Index creation skipped: {e}")
            # Index can be created later when there's data

        await conn.close()
        print("✅ Database setup complete!")

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_database())
