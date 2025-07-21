-- Multi-Modal Memory Database Schema for Second Brain v2.6.0
-- Enhanced PostgreSQL schema supporting text, audio, video, image, and document content

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enhanced memories table with multimodal support
CREATE TABLE IF NOT EXISTS multimodal_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core content
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'text', -- text, image, audio, video, document
    
    -- Vector embeddings for different modalities
    text_vector vector(1536),           -- Text embeddings (OpenAI)
    image_vector vector(512),           -- Image embeddings (CLIP)
    audio_vector vector(768),           -- Audio embeddings (Whisper)
    multimodal_vector vector(768),      -- Combined multimodal embedding
    
    -- File information
    file_path TEXT,                     -- Path to original file
    file_name TEXT,                     -- Original filename
    file_size BIGINT,                   -- File size in bytes
    mime_type TEXT,                     -- MIME type
    file_hash VARCHAR(64),              -- SHA-256 hash for deduplication
    
    -- Content analysis
    extracted_text TEXT,               -- OCR or transcribed text
    summary TEXT,                       -- AI-generated summary
    keywords TEXT[],                    -- Extracted keywords
    entities JSONB,                     -- Named entities (person, place, etc.)
    sentiment JSONB,                    -- Sentiment analysis results
    
    -- Metadata
    metadata JSONB DEFAULT '{}',        -- Flexible metadata
    importance REAL DEFAULT 1.0,       -- 0-10 importance scale
    tags TEXT[] DEFAULT '{}',           -- User tags
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    processing_errors JSONB,           -- Error details if processing failed
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Search vectors
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            COALESCE(content, '') || ' ' || 
            COALESCE(extracted_text, '') || ' ' || 
            COALESCE(summary, '') || ' ' ||
            COALESCE(array_to_string(keywords, ' '), '')
        )
    ) STORED
);

-- Media-specific metadata tables
CREATE TABLE IF NOT EXISTS image_metadata (
    memory_id UUID PRIMARY KEY REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    width INTEGER,
    height INTEGER,
    format VARCHAR(10),                 -- JPEG, PNG, GIF, etc.
    color_mode VARCHAR(10),             -- RGB, RGBA, L, etc.
    dpi INTEGER,
    exif_data JSONB,                   -- EXIF metadata
    dominant_colors JSONB,             -- Color palette analysis
    objects_detected JSONB,            -- Object detection results
    faces_detected JSONB,              -- Face detection results
    scene_description TEXT             -- AI-generated scene description
);

CREATE TABLE IF NOT EXISTS audio_metadata (
    memory_id UUID PRIMARY KEY REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    duration REAL,                     -- Duration in seconds
    sample_rate INTEGER,               -- Sample rate in Hz
    channels INTEGER,                  -- Number of audio channels
    format VARCHAR(10),                -- MP3, WAV, FLAC, etc.
    bitrate INTEGER,                   -- Bitrate in kbps
    language VARCHAR(10),              -- Detected language
    speaker_count INTEGER,             -- Number of speakers detected
    transcript TEXT,                   -- Full transcript
    transcript_confidence REAL,       -- Transcription confidence (0-1)
    audio_features JSONB              -- Spectral features, tempo, etc.
);

CREATE TABLE IF NOT EXISTS video_metadata (
    memory_id UUID PRIMARY KEY REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    duration REAL,                     -- Duration in seconds
    width INTEGER,                     -- Video width
    height INTEGER,                    -- Video height
    fps REAL,                          -- Frames per second
    format VARCHAR(10),                -- MP4, AVI, MOV, etc.
    codec VARCHAR(20),                 -- Video codec
    bitrate INTEGER,                   -- Bitrate in kbps
    has_audio BOOLEAN DEFAULT FALSE,   -- Whether video has audio track
    frame_count INTEGER,               -- Total number of frames
    keyframes JSONB,                   -- Key frame timestamps and descriptions
    scene_changes JSONB,               -- Scene change detection results
    object_tracking JSONB             -- Object tracking data
);

CREATE TABLE IF NOT EXISTS document_metadata (
    memory_id UUID PRIMARY KEY REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    page_count INTEGER,                -- Number of pages
    word_count INTEGER,                -- Word count
    character_count INTEGER,           -- Character count
    format VARCHAR(10),                -- PDF, DOCX, PPTX, etc.
    author TEXT,                       -- Document author
    title TEXT,                        -- Document title
    subject TEXT,                      -- Document subject
    creator TEXT,                      -- Creating application
    creation_date TIMESTAMP WITH TIME ZONE,
    modification_date TIMESTAMP WITH TIME ZONE,
    table_of_contents JSONB,          -- TOC structure
    page_summaries JSONB,             -- Per-page summaries
    embedded_images INTEGER           -- Count of embedded images
);

