"""
Test suite for multi-modal models in Second Brain v2.6.0
Comprehensive testing of data models, validation, and serialization.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock, patch

# Import the models we're testing
from app.multimodal.models import (
    ContentType, MediaFormat, ProcessingStatus,
    AudioMetadata, VideoMetadata, ImageMetadata, DocumentMetadata,
    ProcessingResult, MultiModalContent, MultiModalMemory,
    MultiModalSearchRequest, MultiModalSearchResult,
    ContentUploadRequest, ProcessingConfig
)


class TestContentTypeEnum:
    """Test ContentType enumeration."""
    
    def test_content_type_values(self):
        """Test all content type values are correct."""
        assert ContentType.TEXT == "text"
        assert ContentType.AUDIO == "audio"
        assert ContentType.VIDEO == "video"
        assert ContentType.IMAGE == "image"
        assert ContentType.DOCUMENT == "document"
        assert ContentType.MIXED == "mixed"
    
    def test_content_type_membership(self):
        """Test membership in ContentType enum."""
        assert "text" in [ct.value for ct in ContentType]
        assert "invalid_type" not in [ct.value for ct in ContentType]


class TestMediaFormatEnum:
    """Test MediaFormat enumeration."""
    
    def test_audio_formats(self):
        """Test audio format constants."""
        assert MediaFormat.MP3 == "audio/mpeg"
        assert MediaFormat.WAV == "audio/wav"
        assert MediaFormat.M4A == "audio/m4a"
    
    def test_video_formats(self):
        """Test video format constants."""
        assert MediaFormat.MP4 == "video/mp4"
        assert MediaFormat.WEBM_VIDEO == "video/webm"
        assert MediaFormat.AVI == "video/avi"
    
    def test_image_formats(self):
        """Test image format constants."""
        assert MediaFormat.JPEG == "image/jpeg"
        assert MediaFormat.PNG == "image/png"
        assert MediaFormat.GIF == "image/gif"
    
    def test_document_formats(self):
        """Test document format constants."""
        assert MediaFormat.PDF == "application/pdf"
        assert MediaFormat.DOCX == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class TestAudioMetadata:
    """Test AudioMetadata model."""
    
    def test_empty_audio_metadata(self):
        """Test creating empty audio metadata."""
        metadata = AudioMetadata()
        assert metadata.duration_seconds is None
        assert metadata.sample_rate is None
        assert metadata.transcription is None
    
    def test_complete_audio_metadata(self):
        """Test creating complete audio metadata."""
        metadata = AudioMetadata(
            duration_seconds=120.5,
            sample_rate=44100,
            channels=2,
            bitrate=320,
            format=MediaFormat.MP3,
            transcription="This is a test transcription",
            transcription_confidence=0.95,
            language="en",
            speaker_count=2,
            audio_fingerprint="abc123"
        )
        
        assert metadata.duration_seconds == 120.5
        assert metadata.sample_rate == 44100
        assert metadata.channels == 2
        assert metadata.bitrate == 320
        assert metadata.format == MediaFormat.MP3
        assert metadata.transcription == "This is a test transcription"
        assert metadata.transcription_confidence == 0.95
        assert metadata.language == "en"
        assert metadata.speaker_count == 2
        assert metadata.audio_fingerprint == "abc123"
    
    def test_audio_metadata_serialization(self):
        """Test JSON serialization of audio metadata."""
        metadata = AudioMetadata(
            duration_seconds=60.0,
            sample_rate=22050,
            transcription="Hello world"
        )
        
        # Test that it can be serialized to dict
        metadata_dict = metadata.dict()
        assert metadata_dict["duration_seconds"] == 60.0
        assert metadata_dict["sample_rate"] == 22050
        assert metadata_dict["transcription"] == "Hello world"
        
        # Test that it can be recreated from dict
        metadata_restored = AudioMetadata(**metadata_dict)
        assert metadata_restored.duration_seconds == metadata.duration_seconds


class TestVideoMetadata:
    """Test VideoMetadata model."""
    
    def test_video_metadata_with_audio(self):
        """Test video metadata including audio metadata."""
        audio_meta = AudioMetadata(
            duration_seconds=300.0,
            transcription="Video narration content"
        )
        
        video_meta = VideoMetadata(
            duration_seconds=300.0,
            width=1920,
            height=1080,
            fps=30.0,
            format=MediaFormat.MP4,
            has_audio=True,
            audio_metadata=audio_meta,
            frame_count=9000
        )
        
        assert video_meta.duration_seconds == 300.0
        assert video_meta.width == 1920
        assert video_meta.height == 1080
        assert video_meta.has_audio is True
        assert video_meta.audio_metadata.transcription == "Video narration content"
        assert video_meta.frame_count == 9000
    
    def test_video_metadata_without_audio(self):
        """Test video metadata for silent video."""
        video_meta = VideoMetadata(
            duration_seconds=60.0,
            width=1280,
            height=720,
            fps=24.0,
            has_audio=False
        )
        
        assert video_meta.has_audio is False
        assert video_meta.audio_metadata is None


class TestImageMetadata:
    """Test ImageMetadata model."""
    
    def test_basic_image_metadata(self):
        """Test basic image metadata."""
        metadata = ImageMetadata(
            width=1920,
            height=1080,
            format=MediaFormat.JPEG,
            color_mode="RGB",
            has_transparency=False
        )
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.format == MediaFormat.JPEG
        assert metadata.color_mode == "RGB"
        assert metadata.has_transparency is False
    
    def test_image_metadata_with_analysis(self):
        """Test image metadata with analysis results."""
        metadata = ImageMetadata(
            width=800,
            height=600,
            dominant_colors=["#FF0000", "#00FF00", "#0000FF"],
            detected_objects=["person", "car", "building"],
            detected_text="Hello World",
            image_hash="abc123def456"
        )
        
        assert len(metadata.dominant_colors) == 3
        assert "person" in metadata.detected_objects
        assert metadata.detected_text == "Hello World"
        assert metadata.image_hash == "abc123def456"
    
    def test_image_metadata_exif(self):
        """Test image metadata with EXIF data."""
        exif_data = {
            "camera": "Canon EOS R5",
            "focal_length": "85mm",
            "aperture": "f/2.8",
            "iso": 400,
            "date_taken": "2023-12-01"
        }
        
        metadata = ImageMetadata(
            width=6000,
            height=4000,
            exif_data=exif_data
        )
        
        assert metadata.exif_data["camera"] == "Canon EOS R5"
        assert metadata.exif_data["iso"] == 400


class TestDocumentMetadata:
    """Test DocumentMetadata model."""
    
    def test_pdf_metadata(self):
        """Test PDF document metadata."""
        metadata = DocumentMetadata(
            page_count=25,
            format=MediaFormat.PDF,
            author="Dr. AI Researcher",
            title="Advanced Machine Learning Techniques",
            subject="Artificial Intelligence",
            creation_date=datetime(2023, 1, 15),
            language="en",
            word_count=8500
        )
        
        assert metadata.page_count == 25
        assert metadata.format == MediaFormat.PDF
        assert metadata.author == "Dr. AI Researcher"
        assert metadata.title == "Advanced Machine Learning Techniques"
        assert metadata.word_count == 8500
    
    def test_docx_metadata(self):
        """Test DOCX document metadata."""
        metadata = DocumentMetadata(
            format=MediaFormat.DOCX,
            word_count=1200,
            has_table_of_contents=True,
            extracted_images_count=5
        )
        
        assert metadata.format == MediaFormat.DOCX
        assert metadata.word_count == 1200
        assert metadata.has_table_of_contents is True
        assert metadata.extracted_images_count == 5


class TestProcessingResult:
    """Test ProcessingResult model."""
    
    def test_successful_processing_result(self):
        """Test successful processing result."""
        result = ProcessingResult(
            success=True,
            content_type=ContentType.AUDIO,
            extracted_text="This is transcribed audio content",
            embeddings=[0.1, 0.2, 0.3, 0.4],
            metadata={"language": "en", "confidence": 0.95},
            processing_time_seconds=45.2,
            confidence_score=0.95
        )
        
        assert result.success is True
        assert result.content_type == ContentType.AUDIO
        assert result.extracted_text == "This is transcribed audio content"
        assert len(result.embeddings) == 4
        assert result.metadata["language"] == "en"
        assert result.processing_time_seconds == 45.2
        assert result.confidence_score == 0.95
        assert result.error_message is None
    
    def test_failed_processing_result(self):
        """Test failed processing result."""
        result = ProcessingResult(
            success=False,
            content_type=ContentType.VIDEO,
            error_message="FFmpeg not found",
            processing_time_seconds=5.0
        )
        
        assert result.success is False
        assert result.content_type == ContentType.VIDEO
        assert result.error_message == "FFmpeg not found"
        assert result.extracted_text is None
        assert result.embeddings is None


class TestMultiModalContent:
    """Test MultiModalContent model."""
    
    def test_text_content(self):
        """Test multi-modal content for text."""
        content = MultiModalContent(
            content_type=ContentType.TEXT,
            primary_text="This is some text content",
            processing_status=ProcessingStatus.COMPLETED
        )
        
        assert content.content_type == ContentType.TEXT
        assert content.primary_text == "This is some text content"
        assert content.processing_status == ProcessingStatus.COMPLETED
        assert content.raw_content is None
    
    def test_audio_content_with_metadata(self):
        """Test multi-modal content for audio with metadata."""
        audio_meta = AudioMetadata(
            duration_seconds=180.0,
            transcription="Audio content transcription"
        )
        
        content = MultiModalContent(
            content_type=ContentType.AUDIO,
            primary_text="Audio content transcription",
            file_path="/uploads/audio123.mp3",
            file_size_bytes=1024000,
            content_hash="sha256hash",
            mime_type="audio/mpeg",
            audio_metadata=audio_meta,
            processing_status=ProcessingStatus.COMPLETED
        )
        
        assert content.content_type == ContentType.AUDIO
        assert content.file_path == "/uploads/audio123.mp3"
        assert content.file_size_bytes == 1024000
        assert content.audio_metadata.duration_seconds == 180.0
        assert content.processing_status == ProcessingStatus.COMPLETED


class TestMultiModalMemory:
    """Test MultiModalMemory model."""
    
    def test_basic_text_memory(self):
        """Test basic text memory creation."""
        memory = MultiModalMemory(
            content_type=ContentType.TEXT,
            primary_content="This is a text memory for testing",
            importance=7.5,
            tags=["testing", "text", "memory"]
        )
        
        assert memory.content_type == ContentType.TEXT
        assert memory.primary_content == "This is a text memory for testing"
        assert memory.importance == 7.5
        assert "testing" in memory.tags
        assert memory.processing_status == ProcessingStatus.PENDING
    
    def test_multimodal_memory_with_embeddings(self):
        """Test memory with multiple embedding types."""
        memory = MultiModalMemory(
            content_type=ContentType.VIDEO,
            primary_content="Educational video about Python programming",
            importance=9.0,
            tags=["education", "python", "programming"],
            text_embedding=[0.1] * 1536,
            image_embedding=[0.2] * 512,
            audio_embedding=[0.3] * 384
        )
        
        assert memory.content_type == ContentType.VIDEO
        assert len(memory.text_embedding) == 1536
        assert len(memory.image_embedding) == 512
        assert len(memory.audio_embedding) == 384
        assert memory.importance == 9.0
    
    def test_memory_validation_primary_content(self):
        """Test validation of primary content."""
        with pytest.raises(ValueError, match="Primary content cannot be empty"):
            MultiModalMemory(
                content_type=ContentType.TEXT,
                primary_content="",
                importance=5.0
            )
        
        with pytest.raises(ValueError, match="Primary content cannot be empty"):
            MultiModalMemory(
                content_type=ContentType.TEXT,
                primary_content="   ",  # Only whitespace
                importance=5.0
            )
    
    def test_memory_validation_importance(self):
        """Test validation of importance score."""
        # Test importance clamping
        memory_low = MultiModalMemory(
            content_type=ContentType.TEXT,
            primary_content="Test content",
            importance=-1.0  # Should be clamped to 0.0
        )
        assert memory_low.importance == 0.0
        
        memory_high = MultiModalMemory(
            content_type=ContentType.TEXT,
            primary_content="Test content",
            importance=15.0  # Should be clamped to 10.0
        )
        assert memory_high.importance == 10.0


class TestMultiModalSearchRequest:
    """Test MultiModalSearchRequest model."""
    
    def test_basic_text_search(self):
        """Test basic text search request."""
        request = MultiModalSearchRequest(
            text_query="machine learning algorithms",
            limit=20,
            threshold=0.8
        )
        
        assert request.text_query == "machine learning algorithms"
        assert request.limit == 20
        assert request.threshold == 0.8
        assert request.content_types is None
        assert request.text_weight == 0.6  # Default value
    
    def test_filtered_search_request(self):
        """Test search request with filters."""
        created_after = datetime.now() - timedelta(days=30)
        
        request = MultiModalSearchRequest(
            text_query="neural networks",
            content_types=[ContentType.AUDIO, ContentType.VIDEO],
            tags=["ai", "education"],
            importance_min=7.0,
            importance_max=10.0,
            created_after=created_after,
            limit=10,
            threshold=0.75,
            text_weight=0.7,
            image_weight=0.2,
            audio_weight=0.1
        )
        
        assert request.text_query == "neural networks"
        assert ContentType.AUDIO in request.content_types
        assert ContentType.VIDEO in request.content_types
        assert request.tags == ["ai", "education"]
        assert request.importance_min == 7.0
        assert request.importance_max == 10.0
        assert request.created_after == created_after
        assert request.text_weight == 0.7
        assert request.image_weight == 0.2
        assert request.audio_weight == 0.1
    
    def test_multimodal_search_with_files(self):
        """Test search request with file-based queries."""
        image_data = b"fake_image_data"
        audio_data = b"fake_audio_data"
        
        request = MultiModalSearchRequest(
            text_query="find similar content",
            image_query=image_data,
            audio_query=audio_data,
            content_types=[ContentType.IMAGE, ContentType.AUDIO]
        )
        
        assert request.image_query == image_data
        assert request.audio_query == audio_data
        assert request.content_types == [ContentType.IMAGE, ContentType.AUDIO]
    
    def test_content_types_deduplication(self):
        """Test that duplicate content types are removed."""
        request = MultiModalSearchRequest(
            text_query="test query",
            content_types=[ContentType.TEXT, ContentType.TEXT, ContentType.AUDIO]
        )
        
        # Should deduplicate content types
        assert len(request.content_types) == 2
        assert ContentType.TEXT in request.content_types
        assert ContentType.AUDIO in request.content_types


class TestMultiModalSearchResult:
    """Test MultiModalSearchResult model."""
    
    def test_search_result_creation(self):
        """Test creating a search result."""
        memory = MultiModalMemory(
            content_type=ContentType.IMAGE,
            primary_content="A beautiful sunset photograph",
            importance=8.5,
            tags=["photography", "nature"]
        )
        
        result = MultiModalSearchResult(
            memory=memory,
            relevance_score=0.92,
            similarity_scores={"text": 0.85, "image": 0.95},
            rank=1,
            matched_content_types=[ContentType.IMAGE],
            explanation="Matched on visual similarity and tags"
        )
        
        assert result.memory.content_type == ContentType.IMAGE
        assert result.relevance_score == 0.92
        assert result.similarity_scores["text"] == 0.85
        assert result.similarity_scores["image"] == 0.95
        assert result.rank == 1
        assert ContentType.IMAGE in result.matched_content_types
        assert result.explanation == "Matched on visual similarity and tags"


class TestContentUploadRequest:
    """Test ContentUploadRequest model."""
    
    def test_basic_upload_request(self):
        """Test basic content upload request."""
        request = ContentUploadRequest(
            content_type=ContentType.AUDIO,
            file_name="lecture.mp3",
            file_size=2048000,
            mime_type="audio/mpeg",
            description="Machine learning lecture",
            tags=["education", "ml"],
            importance=8.0
        )
        
        assert request.content_type == ContentType.AUDIO
        assert request.file_name == "lecture.mp3"
        assert request.file_size == 2048000
        assert request.mime_type == "audio/mpeg"
        assert request.description == "Machine learning lecture"
        assert request.tags == ["education", "ml"]
        assert request.importance == 8.0
        assert request.extract_text is True  # Default
    
    def test_upload_request_processing_options(self):
        """Test upload request with processing options."""
        request = ContentUploadRequest(
            content_type=ContentType.VIDEO,
            description="Training video",
            extract_text=False,
            generate_embeddings=True,
            analyze_content=False
        )
        
        assert request.extract_text is False
        assert request.generate_embeddings is True
        assert request.analyze_content is False


class TestProcessingConfig:
    """Test ProcessingConfig model."""
    
    def test_default_processing_config(self):
        """Test default processing configuration."""
        config = ProcessingConfig()
        
        # Text processing defaults
        assert config.max_text_length == 50000
        assert config.extract_entities is True
        assert config.detect_language is True
        
        # Audio processing defaults
        assert config.transcription_model == "whisper-1"
        assert config.speaker_diarization is False
        
        # Video processing defaults
        assert config.extract_frames is True
        assert config.frame_interval_seconds == 10.0
        assert config.max_frames == 50
        
        # Image processing defaults
        assert config.perform_ocr is True
        assert config.detect_objects is True
        assert config.max_image_dimension == 2048
        
        # Document processing defaults
        assert config.extract_metadata is True
        assert config.chunk_size == 1000
    
    def test_custom_processing_config(self):
        """Test custom processing configuration."""
        config = ProcessingConfig(
            max_text_length=100000,
            transcription_model="whisper-large",
            frame_interval_seconds=5.0,
            max_frames=100,
            perform_ocr=False,
            chunk_size=2000,
            store_original_files=False
        )
        
        assert config.max_text_length == 100000
        assert config.transcription_model == "whisper-large"
        assert config.frame_interval_seconds == 5.0
        assert config.max_frames == 100
        assert config.perform_ocr is False
        assert config.chunk_size == 2000
        assert config.store_original_files is False


class TestModelIntegration:
    """Test integration between different models."""
    
    def test_memory_with_multimodal_content(self):
        """Test memory containing multi-modal content."""
        # Create audio metadata
        audio_meta = AudioMetadata(
            duration_seconds=300.0,
            transcription="This is a lecture about AI"
        )
        
        # Create multi-modal content
        content = MultiModalContent(
            content_type=ContentType.AUDIO,
            primary_text="This is a lecture about AI",
            file_path="/uploads/lecture.mp3",
            audio_metadata=audio_meta,
            processing_status=ProcessingStatus.COMPLETED
        )
        
        # Create memory with the content
        memory = MultiModalMemory(
            content_type=ContentType.AUDIO,
            primary_content="AI lecture recording",
            multimodal_content=content,
            importance=9.0,
            tags=["ai", "lecture", "education"]
        )
        
        assert memory.content_type == ContentType.AUDIO
        assert memory.multimodal_content.audio_metadata.duration_seconds == 300.0
        assert memory.multimodal_content.processing_status == ProcessingStatus.COMPLETED
    
    def test_search_result_with_complex_memory(self):
        """Test search result with complex memory structure."""
        # Create a video memory with multiple metadata types
        video_meta = VideoMetadata(
            duration_seconds=600.0,
            width=1920,
            height=1080,
            has_audio=True
        )
        
        content = MultiModalContent(
            content_type=ContentType.VIDEO,
            primary_text="Python tutorial - advanced concepts",
            video_metadata=video_meta
        )
        
        memory = MultiModalMemory(
            content_type=ContentType.VIDEO,
            primary_content="Python tutorial - advanced concepts",
            multimodal_content=content,
            text_embedding=[0.1] * 1536,
            image_embedding=[0.2] * 512,
            audio_embedding=[0.3] * 384,
            importance=8.5
        )
        
        result = MultiModalSearchResult(
            memory=memory,
            relevance_score=0.88,
            similarity_scores={
                "text": 0.85,
                "image": 0.90,
                "audio": 0.89
            },
            rank=1,
            matched_content_types=[ContentType.VIDEO]
        )
        
        assert result.memory.multimodal_content.video_metadata.width == 1920
        assert len(result.similarity_scores) == 3
        assert all(score > 0.8 for score in result.similarity_scores.values())


# Test fixtures and utilities
@pytest.fixture
def sample_audio_metadata():
    """Sample audio metadata for testing."""
    return AudioMetadata(
        duration_seconds=120.0,
        sample_rate=44100,
        channels=2,
        transcription="Test audio transcription"
    )


@pytest.fixture
def sample_memory():
    """Sample multi-modal memory for testing."""
    return MultiModalMemory(
        content_type=ContentType.TEXT,
        primary_content="Sample memory content for testing",
        importance=7.5,
        tags=["test", "sample"]
    )


@pytest.fixture
def sample_search_request():
    """Sample search request for testing."""
    return MultiModalSearchRequest(
        text_query="test query",
        content_types=[ContentType.TEXT, ContentType.AUDIO],
        limit=10
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
