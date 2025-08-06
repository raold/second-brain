-- Create hybrid search function for v4.2.0
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
    similarity_score DOUBLE PRECISION,
    text_rank DOUBLE PRECISION,
    combined_score DOUBLE PRECISION
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
            COALESCE(v.similarity_score, 0)::FLOAT8 AS similarity_score,
            COALESCE(t.text_rank, 0)::FLOAT8 AS text_rank,
            (COALESCE(v.similarity_score, 0) * vector_weight + 
             COALESCE(t.text_rank, 0) * (1 - vector_weight))::FLOAT8 AS combined_score
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT * FROM combined
    WHERE combined.combined_score >= min_score
    ORDER BY combined.combined_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;