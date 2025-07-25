-- Migration for v2.8.2 Synthesis features
-- Adds tables for memory consolidation, lineage tracking, and metrics

-- Create enum for consolidation strategies
CREATE TYPE consolidation_strategy_enum AS ENUM (
    'merge_similar',
    'chronological',
    'topic_based',
    'entity_focused',
    'hierarchical'
);

-- Track consolidation history
CREATE TABLE memory_consolidations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_memory_ids UUID[] NOT NULL,
    consolidated_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    strategy consolidation_strategy_enum NOT NULL,
    quality_score REAL DEFAULT 0.0,
    token_reduction INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT
);

-- Track memory lineage and relationships
CREATE TABLE memory_lineage (
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    parent_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL, -- 'consolidated_from', 'derived_from', 'updated_from', etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (memory_id, parent_memory_id)
);

-- Cache for graph metrics
CREATE TABLE graph_metrics_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_key TEXT UNIQUE NOT NULL,
    metrics_data JSONB NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    hit_count INTEGER DEFAULT 0
);

-- Track scheduled reviews
CREATE TABLE scheduled_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    review_strategy TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    review_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track generated summaries
CREATE TABLE knowledge_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_type TEXT NOT NULL, -- 'topic', 'period', 'executive'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    memory_ids UUID[] DEFAULT '{}',
    entities TEXT[] DEFAULT '{}',
    topics TEXT[] DEFAULT '{}',
    time_range TSTZRANGE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_consolidation_date ON memory_consolidations(created_at DESC);
CREATE INDEX idx_consolidation_strategy ON memory_consolidations(strategy);
CREATE INDEX idx_lineage_memory ON memory_lineage(memory_id);
CREATE INDEX idx_lineage_parent ON memory_lineage(parent_memory_id);
CREATE INDEX idx_metrics_cache_key ON graph_metrics_cache(metric_key);
CREATE INDEX idx_metrics_cache_expires ON graph_metrics_cache(expires_at);
CREATE INDEX idx_reviews_scheduled ON scheduled_reviews(scheduled_for) WHERE completed_at IS NULL;
CREATE INDEX idx_reviews_memory ON scheduled_reviews(memory_id);
CREATE INDEX idx_summaries_type ON knowledge_summaries(summary_type);
CREATE INDEX idx_summaries_date ON knowledge_summaries(created_at DESC);

-- GIN indexes for JSONB and arrays
CREATE INDEX idx_consolidation_metadata ON memory_consolidations USING gin(metadata);
CREATE INDEX idx_summaries_memory_ids ON knowledge_summaries USING gin(memory_ids);

-- Function to get memory lineage tree
CREATE OR REPLACE FUNCTION get_memory_lineage(target_memory_id UUID, max_depth INTEGER DEFAULT 5)
RETURNS TABLE (
    memory_id UUID,
    parent_id UUID,
    relationship TEXT,
    depth INTEGER,
    path UUID[]
) AS $$
WITH RECURSIVE lineage_tree AS (
    -- Base case: the target memory
    SELECT 
        m.memory_id,
        m.parent_memory_id,
        m.relationship_type,
        1 as depth,
        ARRAY[m.memory_id] as path
    FROM memory_lineage m
    WHERE m.memory_id = target_memory_id
    
    UNION ALL
    
    -- Recursive case: traverse up the tree
    SELECT 
        m.memory_id,
        m.parent_memory_id,
        m.relationship_type,
        lt.depth + 1,
        lt.path || m.memory_id
    FROM memory_lineage m
    JOIN lineage_tree lt ON m.memory_id = lt.parent_memory_id
    WHERE lt.depth < max_depth
    AND NOT m.memory_id = ANY(lt.path) -- Prevent cycles
)
SELECT * FROM lineage_tree;
$$ LANGUAGE SQL;

-- Function to calculate consolidation savings
CREATE OR REPLACE FUNCTION calculate_consolidation_savings()
RETURNS TABLE (
    total_consolidations BIGINT,
    total_token_reduction BIGINT,
    avg_quality_score REAL,
    most_used_strategy consolidation_strategy_enum
) AS $$
SELECT 
    COUNT(*) as total_consolidations,
    SUM(token_reduction) as total_token_reduction,
    AVG(quality_score) as avg_quality_score,
    MODE() WITHIN GROUP (ORDER BY strategy) as most_used_strategy
FROM memory_consolidations
WHERE created_at > NOW() - INTERVAL '30 days';
$$ LANGUAGE SQL;

-- Trigger to update metrics cache expiration
CREATE OR REPLACE FUNCTION update_metrics_cache_expiration()
RETURNS TRIGGER AS $$
BEGIN
    -- Set expiration based on metric type
    IF NEW.metric_key LIKE 'realtime:%' THEN
        NEW.expires_at := NOW() + INTERVAL '5 minutes';
    ELSIF NEW.metric_key LIKE 'daily:%' THEN
        NEW.expires_at := NOW() + INTERVAL '1 hour';
    ELSE
        NEW.expires_at := NOW() + INTERVAL '30 minutes';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_metrics_expiration
    BEFORE INSERT ON graph_metrics_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_metrics_cache_expiration();

-- View for consolidation statistics
CREATE VIEW consolidation_stats AS
SELECT 
    DATE_TRUNC('day', created_at) as consolidation_date,
    COUNT(*) as daily_consolidations,
    AVG(quality_score) as avg_quality,
    SUM(token_reduction) as total_tokens_saved,
    ARRAY_AGG(DISTINCT strategy) as strategies_used
FROM memory_consolidations
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY consolidation_date DESC;

-- Grant permissions (adjust based on your user setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO your_app_user;