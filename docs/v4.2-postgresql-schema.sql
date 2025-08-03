-- Second Brain v4.2 PostgreSQL + pgvector Schema
-- Unified storage for memories, embeddings, and metadata
-- Created: August 3, 2025

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Main memories table
CREATE TABLE IF NOT EXISTS memories (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Core content
    content TEXT NOT NULL,
    content_hash VARCHAR(64) GENERATED ALWAYS AS (encode(sha256(content::bytea), 'hex')) STORED,
    
    -- Memory metadata
    memory_type VARCHAR(50) DEFAULT 'generic',
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
    access_count INTEGER DEFAULT 0,
    
    -- Vector embedding (1536 dimensions for OpenAI ada-002)
    embedding vector(1536),
    embedding_model VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    embedding_generated_at TIMESTAMPTZ,
    
    -- Full-text search
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    
    -- Tags and metadata
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Soft delete
    deleted_at TIMESTAMPTZ,
    
    -- User/container association (for future multi-tenancy)
    container_id VARCHAR(255) DEFAULT 'default',
    
    -- Version tracking
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES memories(id)
);

-- Indexes for performance
CREATE INDEX idx_memories_created_at ON memories(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_updated_at ON memories(updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_importance ON memories(importance_score DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_type ON memories(memory_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_container ON memories(container_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_content_hash ON memories(content_hash) WHERE deleted_at IS NULL;

-- GIN indexes for arrays and JSONB
CREATE INDEX idx_memories_tags ON memories USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_memories_metadata ON memories USING GIN(metadata) WHERE deleted_at IS NULL;

-- Full-text search index
CREATE INDEX idx_memories_fts ON memories USING GIN(content_tsvector) WHERE deleted_at IS NULL;

-- Trigram index for fuzzy search
CREATE INDEX idx_memories_content_trgm ON memories USING GIN(content gin_trgm_ops) WHERE deleted_at IS NULL;

-- Vector similarity search index (HNSW method for better performance)
CREATE INDEX idx_memories_embedding ON memories USING hnsw(embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64) 
    WHERE deleted_at IS NULL AND embedding IS NOT NULL;

-- Memory relationships table (for knowledge graph)
CREATE TABLE IF NOT EXISTS memory_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX idx_relationships_source ON memory_relationships(source_memory_id);
CREATE INDEX idx_relationships_target ON memory_relationships(target_memory_id);
CREATE INDEX idx_relationships_type ON memory_relationships(relationship_type);

-- Consolidation tracking table
CREATE TABLE IF NOT EXISTS memory_consolidations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consolidated_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    source_memory_ids UUID[] NOT NULL,
    consolidation_type VARCHAR(50) NOT NULL, -- 'merge', 'summary', 'abstraction'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_consolidations_memory ON memory_consolidations(consolidated_memory_id);
CREATE INDEX idx_consolidations_sources ON memory_consolidations USING GIN(source_memory_ids);

-- Search history for learning patterns
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT NOT NULL,
    query_embedding vector(1536),
    results_count INTEGER DEFAULT 0,
    selected_memory_ids UUID[] DEFAULT ARRAY[]::UUID[],
    search_type VARCHAR(50) DEFAULT 'hybrid', -- 'vector', 'text', 'hybrid'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    container_id VARCHAR(255) DEFAULT 'default'
);

CREATE INDEX idx_search_history_created ON search_history(created_at DESC);
CREATE INDEX idx_search_history_container ON search_history(container_id);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update access tracking function
CREATE OR REPLACE FUNCTION track_memory_access(memory_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE memories 
    SET access_count = access_count + 1,
        last_accessed_at = NOW()
    WHERE id = memory_id;
END;
$$ LANGUAGE plpgsql;

-- Hybrid search function (combines vector and text search)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    result_limit INTEGER DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.5,
    min_score FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    memory_type VARCHAR,
    importance_score FLOAT,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ,
    similarity_score FLOAT,
    text_rank FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            m.id,
            m.content,
            m.memory_type,
            m.importance_score,
            m.tags,
            m.metadata,
            m.created_at,
            1 - (m.embedding <=> query_embedding) AS similarity_score
        FROM memories m
        WHERE m.deleted_at IS NULL 
            AND m.embedding IS NOT NULL
        ORDER BY m.embedding <=> query_embedding
        LIMIT result_limit * 2
    ),
    text_search AS (
        SELECT 
            m.id,
            m.content,
            m.memory_type,
            m.importance_score,
            m.tags,
            m.metadata,
            m.created_at,
            ts_rank(m.content_tsvector, plainto_tsquery('english', query_text)) AS text_rank
        FROM memories m
        WHERE m.deleted_at IS NULL 
            AND m.content_tsvector @@ plainto_tsquery('english', query_text)
        ORDER BY text_rank DESC
        LIMIT result_limit * 2
    ),
    combined AS (
        SELECT 
            COALESCE(v.id, t.id) AS id,
            COALESCE(v.content, t.content) AS content,
            COALESCE(v.memory_type, t.memory_type) AS memory_type,
            COALESCE(v.importance_score, t.importance_score) AS importance_score,
            COALESCE(v.tags, t.tags) AS tags,
            COALESCE(v.metadata, t.metadata) AS metadata,
            COALESCE(v.created_at, t.created_at) AS created_at,
            COALESCE(v.similarity_score, 0) AS similarity_score,
            COALESCE(t.text_rank, 0) AS text_rank,
            (COALESCE(v.similarity_score, 0) * vector_weight + 
             COALESCE(t.text_rank, 0) * (1 - vector_weight)) AS combined_score
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT * FROM combined
    WHERE combined_score >= min_score
    ORDER BY combined_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Memory deduplication function
CREATE OR REPLACE FUNCTION find_duplicate_memories(
    similarity_threshold FLOAT DEFAULT 0.95
)
RETURNS TABLE (
    memory1_id UUID,
    memory2_id UUID,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m1.id AS memory1_id,
        m2.id AS memory2_id,
        1 - (m1.embedding <=> m2.embedding) AS similarity
    FROM memories m1
    CROSS JOIN memories m2
    WHERE m1.id < m2.id
        AND m1.deleted_at IS NULL
        AND m2.deleted_at IS NULL
        AND m1.embedding IS NOT NULL
        AND m2.embedding IS NOT NULL
        AND 1 - (m1.embedding <=> m2.embedding) >= similarity_threshold
    ORDER BY similarity DESC;
END;
$$ LANGUAGE plpgsql;

-- Statistics view
CREATE OR REPLACE VIEW memory_statistics AS
SELECT 
    COUNT(*) AS total_memories,
    COUNT(DISTINCT memory_type) AS unique_types,
    AVG(importance_score) AS avg_importance,
    MAX(access_count) AS max_access_count,
    COUNT(DISTINCT container_id) AS containers,
    COUNT(embedding) AS memories_with_embeddings,
    pg_size_pretty(pg_total_relation_size('memories')) AS table_size,
    MAX(created_at) AS latest_memory,
    MIN(created_at) AS oldest_memory
FROM memories
WHERE deleted_at IS NULL;

-- Grant permissions (adjust as needed)
GRANT ALL ON ALL TABLES IN SCHEMA public TO second_brain_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO second_brain_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO second_brain_app;