"""
Unified Ingestion Engine for Second Brain v2.8.3

This module provides a centralized engine for ingesting various file types,
extracting content, and processing it through the NLP pipeline.
"""

import asyncio
import hashlib
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

import aiofiles

from app.ingestion.core_extraction_pipeline import CoreExtractionPipeline
from app.models.memory import Memory
from app.repositories.memory_repository import MemoryRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileMetadata:
    """Metadata for ingested files"""
    filename: str
    file_type: str
    size: int
    hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "upload"  # upload, google_drive, dropbox, etc.
    source_id: Optional[str] = None  # ID from external source
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Result of file ingestion"""
    success: bool
    file_metadata: FileMetadata
    memories_created: list[Memory] = field(default_factory=list)
    chunks_processed: int = 0
    errors: list[str] = field(default_factory=list)
    processing_time: float = 0.0


class FileParser(ABC):
    """Abstract base class for file parsers"""

    @abstractmethod
    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse file and extract content and metadata"""
        pass

    @abstractmethod
    def supports(self, mime_type: str) -> bool:
        """Check if parser supports given mime type"""
        pass


class TextFileParser(FileParser):
    """Parser for plain text files"""

    SUPPORTED_TYPES = {
        'text/plain',
        'text/markdown',
        'text/x-markdown',
        'application/x-markdown'
    }

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse text file"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        return {
            'content': content,
            'metadata': {
                'format': 'text',
                'encoding': 'utf-8'
            }
        }

    def supports(self, mime_type: str) -> bool:
        return mime_type in self.SUPPORTED_TYPES


