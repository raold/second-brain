-- Second Brain v2.8.2 Synthesis Tables Migration
-- Created: 2025-01-23
-- Description: Adds tables for synthesis features (reports, spaced repetition, websocket events)

-- Report Templates Table
CREATE TABLE IF NOT EXISTS report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    report_type VARCHAR(50) NOT NULL,
    sections JSONB NOT NULL DEFAULT '[]',
    default_format VARCHAR(20) NOT NULL DEFAULT 'pdf',
    custom_css TEXT,
    include_summary BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Report Schedules Table
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    cron_expression VARCHAR(255) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    auto_deliver BOOLEAN DEFAULT true,
    delivery_format VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE
);

-- Generated Reports Table
CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    config JSONB NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    sections JSONB NOT NULL DEFAULT '[]',
    metrics JSONB NOT NULL DEFAULT '{}',
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generation_time_ms INTEGER NOT NULL,
    format VARCHAR(20) NOT NULL,
    content TEXT,
    file_url TEXT,
    file_size_bytes INTEGER,
    delivered BOOLEAN DEFAULT false,
    delivery_status TEXT
);

-- Memory Strengths Table (Spaced Repetition)
CREATE TABLE IF NOT EXISTS memory_strengths (
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE PRIMARY KEY,
    ease_factor DECIMAL(3,2) DEFAULT 2.5,
    interval INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 0.0,
    average_difficulty DECIMAL(3,2) DEFAULT 3.0,
    retention_rate DECIMAL(3,2) DEFAULT 0.9,
    stability DECIMAL(4,2) DEFAULT 1.0,
    retrievability DECIMAL(3,2) DEFAULT 1.0,
    last_review TIMESTAMP WITH TIME ZONE,
    next_review TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Review Schedules Table
CREATE TABLE IF NOT EXISTS review_schedules (
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE PRIMARY KEY,
    scheduled_date TIMESTAMP WITH TIME ZONE NOT NULL,
    interval_days INTEGER NOT NULL,
    priority DECIMAL(4,2) DEFAULT 1.0,
    earliest_date TIMESTAMP WITH TIME ZONE NOT NULL,
    latest_date TIMESTAMP WITH TIME ZONE NOT NULL,
    optimal_time TIME,
    algorithm VARCHAR(20) NOT NULL DEFAULT 'sm2'
);

-- Review Sessions Table
CREATE TABLE IF NOT EXISTS review_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    total_reviews INTEGER DEFAULT 0,
    completed_reviews INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(3,2) DEFAULT 0.0,
    average_time_seconds DECIMAL(10,2) DEFAULT 0.0,
    difficulty_distribution JSONB DEFAULT '{"again": 0, "hard": 0, "good": 0, "easy": 0}',
    best_streak INTEGER DEFAULT 0
);

-- Review Results Table
CREATE TABLE IF NOT EXISTS review_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    session_id VARCHAR(255) REFERENCES review_sessions(id) ON DELETE CASCADE,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    time_taken_seconds INTEGER NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 4),
    interval_change INTEGER NOT NULL,
    confidence_level DECIMAL(3,2),
    notes TEXT,
    streak INTEGER DEFAULT 0
);

-- WebSocket Subscriptions Table
CREATE TABLE IF NOT EXISTS websocket_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) NOT NULL,
    event_types TEXT[] NOT NULL,
    patterns TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- WebSocket Event Log Table (optional, for analytics)
CREATE TABLE IF NOT EXISTS websocket_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    connection_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_report_schedules_enabled ON report_schedules(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_report_schedules_next_run ON report_schedules(next_run) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_generated_reports_user_id ON generated_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_generated_at ON generated_reports(generated_at);
CREATE INDEX IF NOT EXISTS idx_memory_strengths_next_review ON memory_strengths(next_review);
CREATE INDEX IF NOT EXISTS idx_review_schedules_scheduled_date ON review_schedules(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_review_schedules_priority ON review_schedules(priority DESC);
CREATE INDEX IF NOT EXISTS idx_review_results_memory_id ON review_results(memory_id);
CREATE INDEX IF NOT EXISTS idx_review_results_session_id ON review_results(session_id);
CREATE INDEX IF NOT EXISTS idx_review_sessions_user_id ON review_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_websocket_subscriptions_user_id ON websocket_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_websocket_subscriptions_connection_id ON websocket_subscriptions(connection_id);
CREATE INDEX IF NOT EXISTS idx_websocket_events_user_id ON websocket_events(user_id);
CREATE INDEX IF NOT EXISTS idx_websocket_events_created_at ON websocket_events(created_at);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_report_templates_updated_at BEFORE UPDATE ON report_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add constraints
ALTER TABLE review_results ADD CONSTRAINT check_difficulty_valid CHECK (difficulty IN (1, 2, 3, 4));
ALTER TABLE memory_strengths ADD CONSTRAINT check_ease_factor_range CHECK (ease_factor >= 1.3);
ALTER TABLE memory_strengths ADD CONSTRAINT check_success_rate_range CHECK (success_rate >= 0 AND success_rate <= 1);
ALTER TABLE memory_strengths ADD CONSTRAINT check_retention_rate_range CHECK (retention_rate >= 0 AND retention_rate <= 1);
ALTER TABLE memory_strengths ADD CONSTRAINT check_retrievability_range CHECK (retrievability >= 0 AND retrievability <= 1);

-- Grant permissions (adjust based on your user setup)
GRANT ALL ON report_templates TO second_brain_user;
GRANT ALL ON report_schedules TO second_brain_user;
GRANT ALL ON generated_reports TO second_brain_user;
GRANT ALL ON memory_strengths TO second_brain_user;
GRANT ALL ON review_schedules TO second_brain_user;
GRANT ALL ON review_sessions TO second_brain_user;
GRANT ALL ON review_results TO second_brain_user;
GRANT ALL ON websocket_subscriptions TO second_brain_user;
GRANT ALL ON websocket_events TO second_brain_user;

-- Add comment
COMMENT ON SCHEMA public IS 'Second Brain v2.8.2 - Synthesis Features';