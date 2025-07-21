-- Schema for AI insights and analytics tracking
-- Required for pattern detection and usage analytics

-- Access logs table to track memory access patterns
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_type VARCHAR(50) DEFAULT 'view', -- view, edit, search_result
    user_context JSONB DEFAULT '{}', -- Optional context about the access
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_access_logs_memory_id ON access_logs(memory_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_accessed_at ON access_logs(accessed_at);
CREATE INDEX IF NOT EXISTS idx_access_logs_memory_time ON access_logs(memory_id, accessed_at DESC);

-- Insights cache table for storing generated insights
CREATE TABLE IF NOT EXISTS insights_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type VARCHAR(100) NOT NULL,
    time_frame VARCHAR(50) NOT NULL,
    insight_data JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    impact_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(insight_type, time_frame)
);

-- Pattern detection results
CREATE TABLE IF NOT EXISTS detected_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(100) NOT NULL,
    pattern_name TEXT NOT NULL,
    pattern_data JSONB NOT NULL,
    strength FLOAT DEFAULT 0.0,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Knowledge gaps tracking
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area TEXT NOT NULL,
    severity FLOAT DEFAULT 0.0,
    gap_data JSONB NOT NULL,
    suggested_topics TEXT[],
    resolved BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Learning progress tracking
CREATE TABLE IF NOT EXISTS learning_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    time_frame VARCHAR(50) NOT NULL,
    metrics JSONB NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(time_frame, calculated_at)
);

-- Function to log memory access
CREATE OR REPLACE FUNCTION log_memory_access(
    p_memory_id UUID,
    p_access_type VARCHAR DEFAULT 'view',
    p_context JSONB DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO access_logs (memory_id, access_type, user_context)
    VALUES (p_memory_id, p_access_type, p_context)
    RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get memory access statistics
CREATE OR REPLACE FUNCTION get_memory_access_stats(
    p_memory_id UUID,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    total_accesses BIGINT,
    unique_days INTEGER,
    first_access TIMESTAMP WITH TIME ZONE,
    last_access TIMESTAMP WITH TIME ZONE,
    avg_daily_accesses FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_accesses,
        COUNT(DISTINCT DATE(accessed_at))::INTEGER as unique_days,
        MIN(accessed_at) as first_access,
        MAX(accessed_at) as last_access,
        COUNT(*)::FLOAT / GREATEST(COUNT(DISTINCT DATE(accessed_at)), 1)::FLOAT as avg_daily_accesses
    FROM access_logs
    WHERE memory_id = p_memory_id
        AND accessed_at >= NOW() - INTERVAL '1 day' * p_days;
END;
$$ LANGUAGE plpgsql;

-- View for popular memories
CREATE OR REPLACE VIEW popular_memories AS
SELECT 
    m.id,
    m.content,
    m.tags,
    m.importance,
    COUNT(al.id) as access_count,
    MAX(al.accessed_at) as last_accessed
FROM memories m
LEFT JOIN access_logs al ON m.id = al.memory_id
GROUP BY m.id
ORDER BY access_count DESC, m.importance DESC;