#!/bin/bash

echo "================================================"
echo "  SECOND BRAIN v4.2.0 - POSTGRESQL ONLY"
echo "================================================"

# Kill ALL backends
pkill -f uvicorn 2>/dev/null
sleep 2

# Test PostgreSQL connection
echo "Testing PostgreSQL connection..."
PGPASSWORD=changeme psql -h localhost -U secondbrain -d secondbrain -c "SELECT 1;" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ POSTGRESQL IS NOT RUNNING!"
    echo ""
    echo "DO THIS RIGHT NOW:"
    echo ""
    echo "1. Open PowerShell/CMD on Windows (NOT WSL)"
    echo "2. Run these commands:"
    echo ""
    echo "   cd C:\\tools\\second-brain"
    echo "   docker-compose up -d postgres"
    echo ""
    echo "3. Wait 10 seconds"
    echo "4. Run this script again"
    echo ""
    exit 1
fi

echo "✅ PostgreSQL is running!"

# Initialize database schema
echo "Initializing database..."
.venv/bin/python -c "
import asyncio
import asyncpg

async def init():
    conn = await asyncpg.connect(
        'postgresql://secondbrain:changeme@localhost:5432/secondbrain'
    )
    
    # Create pgvector extension
    await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
    await conn.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Create memories table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'generic',
            importance_score FLOAT DEFAULT 0.5,
            embedding vector(1536),
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            access_count INTEGER DEFAULT 0
        )
    ''')
    
    # Create indexes
    await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_memories_embedding 
        ON memories USING hnsw (embedding vector_cosine_ops)
    ''')
    
    count = await conn.fetchval('SELECT COUNT(*) FROM memories')
    print(f'✅ Database ready with {count} memories')
    
    await conn.close()

asyncio.run(init())
"

# Start the REAL backend
echo ""
echo "🚀 Starting REAL backend (PostgreSQL ONLY)..."
echo "================================================"
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "================================================"

cd /mnt/c/tools/second-brain
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload