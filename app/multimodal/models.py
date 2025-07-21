"""
Multi-Modal Memory Models for Second Brain v2.6.0
Comprehensive models supporting text, audio, video, images, and documents.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ContentType(str, Enum):
    """Supported content types for multi-modal memories."""
    TEXT = "text"
    AUDIO = "audio" 
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    MIXED = "mixed"  # For memories with multiple content types


class MediaFormat(str, Enum):
    """Supported media formats."""
    # Text formats
    PLAIN_TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    HTML = "text/html"
    
    # Audio formats
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    M4A = "audio/m4a"
    OGG = "audio/ogg"
    WEBM_AUDIO = "audio/webm"
    
    # Video formats
    MP4 = "video/mp4"
    WEBM_VIDEO = "video/webm"
    AVI = "video/avi"
    MOV = "video/quicktime"
    MKV = "video/mkv"
    
    # Image formats
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    SVG = "image/svg+xml"
    
    # Document formats
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    TXT = "text/plain"


class ProcessingStatus(str, Enum):
    """Processing status for multi-modal content."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some components processed successfully


class AudioMetadata(BaseModel):
    """Metadata specific to audio content."""
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bitrate: Optional[int] = None
    format: Optional[MediaFormat] = None
    transcription: Optional[str] = None
    transcription_confidence: Optional[float] = None
    language: Optional[str] = None
    speaker_count: Optional[int] = None
    audio_fingerprint: Optional[str] = None  # For duplicate detection


class VideoMetadata(BaseModel):
    """Metadata specific to video content."""
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    format: Optional[MediaFormat] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    has_audio: Optional[bool] = None
    audio_metadata: Optional[AudioMetadata] = None
    frame_count: Optional[int] = None
    keyframe_timestamps: Optional[List[float]] = None
    video_fingerprint: Optional[str] = None


class ImageMetadata(BaseModel):
    """Metadata specific to image content."""
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[MediaFormat] = None
    color_mode: Optional[str] = None
    has_transparency: Optional[bool] = None
    dpi: Optional[int] = None
    exif_data: Optional[Dict[str, Any]] = None
    dominant_colors: Optional[List[str]] = None  # Hex color codes
    detected_objects: Optional[List[str]] = None
    detected_text: Optional[str] = None  # OCR results
    image_hash: Optional[str] = None  # Perceptual hash for similarity


class DocumentMetadata(BaseModel):
    """Metadata specific to document content."""
    page_count: Optional[int] = None
    format: Optional[MediaFormat] = None
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    extracted_images_count: Optional[int] = None
    has_table_of_contents: Optional[bool] = None
    document_hash: Optional[str] = None


class ProcessingResult(BaseModel):
    """Result of content processing."""
    success: bool
    content_type: ContentType
    extracted_text: Optional[str] = None
    embeddings: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    confidence_score: Optional[float] = None


class MultiModalContent(BaseModel):
    """Container for multi-modal content data."""
    content_type: ContentType
    primary_text: Optional[str] = None  # Main text content or transcript
    raw_content: Optional[bytes] = None  # Binary data for media files
    file_path: Optional[str] = None  # Path to stored file
    file_size_bytes: Optional[int] = None
    content_hash: Optional[str] = None  # SHA-256 hash for deduplication
    mime_type: Optional[str] = None
    
    # Type-specific metadata
    audio_metadata: Optional[AudioMetadata] = None
    video_metadata: Optional[VideoMetadata] = None
    image_metadata: Optional[ImageMetadata] = None
    document_metadata: Optional[DocumentMetadata] = None
    
    # Processing information
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_results: Optional[List[ProcessingResult]] = None
    last_processed: Optional[datetime] = None


class MultiModalMemory(BaseModel):
    """Enhanced memory model supporting multi-modal content."""
    
    # Core memory fields
    id: Optional[str] = None
    content_type: ContentType
    primary_content: str = Field(..., description="Primary text content or description")
    
    # Multi-modal content
    multimodal_content: Optional[MultiModalContent] = None
    
    # Enhanced metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible metadata storage")
    importance: float = Field(default=1.0, ge=0.0, le=10.0, description="Importance score")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    
    # Embeddings for different modalities
    text_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    audio_embedding: Optional[List[float]] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    
    # Processing status
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_errors: Optional[List[str]] = None

    @validator('primary_content')
    def validate_primary_content(cls, v, values):
        """Ensure primary_content is not empty."""
        if not v or not v.strip():
            raise ValueError("Primary content cannot be empty")
        return v.strip()

    @validator('importance')
    def validate_importance(cls, v):
        """Ensure importance is within valid range."""
        return max(0.0, min(10.0, v))


class MultiModalSearchRequest(BaseModel):
    """Search request for multi-modal memories."""
    
    # Text query (always supported)
    text_query: Optional[str] = None
    
    # Content type filters
    content_types: Optional[List[ContentType]] = None
    
    # File-based queries
    image_query: Optional[bytes] = None  # Image similarity search
    audio_query: Optional[bytes] = None  # Audio similarity search
    
    # Standard filters
    tags: Optional[List[str]] = None
    importance_min: Optional[float] = None
    importance_max: Optional[float] = None
    
    # Date range filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Search parameters
    limit: int = Field(default=20, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Multi-modal search weights
    text_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    image_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    audio_weight: float = Field(default=0.1, ge=0.0, le=1.0)

    @validator('content_types')
    def validate_content_types(cls, v):
        """Remove duplicates from content types."""
        return list(set(v)) if v else None


class MultiModalSearchResult(BaseModel):
    """Search result for multi-modal memories."""
    memory: MultiModalMemory
    relevance_score: float = Field(description="Combined relevance score")
    similarity_scores: Dict[str, float] = Field(default_factory=dict)  # Per-modality scores
    rank: int = Field(description="Result rank")
    matched_content_types: List[ContentType] = Field(default_factory=list)
    explanation: Optional[str] = None  # Why this result matched


class ContentUploadRequest(BaseModel):
    """Request model for uploading multi-modal content."""
    content_type: ContentType
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    importance: float = Field(default=1.0, ge=0.0, le=10.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing options
    extract_text: bool = Field(default=True, description="Extract text from media")
    generate_embeddings: bool = Field(default=True, description="Generate embeddings")
    analyze_content: bool = Field(default=True, description="Perform content analysis")


class ProcessingConfig(BaseModel):
    """Configuration for multi-modal processing."""
    
    # Text processing
    max_text_length: int = 50000
    extract_entities: bool = True
    detect_language: bool = True
    
    # Audio processing
    transcription_model: str = "whisper-1"
    speaker_diarization: bool = False
    audio_embedding_model: str = "openai-audio"
    
    # Video processing  
    extract_frames: bool = True
    frame_interval_seconds: float = 10.0
    max_frames: int = 50
    extract_audio_track: bool = True
    
    # Image processing
    perform_ocr: bool = True
    detect_objects: bool = True
    extract_dominant_colors: bool = True
    generate_alt_text: bool = True
    max_image_dimension: int = 2048
    
    # Document processing
    extract_metadata: bool = True
    extract_images: bool = True
    preserve_formatting: bool = False
    chunk_size: int = 1000
    
    # Storage settings
    store_original_files: bool = True
    compress_media: bool = True
    generate_thumbnails: bool = True
