"""
Unit tests for the ingestion engine
"""

import io
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.ingestion.engine import FileMetadata, IngestionEngine, IngestionResult, TextFileParser
from app.models.memory import Memory


class TestFileMetadata:
    """Test FileMetadata dataclass"""

    def test_file_metadata_creation(self):
        """Test creating FileMetadata instance"""
        metadata = FileMetadata(
            filename="test.pdf", file_type="application/pdf", size=1024, hash="abc123"
        )

        assert metadata.filename == "test.pdf"
        assert metadata.file_type == "application/pdf"
        assert metadata.size == 1024
        assert metadata.hash == "abc123"
        assert metadata.source == "upload"
        assert isinstance(metadata.created_at, datetime)

    def test_file_metadata_with_optional_fields(self):
        """Test FileMetadata with optional fields"""
        metadata = FileMetadata(
            filename="test.docx",
            file_type="application/docx",
            size=2048,
            hash="def456",
            source="google_drive",
            source_id="drive_123",
            metadata={"author": "John Doe"},
        )

        assert metadata.source == "google_drive"
        assert metadata.source_id == "drive_123"
        assert metadata.metadata == {"author": "John Doe"}


class TestIngestionResult:
    """Test IngestionResult dataclass"""

    def test_successful_ingestion_result(self):
        """Test successful ingestion result"""
        file_metadata = FileMetadata(
            filename="test.txt", file_type="text/plain", size=100, hash="xyz789"
        )

        result = IngestionResult(
            success=True,
            file_metadata=file_metadata,
            memories_created=[Mock(spec=Memory)],
            chunks_processed=1,
            processing_time=1.5,
        )

        assert result.success is True
        assert result.file_metadata == file_metadata
        assert len(result.memories_created) == 1
        assert result.chunks_processed == 1
        assert result.processing_time == 1.5
        assert result.errors == []

    def test_failed_ingestion_result(self):
        """Test failed ingestion result"""
        file_metadata = FileMetadata(
            filename="test.pdf", file_type="application/pdf", size=0, hash=""
        )

        result = IngestionResult(
            success=False,
            file_metadata=file_metadata,
            errors=["Failed to parse PDF", "Invalid file format"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert result.memories_created == []
        assert result.chunks_processed == 0


class TestTextFileParser:
    """Test TextFileParser"""

    def test_supports_text_types(self):
        """Test that parser supports text mime types"""
        parser = TextFileParser()

        assert parser.supports("text/plain")
        assert parser.supports("text/markdown")
        assert parser.supports("text/x-markdown")
        assert parser.supports("application/x-markdown")
        assert not parser.supports("application/pdf")

    @pytest.mark.asyncio
    async def test_parse_text_file(self, tmp_path):
        """Test parsing a text file"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "This is a test file.\nWith multiple lines."
        test_file.write_text(test_content, encoding="utf-8")

        parser = TextFileParser()
        result = await parser.parse(test_file)

        assert result["content"] == test_content
        assert result["metadata"]["format"] == "text"
        assert result["metadata"]["encoding"] == "utf-8"


class TestIngestionEngine:
    """Test IngestionEngine"""

    @pytest.fixture
    def mock_memory_repository(self):
        """Create mock memory repository"""
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=Mock(spec=Memory))
        return repo

    @pytest.fixture
    def mock_extraction_pipeline(self):
        """Create mock extraction pipeline"""
        pipeline = AsyncMock()
        pipeline.process = AsyncMock(return_value={"entities": [], "topics": [], "intent": None})
        return pipeline

    @pytest.fixture
    def engine(self, mock_memory_repository, mock_extraction_pipeline, tmp_path):
        """Create IngestionEngine instance"""
        return IngestionEngine(
            memory_repository=mock_memory_repository,
            extraction_pipeline=mock_extraction_pipeline,
            temp_dir=tmp_path / "ingestion",
        )

    @pytest.mark.asyncio
    async def test_ingest_text_file(self, engine, tmp_path):
        """Test ingesting a text file"""
        # Create test file
        test_content = "This is test content for ingestion."
        test_file = tmp_path / "test.txt"
        test_file.write_text(test_content)

        # Mock the memory creation to return a proper Memory object
        mock_memory = Mock(spec=Memory)
        mock_memory.id = "mem-123"
        mock_memory.content = test_content
        engine.memory_repository.create.return_value = mock_memory

        # Ingest file
        result = await engine.ingest_file(
            file=test_file,
            filename="test.txt",
            user_id="user123",
            tags=["test"],
            metadata={"source": "unit_test"},
        )

        assert result.success is True
        assert result.file_metadata.filename == "test.txt"
        assert result.file_metadata.file_type == "text/plain"
        assert result.chunks_processed == 1
        assert len(result.memories_created) == 1
        assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_ingest_file_from_bytes(self, engine):
        """Test ingesting file from bytes"""
        content = b"Binary file content"

        # Create BytesIO object
        file_obj = io.BytesIO(content)

        # Mock to simulate no parser available
        engine._get_parser = Mock(return_value=None)

        result = await engine.ingest_file(file=file_obj, filename="test.bin", user_id="user123")

        # For binary files without parser, should handle gracefully
        assert result.success is False
        assert "Unsupported file type" in result.errors[0]

    @pytest.mark.asyncio
    async def test_ingest_file_size_validation(self, engine):
        """Test file size validation"""
        # Set small max size for testing
        engine.max_file_size = 10  # 10 bytes

        # Create large content
        large_content = "x" * 100

        result = await engine.ingest_file(
            file=large_content, filename="large.txt", user_id="user123"
        )

        assert result.success is False
        assert "File too large" in result.errors[0]

    def test_content_splitting(self, engine):
        """Test content splitting for large files"""
        # Create large content with smaller paragraphs
        paragraphs = []
        for i in range(20):
            # Create paragraphs of varying sizes
            para_content = f"This is paragraph {i}. " * (10 + i % 5)
            paragraphs.append(para_content)

        large_content = "\n\n".join(paragraphs)

        chunks = engine._split_content(large_content, max_chunk_size=500)

        assert len(chunks) > 1

        # Verify all content is preserved
        joined = "\n\n".join(chunks)

        # Check that all original paragraphs are preserved
        for i in range(20):
            assert f"This is paragraph {i}" in joined

        # Verify no content is duplicated or lost
        for para in paragraphs:
            assert para in joined

    def test_get_parser(self, engine):
        """Test getting appropriate parser"""
        # Text parser should be available
        parser = engine._get_parser("text/plain")
        assert parser is not None
        # Check that it's a parser that supports text/plain
        assert parser.supports("text/plain")

        # Markdown parser should be available (it's loaded)
        parser = engine._get_parser("text/markdown")
        assert parser is not None
        assert parser.supports("text/markdown")

        # Unsupported type
        parser = engine._get_parser("application/octet-stream")
        assert parser is None

    @pytest.mark.asyncio
    async def test_batch_ingest(self, engine, tmp_path):
        """Test batch file ingestion"""
        # Create test files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.txt"
            test_file.write_text(f"Content {i}")
            files.append({"file": test_file, "filename": f"test{i}.txt", "metadata": {"index": i}})

        results = await engine.batch_ingest(files=files, user_id="user123", tags=["batch"])

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.chunks_processed == 1 for r in results)

    def test_get_supported_types(self, engine):
        """Test getting supported file types"""
        supported = engine.get_supported_types()

        assert "text/plain" in supported
        assert "text/markdown" in supported
        assert len(supported) >= 4  # At least the text types

    @pytest.mark.asyncio
    async def test_process_content(self, engine):
        """Test content processing through NLP pipeline"""
        memories = await engine._process_content(
            content="Test content",
            user_id="user123",
            filename="test.txt",
            tags=["test"],
            metadata={"key": "value"},
        )

        assert len(memories) == 1
        assert engine.extraction_pipeline.process.called
        assert engine.memory_repository.create.called

    @pytest.mark.asyncio
    async def test_error_handling(self, engine, tmp_path):
        """Test error handling in ingestion"""
        # Create test file
        test_file = tmp_path / "error_test.txt"
        test_file.write_text("Test content")

        # Mock repository to raise error
        engine.memory_repository.create.side_effect = Exception("Database error")

        result = await engine.ingest_file(
            file=test_file, filename="error_test.txt", user_id="user123"
        )

        assert result.success is False
        assert "Database error" in result.errors[0]
        assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_temp_file_cleanup(self, engine, tmp_path):
        """Test that temporary files are cleaned up"""
        test_content = "Temporary file content"

        await engine.ingest_file(file=test_content, filename="temp.txt", user_id="user123")

        # Check that no temp files remain
        temp_files = list(engine.temp_dir.glob("*"))
        assert len(temp_files) == 0


class TestIngestionEngineWithParsers:
    """Test IngestionEngine with additional parsers"""

    @pytest.fixture
    def engine_with_parsers(self, tmp_path):
        """Create engine with mocked parsers"""
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=Mock(spec=Memory))

        pipeline = AsyncMock()
        pipeline.process = AsyncMock(return_value={})

        # Create engine without loading parsers
        engine = IngestionEngine(
            memory_repository=repo, extraction_pipeline=pipeline, temp_dir=tmp_path / "ingestion"
        )

        # Clear existing parsers and add mocked ones
        engine.parsers = []

        # Mock parser instances
        pdf_parser = AsyncMock()
        pdf_parser.supports = Mock(side_effect=lambda mt: mt == "application/pdf")
        pdf_parser.parse = AsyncMock(
            return_value={"content": "PDF content", "metadata": {"pages": 5}}
        )

        docx_parser = AsyncMock()
        docx_parser.supports = Mock(
            side_effect=lambda mt: mt
            in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/docx",
            ]
        )
        docx_parser.parse = AsyncMock(
            return_value={"content": "DOCX content", "metadata": {"paragraphs": 10}}
        )

        # Add parsers for testing
        engine.parsers.extend([pdf_parser, docx_parser])

        return engine

    @pytest.mark.asyncio
    async def test_pdf_ingestion(self, engine_with_parsers, tmp_path):
        """Test PDF file ingestion"""
        # Create dummy PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy pdf content")

        # Mock memory creation
        mock_memory = Mock(spec=Memory)
        mock_memory.id = "mem-pdf-123"
        engine_with_parsers.memory_repository.create.return_value = mock_memory

        result = await engine_with_parsers.ingest_file(
            file=pdf_file, filename="test.pdf", user_id="user123"
        )

        assert result.success is True
        assert result.file_metadata.file_type == "application/pdf"
        assert result.chunks_processed == 1
        # Parser should have been called
        assert any(p.parse.called for p in engine_with_parsers.parsers)


class TestFileValidation:
    """Test file validation functionality"""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create basic engine"""
        repo = AsyncMock()
        return IngestionEngine(memory_repository=repo, temp_dir=tmp_path / "ingestion")

    def test_validate_file_size(self, engine):
        """Test file size validation"""
        # Valid size
        metadata = FileMetadata(filename="test.txt", file_type="text/plain", size=1024, hash="abc")
        engine._validate_file(metadata)  # Should not raise

        # Too large
        metadata.size = engine.max_file_size + 1
        with pytest.raises(ValueError, match="File too large"):
            engine._validate_file(metadata)

    @pytest.mark.asyncio
    async def test_hash_calculation(self, engine, tmp_path):
        """Test file hash calculation"""
        test_file = tmp_path / "test.txt"
        test_content = b"Test content for hashing"
        test_file.write_bytes(test_content)

        metadata = await engine._get_file_metadata(test_file, "test.txt")

        assert metadata.hash is not None
        assert len(metadata.hash) == 32  # MD5 hash length
        assert metadata.size == len(test_content)
