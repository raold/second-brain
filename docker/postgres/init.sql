-- Initialize PostgreSQL with pgvector extension
-- This script runs when the container is first created

-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create any custom functions or configurations
-- Example: Set up text search configuration
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Performance tuning for vector operations
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET work_mem = '16MB';

-- Create indexes for better performance (these will be created by migrations, but just in case)
-- CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at DESC);
-- CREATE INDEX IF NOT EXISTS idx_memories_embedding_vector ON memories USING ivfflat (embedding_vector vector_cosine_ops);

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Second Brain PostgreSQL initialization complete';
    RAISE NOTICE 'pgvector extension enabled';
    RAISE NOTICE 'Performance settings configured';
END $$;