-- Migration for v2.8.2 Synthesis features (SQLite version)
-- Adds tables for memory consolidation, lineage tracking, and metrics

-- Track consolidation history
CREATE TABLE IF NOT EXISTS memory_consolidations (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    original_memory_ids TEXT NOT NULL, -- JSON array of UUIDs
    consolidated_memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
    strategy TEXT NOT NULL CHECK(strategy IN ('merge_similar', 'chronological', 'topic_based', 'entity_focused', 'hierarchical')),
    quality_score REAL DEFAULT 0.0,
    token_reduction INTEGER DEFAULT 0,
    consolidation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

-- Track memory lineage and relationships
CREATE TABLE IF NOT EXISTS memory_lineage (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    parent_memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
    child_memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK(relationship_type IN ('derived_from', 'consolidated_into', 'split_from', 'updated_from')),
    metadata TEXT, -- JSON metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parent_memory_id, child_memory_id, relationship_type)
);

-- Cache for graph metrics to improve performance
CREATE TABLE IF NOT EXISTS graph_metrics_cache (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL,
    metrics_type TEXT NOT NULL CHECK(metrics_type IN ('node_centrality', 'cluster_stats', 'connectivity')),
    cache_key TEXT NOT NULL,
    cached_data TEXT NOT NULL, -- JSON data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(user_id, metrics_type, cache_key)
);

-- Schedule for spaced repetition and review
CREATE TABLE IF NOT EXISTS scheduled_reviews (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    scheduled_for TIMESTAMP NOT NULL,
    review_interval INTEGER DEFAULT 1, -- days
    difficulty_factor REAL DEFAULT 1.0,
    review_count INTEGER DEFAULT 0,
    last_reviewed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge summaries for topics and time periods
CREATE TABLE IF NOT EXISTS knowledge_summaries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL,
    summary_type TEXT NOT NULL CHECK(summary_type IN ('topic', 'period', 'executive')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_memory_ids TEXT, -- JSON array of memory IDs
    metadata TEXT, -- JSON metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_consolidated ON memory_consolidations(consolidated_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_created ON memory_consolidations(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_lineage_parent ON memory_lineage(parent_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_lineage_child ON memory_lineage(child_memory_id);
CREATE INDEX IF NOT EXISTS idx_graph_metrics_cache_user ON graph_metrics_cache(user_id, metrics_type);
CREATE INDEX IF NOT EXISTS idx_graph_metrics_cache_expires ON graph_metrics_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_reviews_user ON scheduled_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reviews_scheduled ON scheduled_reviews(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_knowledge_summaries_user ON knowledge_summaries(user_id, summary_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_summaries_created ON knowledge_summaries(created_at);

-- Triggers to maintain updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_knowledge_summaries_updated_at 
AFTER UPDATE ON knowledge_summaries
BEGIN
    UPDATE knowledge_summaries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;