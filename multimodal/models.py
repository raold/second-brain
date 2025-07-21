"""
Multi-Modal Memory Models for Second Brain v2.6.0
Comprehensive models supporting text, audio, video, image, and document content
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator
from pydantic.types import conint, confloat


class ContentType(str, Enum):
    """Supported content types for multimodal memories."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class ProcessingStatus(str, Enum):
    """Processing status for multimodal content."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RelationshipType(str, Enum):
    """Types of relationships between memories."""
    SIMILAR = "similar"
    RELATED = "related"
    SEQUENCE = "sequence"
    REFERENCE = "reference"
    CONTAINS = "contains"
    DERIVED = "derived"
    DUPLICATE = "duplicate"


# Base Models

class BaseMemoryModel(BaseModel):
    """Base model for all memory-related models."""
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# Core Memory Models

class MultiModalMemoryCreate(BaseMemoryModel):
    """Model for creating multimodal memories."""
    content: str = Field(..., description="Primary content text")
    content_type: ContentType = Field(ContentType.TEXT, description="Type of content")
    
    # File information
    file_path: Optional[str] = Field(None, description="Path to original file")
    file_name: Optional[str] = Field(None, description="Original filename")
    mime_type: Optional[str] = Field(None, description="MIME type")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    importance: confloat(ge=0.0, le=10.0) = Field(1.0, description="Importance score (0-10)")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    
    # Content analysis
    extracted_text: Optional[str] = Field(None, description="Extracted/transcribed text")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Named entities")
    sentiment: Dict[str, Any] = Field(default_factory=dict, description="Sentiment analysis")


class MultiModalMemoryUpdate(BaseMemoryModel):
    """Model for updating multimodal memories."""
    content: Optional[str] = None
    importance: Optional[confloat(ge=0.0, le=10.0)] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    entities: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, Any]] = None


class MultiModalMemoryResponse(BaseMemoryModel):
    """Model for multimodal memory responses."""
    id: UUID
    content: str
    content_type: ContentType
    
    # File information
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None
    
    # Content analysis
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = []
    entities: Dict[str, Any] = {}
    sentiment: Dict[str, Any] = {}
    
    # Metadata
    metadata: Dict[str, Any] = {}
    importance: float
    tags: List[str] = []
    
    # Processing status
    processing_status: ProcessingStatus
    processing_errors: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


# Media-specific metadata models

class ImageMetadata(BaseMemoryModel):
    """Metadata specific to image content."""
    memory_id: UUID
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None  # JPEG, PNG, GIF, etc.
    color_mode: Optional[str] = None  # RGB, RGBA, L, etc.
    dpi: Optional[int] = None
    exif_data: Dict[str, Any] = {}
    dominant_colors: Dict[str, Any] = {}
    objects_detected: Dict[str, Any] = {}
    faces_detected: Dict[str, Any] = {}
    scene_description: Optional[str] = None


class AudioMetadata(BaseMemoryModel):
    """Metadata specific to audio content."""
    memory_id: UUID
    duration: Optional[float] = None  # Duration in seconds
    sample_rate: Optional[int] = None  # Sample rate in Hz
    channels: Optional[int] = None  # Number of audio channels
    format: Optional[str] = None  # MP3, WAV, FLAC, etc.
    bitrate: Optional[int] = None  # Bitrate in kbps
    language: Optional[str] = None  # Detected language
    speaker_count: Optional[int] = None  # Number of speakers
    transcript: Optional[str] = None  # Full transcript
    transcript_confidence: Optional[confloat(ge=0.0, le=1.0)] = None
    audio_features: Dict[str, Any] = {}  # Spectral features, tempo, etc.


class VideoMetadata(BaseMemoryModel):
    """Metadata specific to video content."""
    memory_id: UUID
    duration: Optional[float] = None  # Duration in seconds
    width: Optional[int] = None  # Video width
    height: Optional[int] = None  # Video height
    fps: Optional[float] = None  # Frames per second
    format: Optional[str] = None  # MP4, AVI, MOV, etc.
    codec: Optional[str] = None  # Video codec
    bitrate: Optional[int] = None  # Bitrate in kbps
    has_audio: bool = False  # Whether video has audio track
    frame_count: Optional[int] = None  # Total number of frames
    keyframes: Dict[str, Any] = {}  # Key frame data
    scene_changes: Dict[str, Any] = {}  # Scene change detection
    object_tracking: Dict[str, Any] = {}  # Object tracking data


class DocumentMetadata(BaseMemoryModel):
    """Metadata specific to document content."""
    memory_id: UUID
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    format: Optional[str] = None  # PDF, DOCX, PPTX, etc.
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None  # Creating application
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    table_of_contents: Dict[str, Any] = {}
    page_summaries: Dict[str, Any] = {}
    embedded_images: Optional[int] = None


# Relationship Models

class MultiModalRelationshipCreate(BaseMemoryModel):
    """Model for creating relationships between memories."""
    source_memory_id: UUID
    target_memory_id: UUID
    relationship_type: RelationshipType
    confidence: confloat(ge=0.0, le=1.0) = 0.5
    metadata: Dict[str, Any] = {}


class MultiModalRelationshipResponse(BaseMemoryModel):
    """Model for relationship responses."""
    id: UUID
    source_memory_id: UUID
    target_memory_id: UUID
    relationship_type: RelationshipType
    confidence: float
    metadata: Dict[str, Any] = {}
    created_at: datetime


# Processing Models

class ProcessingQueueItem(BaseMemoryModel):
    """Model for processing queue items."""
    id: UUID
    memory_id: UUID
    operation_type: str  # extract_text, generate_embedding, analyze_content, etc.
    priority: conint(ge=1, le=10) = 5
    parameters: Dict[str, Any] = {}
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: confloat(ge=0.0, le=1.0) = 0.0
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# Search Models

class MultiModalSearchRequest(BaseMemoryModel):
    """Model for multimodal search requests."""
    query: str = Field(..., description="Search query")
    content_types: Optional[List[ContentType]] = Field(None, description="Filter by content types")
    limit: conint(ge=1, le=100) = Field(20, description="Maximum results")
    offset: conint(ge=0) = Field(0, description="Result offset")
    threshold: confloat(ge=0.0, le=1.0) = Field(0.7, description="Similarity threshold")
    importance_min: Optional[confloat(ge=0.0, le=10.0)] = Field(None, description="Minimum importance")
    importance_max: Optional[confloat(ge=0.0, le=10.0)] = Field(None, description="Maximum importance")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    date_from: Optional[datetime] = Field(None, description="Filter by creation date from")
    date_to: Optional[datetime] = Field(None, description="Filter by creation date to")
    include_processing: bool = Field(False, description="Include memories being processed")


class MultiModalSearchResult(BaseMemoryModel):
    """Individual search result."""
    memory: MultiModalMemoryResponse
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    relevance_score: float = Field(..., description="Combined relevance score")
    match_type: str = Field(..., description="Type of match (text, vector, hybrid)")


class MultiModalSearchResponse(BaseMemoryModel):
    """Complete search response."""
    results: List[MultiModalSearchResult]
    total_count: int = Field(..., description="Total matching memories")
    query: str = Field(..., description="Original search query")
    processing_time: float = Field(..., description="Processing time in seconds")
    filters_applied: Dict[str, Any] = Field(..., description="Applied filters")


# Statistics Models

class MultiModalStats(BaseMemoryModel):
    """Statistics for multimodal content."""
    total_memories: int
    memories_by_type: Dict[ContentType, int]
    processing_queue_size: int
    storage_usage: Dict[str, int]  # Bytes by content type
    recent_activity: Dict[str, int]  # Activity counts
    performance_metrics: Dict[str, float]
    health_status: str


# File Upload Models

class FileUploadRequest(BaseMemoryModel):
    """Model for file upload requests."""
    content: Optional[str] = Field(None, description="Optional content description")
    importance: confloat(ge=0.0, le=10.0) = Field(5.0, description="Importance score")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    auto_process: bool = Field(True, description="Auto-process after upload")
    extract_text: bool = Field(True, description="Extract text from content")
    generate_summary: bool = Field(True, description="Generate AI summary")
    analyze_content: bool = Field(True, description="Perform content analysis")


class FileUploadResponse(BaseMemoryModel):
    """Response for file upload."""
    memory_id: UUID
    file_name: str
    file_size: int
    content_type: ContentType
    processing_status: ProcessingStatus
    message: str


# Validation helpers

@validator('tags', pre=True)
def validate_tags(cls, v):
    """Validate and clean tags."""
    if isinstance(v, str):
        v = [tag.strip() for tag in v.split(',')]
    return [tag.lower().strip() for tag in v if tag.strip()]


@validator('importance')
def validate_importance(cls, v):
    """Validate importance score."""
    return max(0.0, min(10.0, float(v)))


# Export all models
__all__ = [
    'ContentType',
    'ProcessingStatus', 
    'RelationshipType',
    'MultiModalMemoryCreate',
    'MultiModalMemoryUpdate',
    'MultiModalMemoryResponse',
    'ImageMetadata',
    'AudioMetadata',
    'VideoMetadata',
    'DocumentMetadata',
    'MultiModalRelationshipCreate',
    'MultiModalRelationshipResponse',
    'ProcessingQueueItem',
    'MultiModalSearchRequest',
    'MultiModalSearchResult',
    'MultiModalSearchResponse',
    'MultiModalStats',
    'FileUploadRequest',
    'FileUploadResponse'
]