-- Memory relationships for multimodal content
CREATE TABLE IF NOT EXISTS multimodal_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- similar, related, sequence, reference, etc.
    confidence REAL DEFAULT 0.5,      -- Relationship confidence (0-1)
    metadata JSONB DEFAULT '{}',       -- Relationship-specific metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(source_memory_id, target_memory_id, relationship_type)
);

-- Processing queue for batch operations
CREATE TABLE IF NOT EXISTS processing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES multimodal_memories(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL, -- extract_text, generate_embedding, analyze_content, etc.
    priority INTEGER DEFAULT 5,       -- 1-10 priority
    parameters JSONB DEFAULT '{}',     -- Operation parameters
    status VARCHAR(20) DEFAULT 'queued', -- queued, processing, completed, failed
    progress REAL DEFAULT 0.0,        -- Progress percentage (0-1)
    error_message TEXT,               -- Error details if failed
    worker_id TEXT,                   -- ID of worker processing this item
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_processing_queue_status (status),
    INDEX idx_processing_queue_priority (priority DESC)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_content_type ON multimodal_memories(content_type);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_file_hash ON multimodal_memories(file_hash);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_processing_status ON multimodal_memories(processing_status);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_created_at ON multimodal_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_importance ON multimodal_memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_tags ON multimodal_memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_search ON multimodal_memories USING GIN(search_vector);

-- Vector similarity indexes
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_text_vector ON multimodal_memories 
    USING ivfflat (text_vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_image_vector ON multimodal_memories 
    USING ivfflat (image_vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_audio_vector ON multimodal_memories 
    USING ivfflat (audio_vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_multimodal_memories_multimodal_vector ON multimodal_memories 
    USING ivfflat (multimodal_vector vector_cosine_ops) WITH (lists = 100);

-- Relationship indexes
CREATE INDEX IF NOT EXISTS idx_multimodal_relationships_source ON multimodal_relationships(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_multimodal_relationships_target ON multimodal_relationships(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_multimodal_relationships_type ON multimodal_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_multimodal_relationships_confidence ON multimodal_relationships(confidence DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_multimodal_memories_updated_at 
    BEFORE UPDATE ON multimodal_memories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing
INSERT INTO multimodal_memories (content, content_type, importance, tags, metadata) VALUES
('Welcome to the multimodal Second Brain system. This supports text, images, audio, video, and documents.', 
 'text', 9.0, ARRAY['welcome', 'documentation', 'multimodal'], 
 '{"category": "system", "version": "2.6.0"}'),
 
('Sample image description for testing multimodal capabilities.', 
 'image', 7.5, ARRAY['sample', 'test', 'image'], 
 '{"file_type": "jpg", "test_data": true}'),
 
('Audio transcription example for voice memos and recordings.', 
 'audio', 8.0, ARRAY['audio', 'transcription', 'voice'], 
 '{"duration": 30.5, "sample_rate": 44100}'),
 
('Video content description with scene analysis capabilities.', 
 'video', 8.5, ARRAY['video', 'analysis', 'multimedia'], 
 '{"duration": 120.0, "resolution": "1080p"}'),
 
('Document processing example with full-text extraction and analysis.', 
 'document', 7.0, ARRAY['document', 'pdf', 'processing'], 
 '{"pages": 5, "word_count": 1250}');

-- Create view for simplified multimodal queries
CREATE OR REPLACE VIEW multimodal_summary AS
SELECT 
    m.id,
    m.content,
    m.content_type,
    m.importance,
    m.tags,
    m.file_name,
    m.processing_status,
    CASE 
        WHEN m.content_type = 'image' THEN i.width || 'x' || i.height
        WHEN m.content_type = 'audio' THEN a.duration || 's'
        WHEN m.content_type = 'video' THEN v.duration || 's @ ' || v.fps || 'fps'
        WHEN m.content_type = 'document' THEN d.page_count || ' pages'
        ELSE 'N/A'
    END as format_info,
    m.created_at,
    m.updated_at
FROM multimodal_memories m
LEFT JOIN image_metadata i ON m.id = i.memory_id
LEFT JOIN audio_metadata a ON m.id = a.memory_id  
LEFT JOIN video_metadata v ON m.id = v.memory_id
LEFT JOIN document_metadata d ON m.id = d.memory_id;

COMMENT ON TABLE multimodal_memories IS 'Enhanced memory storage supporting text, image, audio, video, and document content types';
COMMENT ON TABLE processing_queue IS 'Queue for background processing of multimodal content';
COMMENT ON VIEW multimodal_summary IS 'Simplified view of multimodal memories with format-specific information';