class IngestionEngine:
    """
    Unified engine for ingesting various file types into Second Brain
    """

    def __init__(
        self,
        memory_repository: MemoryRepository,
        extraction_pipeline: Optional[CoreExtractionPipeline] = None,
        temp_dir: Optional[Path] = None
    ):
        self.memory_repository = memory_repository
        self.extraction_pipeline = extraction_pipeline or CoreExtractionPipeline()
        
        # Use platform-appropriate temp directory
        if temp_dir:
            self.temp_dir = temp_dir
        else:
            import tempfile
            import os
            # Use environment variable if set (for Docker), otherwise use system temp
            base_temp = os.environ.get('TEMP_DIR', tempfile.gettempdir())
            self.temp_dir = Path(base_temp) / "secondbrain" / "ingestion"
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize parsers
        self.parsers: list[FileParser] = [
            TextFileParser(),
        ]

        # Add optional parsers based on available libraries
        try:
            from app.ingestion.parsers import (
                DocxParser,
                HTMLParser,
                ImageParser,
                MarkdownParser,
                PDFParser,
                SpreadsheetParser,
            )

            # Add parsers with error handling
            for parser_class in [PDFParser, DocxParser, HTMLParser,
                               ImageParser, SpreadsheetParser, MarkdownParser]:
                try:
                    self.parsers.append(parser_class())
                    logger.info(f"Loaded {parser_class.__name__}")
                except ImportError as e:
                    logger.warning(f"Could not load {parser_class.__name__}: {e}")
        except ImportError:
            logger.warning("Additional parsers not available")
        
        # Add multimedia parsers
        try:
            from app.ingestion.multimedia_parsers import (
                AudioParser,
                VideoParser,
                SubtitleParser,
            )
            
            for parser_class in [AudioParser, VideoParser, SubtitleParser]:
                try:
                    self.parsers.append(parser_class())
                    logger.info(f"Loaded {parser_class.__name__}")
                except Exception as e:
                    logger.warning(f"Could not load {parser_class.__name__}: {e}")
        except ImportError:
            logger.warning("Multimedia parsers not available")

        # File size limits (in bytes)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.chunk_size = 4096  # 4KB chunks for processing

    async def ingest_file(
        self,
        file: Union[BinaryIO, Path, str],
        filename: str,
        user_id: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest a file into Second Brain

        Args:
            file: File object, path, or file content
            filename: Original filename
            user_id: User ID for ownership
            tags: Optional tags to apply
            metadata: Optional metadata

        Returns:
            IngestionResult with details of the ingestion
        """
        start_time = asyncio.get_event_loop().time()
        file_path = None

        try:
            # Save file to temp location
            file_path = await self._save_temp_file(file, filename)

            # Get file metadata
            file_metadata = await self._get_file_metadata(file_path, filename)

            # Validate file
            self._validate_file(file_metadata)

            # Detect mime type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Find appropriate parser
            parser = self._get_parser(mime_type)
            if not parser:
                raise ValueError(f"Unsupported file type: {mime_type}")

            # Parse file
            parsed_data = await parser.parse(file_path)

            # Process through NLP pipeline
            memories = await self._process_content(
                content=parsed_data['content'],
                user_id=user_id,
                filename=filename,
                tags=tags,
                metadata={
                    **(metadata or {}),
                    'file_metadata': file_metadata.__dict__,
                    'parsed_metadata': parsed_data.get('metadata', {})
                }
            )

            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time

            return IngestionResult(
                success=True,
                file_metadata=file_metadata,
                memories_created=memories,
                chunks_processed=len(memories),
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Failed to ingest file {filename}: {str(e)}")
            return IngestionResult(
                success=False,
                file_metadata=file_metadata if 'file_metadata' in locals() else FileMetadata(
                    filename=filename,
                    file_type='unknown',
                    size=0,
                    hash=''
                ),
                errors=[str(e)],
                processing_time=asyncio.get_event_loop().time() - start_time
            )
        finally:
            # Cleanup temp file
            if file_path and file_path.exists():
                file_path.unlink()

    async def _save_temp_file(
        self,
        file: Union[BinaryIO, Path, str],
        filename: str
    ) -> Path:
        """Save uploaded file to temporary location"""
        temp_path = self.temp_dir / f"{datetime.utcnow().timestamp()}_{filename}"

        if isinstance(file, Path):
            # Copy existing file
            import shutil
            shutil.copy2(file, temp_path)
        elif isinstance(file, str):
            # Save string content
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(file)
        else:
            # Save binary content
            async with aiofiles.open(temp_path, 'wb') as f:
                while chunk := file.read(self.chunk_size):
                    await f.write(chunk)

        return temp_path

    async def _get_file_metadata(self, file_path: Path, filename: str) -> FileMetadata:
        """Extract file metadata"""
        stat = file_path.stat()

        # Calculate file hash
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(self.chunk_size):
                hash_md5.update(chunk)

        mime_type, _ = mimetypes.guess_type(filename)

        return FileMetadata(
            filename=filename,
            file_type=mime_type or 'application/octet-stream',
            size=stat.st_size,
            hash=hash_md5.hexdigest(),
            created_at=datetime.fromtimestamp(stat.st_ctime)
        )

    def _validate_file(self, file_metadata: FileMetadata):
        """Validate file before processing"""
        if file_metadata.size > self.max_file_size:
            raise ValueError(
                f"File too large: {file_metadata.size} bytes "
                f"(max: {self.max_file_size} bytes)"
            )

        # Add more validation as needed (file type restrictions, etc.)

    def _get_parser(self, mime_type: str) -> Optional[FileParser]:
        """Get appropriate parser for mime type"""
        for parser in self.parsers:
            if parser.supports(mime_type):
                return parser
        return None

    async def _process_content(
        self,
        content: str,
        user_id: str,
        filename: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> list[Memory]:
        """Process content through NLP pipeline and create memories"""
        # Split content into chunks if needed
        chunks = self._split_content(content)
        memories = []

        for i, chunk in enumerate(chunks):
            # Process through NLP pipeline
            extraction_result = await self.extraction_pipeline.process(chunk)

            # Create memory
            memory = Memory(
                user_id=user_id,
                content=chunk,
                tags=tags or [],
                metadata={
                    **(metadata or {}),
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'extraction_result': extraction_result,
                    'source_filename': filename,
                    'chunk_title': f"{filename} - Part {i+1}" if len(chunks) > 1 else filename
                }
            )

            # Save to repository
            saved_memory = await self.memory_repository.create(memory)
            memories.append(saved_memory)

        return memories

    def _split_content(self, content: str, max_chunk_size: int = 4000) -> list[str]:
        """Split content into manageable chunks"""
        if len(content) <= max_chunk_size:
            return [content]

        # Simple splitting by paragraphs
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for paragraph in paragraphs:
            paragraph_size = len(paragraph)

            if current_size + paragraph_size > max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = paragraph_size
            else:
                current_chunk.append(paragraph)
                current_size += paragraph_size

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    async def ingest_google_drive_file(
        self,
        file_id: str,
        user_id: str,
        drive_service: Any,  # Google Drive service instance
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest a file from Google Drive

        Args:
            file_id: Google Drive file ID
            user_id: User ID for ownership
            drive_service: Authenticated Google Drive service
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            IngestionResult
        """
        # To be implemented with Google Drive integration
        raise NotImplementedError("Google Drive integration pending")

    async def batch_ingest(
        self,
        files: list[dict[str, Any]],
        user_id: str,
        tags: Optional[list[str]] = None
    ) -> list[IngestionResult]:
        """
        Ingest multiple files in batch

        Args:
            files: List of file dictionaries with 'file' and 'filename' keys
            user_id: User ID for ownership
            tags: Optional tags to apply to all files

        Returns:
            List of IngestionResults
        """
        tasks = [
            self.ingest_file(
                file=f['file'],
                filename=f['filename'],
                user_id=user_id,
                tags=tags,
                metadata=f.get('metadata')
            )
            for f in files
        ]

        return await asyncio.gather(*tasks)

    def get_supported_types(self) -> list[str]:
        """Get list of supported file types"""
        supported = set()
        for parser in self.parsers:
            if hasattr(parser, 'SUPPORTED_TYPES'):
                supported.update(parser.SUPPORTED_TYPES)
        return sorted(list(supported))
