-- Google Drive Integration Database Schema
-- Based on Gemini 2.5 Pro recommendations for enterprise streaming architecture

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- User Google credentials (encrypted storage)
CREATE TABLE user_google_credentials (
    user_id UUID PRIMARY KEY,
    encrypted_refresh_token TEXT NOT NULL,
    access_token_hash VARCHAR(255), -- For cache validation only
    drive_permissions JSONB DEFAULT '{}',
    quota_info JSONB DEFAULT '{}',
    webhook_resource_id VARCHAR(255), -- For Drive change notifications
    webhook_expiration TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_google_credentials_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Drive files metadata and processing tracking
CREATE TABLE gdrive_files (
    file_id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    mime_type VARCHAR(255),
    size_bytes BIGINT,
    md5_checksum VARCHAR(255),
    modified_time TIMESTAMP,
    processed_at TIMESTAMP,
    memory_id UUID,
    parent_folders TEXT[] DEFAULT '{}', -- Array of folder IDs
    drive_metadata JSONB DEFAULT '{}', -- Full Drive API response
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_priority INTEGER DEFAULT 5, -- 1=highest, 10=lowest
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    ai_extracted_entities JSONB DEFAULT '{}', -- From Natural Language API
    document_structure JSONB DEFAULT '{}', -- From Document AI
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_gdrive_files_memory_id 
        FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE SET NULL,
    CONSTRAINT fk_gdrive_files_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Drive folders for hierarchical organization
CREATE TABLE gdrive_folders (
    folder_id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    parent_folder_id VARCHAR(255),
    sync_enabled BOOLEAN DEFAULT false, -- User-selected folders to sync
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_gdrive_folders_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_gdrive_folders_parent 
        FOREIGN KEY (parent_folder_id) REFERENCES gdrive_folders(folder_id) ON DELETE CASCADE
);

-- Background job processing queue
CREATE TABLE gdrive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    file_id VARCHAR(255),
    folder_id VARCHAR(255),
    job_type VARCHAR(50) NOT NULL, -- 'initial_sync', 'file_update', 'file_delete', 'folder_sync'
    status VARCHAR(50) DEFAULT 'queued', -- 'queued', 'processing', 'completed', 'failed', 'cancelled'
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    job_data JSONB DEFAULT '{}', -- Job-specific parameters
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT fk_gdrive_jobs_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Webhook change notifications tracking
CREATE TABLE gdrive_change_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    file_id VARCHAR(255),
    change_type VARCHAR(50), -- 'add', 'update', 'remove', 'trash'
    notification_data JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    CONSTRAINT fk_gdrive_changes_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- API rate limiting tracking
CREATE TABLE gdrive_api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT NOW(),
    window_duration INTERVAL DEFAULT '1 minute',
    
    CONSTRAINT fk_gdrive_api_usage_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Processing performance metrics
CREATE TABLE gdrive_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    metric_type VARCHAR(100) NOT NULL, -- 'file_processing_time', 'api_call_duration', etc.
    metric_value NUMERIC,
    file_type VARCHAR(100),
    file_size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_gdrive_metrics_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance optimization
-- User-based queries
CREATE INDEX idx_gdrive_files_user_id ON gdrive_files(user_id);
CREATE INDEX idx_gdrive_folders_user_id ON gdrive_folders(user_id);
CREATE INDEX idx_gdrive_jobs_user_id ON gdrive_jobs(user_id);

-- Processing status queries
CREATE INDEX idx_gdrive_files_status ON gdrive_files(processing_status);
CREATE INDEX idx_gdrive_files_modified_time ON gdrive_files(modified_time);
CREATE INDEX idx_gdrive_jobs_status ON gdrive_jobs(status);
CREATE INDEX idx_gdrive_jobs_priority ON gdrive_jobs(priority, created_at);

-- Change detection queries
CREATE INDEX idx_gdrive_files_md5_checksum ON gdrive_files(md5_checksum);
CREATE INDEX idx_gdrive_changes_processed ON gdrive_change_notifications(processed, created_at);

-- Performance monitoring
CREATE INDEX idx_gdrive_metrics_type_time ON gdrive_metrics(metric_type, recorded_at);
CREATE INDEX idx_gdrive_api_usage_window ON gdrive_api_usage(user_id, api_endpoint, window_start);

-- Folder hierarchy queries
CREATE INDEX idx_gdrive_folders_parent ON gdrive_folders(parent_folder_id);
CREATE INDEX idx_gdrive_folders_sync_enabled ON gdrive_folders(user_id, sync_enabled);

-- Job queue optimization
CREATE INDEX idx_gdrive_jobs_queue ON gdrive_jobs(status, priority, created_at) 
    WHERE status IN ('queued', 'processing');

-- File relationships
CREATE INDEX idx_gdrive_files_memory_id ON gdrive_files(memory_id) WHERE memory_id IS NOT NULL;

-- Functions for common operations
-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to relevant tables
CREATE TRIGGER update_gdrive_files_updated_at 
    BEFORE UPDATE ON gdrive_files 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gdrive_folders_updated_at 
    BEFORE UPDATE ON gdrive_folders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_google_credentials_updated_at 
    BEFORE UPDATE ON user_google_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get pending jobs by priority
CREATE OR REPLACE FUNCTION get_next_gdrive_job()
RETURNS TABLE (
    job_id UUID,
    user_id UUID,
    file_id VARCHAR(255),
    job_type VARCHAR(50),
    job_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    UPDATE gdrive_jobs 
    SET status = 'processing', started_at = NOW()
    WHERE id = (
        SELECT gj.id FROM gdrive_jobs gj
        WHERE gj.status = 'queued' 
        AND gj.retry_count < gj.max_retries
        ORDER BY gj.priority ASC, gj.created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING gdrive_jobs.id, gdrive_jobs.user_id, gdrive_jobs.file_id, 
              gdrive_jobs.job_type, gdrive_jobs.job_data;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate user's Drive usage statistics
CREATE OR REPLACE FUNCTION get_user_gdrive_stats(p_user_id UUID)
RETURNS TABLE (
    total_files INTEGER,
    total_size_bytes BIGINT,
    processed_files INTEGER,
    pending_files INTEGER,
    last_sync TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_files,
        COALESCE(SUM(gf.size_bytes), 0) as total_size_bytes,
        COUNT(CASE WHEN gf.processing_status = 'completed' THEN 1 END)::INTEGER as processed_files,
        COUNT(CASE WHEN gf.processing_status IN ('pending', 'processing') THEN 1 END)::INTEGER as pending_files,
        MAX(gf.processed_at) as last_sync
    FROM gdrive_files gf
    WHERE gf.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- View for dashboard statistics
CREATE VIEW gdrive_dashboard_stats AS
SELECT 
    ugc.user_id,
    gds.total_files,
    gds.total_size_bytes,
    gds.processed_files,
    gds.pending_files,
    gds.last_sync,
    COUNT(gj.id) as queued_jobs,
    ugc.webhook_expiration,
    CASE 
        WHEN ugc.webhook_expiration > NOW() THEN 'active'
        ELSE 'expired'
    END as webhook_status
FROM user_google_credentials ugc
LEFT JOIN LATERAL get_user_gdrive_stats(ugc.user_id) gds ON true
LEFT JOIN gdrive_jobs gj ON gj.user_id = ugc.user_id AND gj.status = 'queued'
GROUP BY ugc.user_id, gds.total_files, gds.total_size_bytes, 
         gds.processed_files, gds.pending_files, gds.last_sync, ugc.webhook_expiration;

-- Insert default admin user's Google credentials placeholder (if admin user exists)
INSERT INTO user_google_credentials (user_id, encrypted_refresh_token)
SELECT id, 'placeholder_token_not_configured'
FROM users 
WHERE email = 'admin@example.com'
ON CONFLICT (user_id) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE user_google_credentials IS 'Encrypted storage for Google OAuth tokens and Drive permissions';
COMMENT ON TABLE gdrive_files IS 'Metadata and processing status for all user Drive files';
COMMENT ON TABLE gdrive_folders IS 'Drive folder hierarchy and sync preferences';
COMMENT ON TABLE gdrive_jobs IS 'Background job queue for file processing tasks';
COMMENT ON TABLE gdrive_change_notifications IS 'Webhook notifications from Google Drive';
COMMENT ON TABLE gdrive_metrics IS 'Performance and usage metrics for monitoring';

COMMENT ON COLUMN user_google_credentials.encrypted_refresh_token IS 'Fernet-encrypted refresh token for long-term access';
COMMENT ON COLUMN gdrive_files.md5_checksum IS 'Used for change detection - only reprocess if hash changes';
COMMENT ON COLUMN gdrive_files.processing_status IS 'pending, processing, completed, failed, skipped';
COMMENT ON COLUMN gdrive_jobs.job_type IS 'Type of background job: initial_sync, file_update, file_delete, folder_sync';
COMMENT ON COLUMN gdrive_folders.sync_enabled IS 'User-selected folders to actively monitor and process';