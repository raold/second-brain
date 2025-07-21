"""
Multi-Modal Memory System for Second Brain v2.6.0
Comprehensive support for text, audio, video, image, and document content.
"""

from .models import (
    ContentType,
    MediaFormat,
    ProcessingStatus,
    AudioMetadata,
    VideoMetadata,
    ImageMetadata,
    DocumentMetadata,
    ProcessingResult,
    MultiModalContent,
    MultiModalMemory,
    MultiModalSearchRequest,
    MultiModalSearchResult,
    ContentUploadRequest,
    ProcessingConfig,
)

# Services will be imported when available
# from .services import (
#     AudioProcessor,
#     VideoProcessor,
#     ImageProcessor,
#     DocumentProcessor,
#     MultiModalProcessor,
# )

__version__ = "2.6.0-dev"
__all__ = [
    # Enums and Types
    "ContentType",
    "MediaFormat", 
    "ProcessingStatus",
    
    # Metadata Models
    "AudioMetadata",
    "VideoMetadata",
    "ImageMetadata",
    "DocumentMetadata",
    
    # Core Models
    "ProcessingResult",
    "MultiModalContent",
    "MultiModalMemory",
    "MultiModalSearchRequest",
    "MultiModalSearchResult",
    "ContentUploadRequest",
    "ProcessingConfig",
    
    # Services (will be added when available)
    # "AudioProcessor",
    # "VideoProcessor", 
    # "ImageProcessor",
    # "DocumentProcessor",
    # "MultiModalProcessor",
]
