-- Second Brain PostgreSQL + pgvector initialization
-- This script sets up the database with required extensions and tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the memories table with pgvector support
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    content_vector vector(1536),  -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}',
    importance REAL DEFAULT 1.0 CHECK (importance >= 0.0 AND importance <= 10.0),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_vector 
ON memories USING ivfflat (content_vector vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_memories_search 
ON memories USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_memories_tags 
ON memories USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_memories_importance 
ON memories (importance DESC);

CREATE INDEX IF NOT EXISTS idx_memories_created_at 
ON memories (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memories_metadata 
ON memories USING GIN (metadata);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_memories_updated_at 
    BEFORE UPDATE ON memories 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for demonstration
INSERT INTO memories (content, importance, tags) VALUES
    ('Learning about PostgreSQL vector extensions and how they can improve semantic search capabilities.', 8.5, ARRAY['postgresql', 'vector', 'database', 'learning']),
    ('FastAPI provides excellent async support and automatic API documentation with OpenAPI.', 7.2, ARRAY['fastapi', 'python', 'api', 'development']),
    ('D3.js is a powerful library for creating interactive data visualizations in web browsers.', 6.8, ARRAY['d3js', 'visualization', 'javascript', 'web']),
    ('Understanding the importance of proper indexing strategies for vector similarity search.', 9.1, ARRAY['indexing', 'performance', 'vector', 'optimization']),
    ('Building a modern dashboard requires careful consideration of user experience and responsive design.', 5.5, ARRAY['dashboard', 'ui', 'ux', 'design'])
ON CONFLICT DO NOTHING;

-- Create a view for analytics
CREATE OR REPLACE VIEW memory_analytics AS
SELECT 
    COUNT(*) as total_memories,
    AVG(importance) as avg_importance,
    COUNT(*) FILTER (WHERE importance > 7.0) as high_importance_count,
    COUNT(DISTINCT tag) as unique_tags,
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as daily_count
FROM memories
CROSS JOIN UNNEST(tags) as tag
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY day DESC;

-- Grant necessary permissions (if needed for specific users)
-- GRANT ALL PRIVILEGES ON TABLE memories TO second_brain_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO second_brain_user;

-- Output success message
DO $$
BEGIN
    RAISE NOTICE 'Second Brain database initialized successfully!';
    RAISE NOTICE 'Extensions enabled: vector, pg_trgm, uuid-ossp';
    RAISE NOTICE 'Tables created: memories';
    RAISE NOTICE 'Indexes created for optimal performance';
    RAISE NOTICE 'Sample data inserted for demonstration';
END $$; 