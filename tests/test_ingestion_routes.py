"""
Integration tests for ingestion routes
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.ingestion.engine import FileMetadata, IngestionResult
from app.routes.ingestion_routes import IngestionStatus, ingestion_jobs


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers"""
    return {"Authorization": "Bearer demo-token"}


@pytest.fixture
def mock_current_user():
    """Mock current user"""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user


class TestIngestionRoutes:
    """Test file ingestion routes"""

    def test_get_supported_types(self, client, auth_headers):
        """Test getting supported file types"""
        response = client.get("/api/v1/ingest/supported-types")

        assert response.status_code == 200
        data = response.json()

        assert "supported_types" in data
        assert len(data["supported_types"]) > 0

        # Check structure
        for category in data["supported_types"]:
            assert "category" in category
            assert "types" in category
            assert len(category["types"]) > 0

            for file_type in category["types"]:
                assert "extension" in file_type
                assert "mime_type" in file_type

        assert data["max_file_size_mb"] == 100
        assert "notes" in data

    @patch("app.routes.ingestion_routes.get_current_user")
    @patch("app.routes.ingestion_routes.process_file_ingestion")
    def test_upload_single_file(
        self, mock_process, mock_user, client, auth_headers, mock_current_user
    ):
        """Test single file upload"""
        mock_user.return_value = mock_current_user

        # Create test file
        file_content = b"Test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {"tags": "test,upload", "metadata": json.dumps({"source": "test"})}

        response = client.post(
            "/api/v1/ingest/upload", files=files, data=data, headers=auth_headers
        )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert "job_id" in result
        assert result["message"] == "File 'test.txt' queued for processing"

        # Check job was created
        assert result["job_id"] in ingestion_jobs
        job = ingestion_jobs[result["job_id"]]
        assert job.status == "pending"
        assert job.filename == "test.txt"

    @patch("app.routes.ingestion_routes.get_current_user")
    @patch("app.routes.ingestion_routes.process_batch_ingestion")
    def test_upload_batch_files(
        self, mock_process, mock_user, client, auth_headers, mock_current_user
    ):
        """Test batch file upload"""
        mock_user.return_value = mock_current_user

        # Create test files
        files = [
            ("files", ("test1.txt", b"Content 1", "text/plain")),
            ("files", ("test2.pdf", b"Content 2", "application/pdf")),
            (
                "files",
                (
                    "test3.docx",
                    b"Content 3",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ]

        data = {"request": json.dumps({"tags": ["batch", "test"], "metadata": {"batch": True}})}

        response = client.post(
            "/api/v1/ingest/upload/batch", files=files, data=data, headers=auth_headers
        )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert "job_id" in result
        assert result["message"] == "Batch of 3 files queued for processing"

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_upload_without_file(self, mock_user, client, auth_headers, mock_current_user):
        """Test upload without file"""
        mock_user.return_value = mock_current_user

        response = client.post("/api/v1/ingest/upload", data={"tags": "test"}, headers=auth_headers)

        assert response.status_code == 422  # Validation error

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_get_job_status(self, mock_user, client, auth_headers, mock_current_user):
        """Test getting job status"""
        mock_user.return_value = mock_current_user

        # Create test job
        job_id = f"{mock_current_user.id}_123456"
        test_job = IngestionStatus(
            job_id=job_id,
            status="completed",
            filename="test.pdf",
            file_type="application/pdf",
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result={
                "success": True,
                "memories_created": 5,
                "chunks_processed": 5,
                "processing_time": 2.5,
                "file_hash": "abc123",
            },
        )
        ingestion_jobs[job_id] = test_job

        response = client.get(f"/api/v1/ingest/status/{job_id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()

        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        assert result["filename"] == "test.pdf"
        assert result["result"]["memories_created"] == 5

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_get_job_status_unauthorized(self, mock_user, client, auth_headers, mock_current_user):
        """Test getting job status for another user's job"""
        mock_user.return_value = mock_current_user

        # Create job for different user
        job_id = "other_user_123456"
        test_job = IngestionStatus(
            job_id=job_id,
            status="processing",
            filename="secret.pdf",
            file_type="application/pdf",
            created_at=datetime.utcnow(),
        )
        ingestion_jobs[job_id] = test_job

        response = client.get(f"/api/v1/ingest/status/{job_id}", headers=auth_headers)

        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_list_ingestion_jobs(self, mock_user, client, auth_headers, mock_current_user):
        """Test listing user's ingestion jobs"""
        mock_user.return_value = mock_current_user

        # Clear existing jobs
        ingestion_jobs.clear()

        # Create test jobs
        for i in range(3):
            job_id = f"{mock_current_user.id}_{123456 + i}"
            ingestion_jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status="completed",
                filename=f"test{i}.txt",
                file_type="text/plain",
                created_at=datetime.utcnow(),
            )

        # Add job for different user
        ingestion_jobs["other_user_999"] = IngestionStatus(
            job_id="other_user_999",
            status="pending",
            filename="other.txt",
            file_type="text/plain",
            created_at=datetime.utcnow(),
        )

        response = client.get("/api/v1/ingest/jobs", headers=auth_headers)

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 3  # Only user's jobs
        assert all(job["filename"].startswith("test") for job in jobs)


class TestIngestionProcessing:
    """Test ingestion processing functions"""

    @pytest.mark.asyncio
    @patch("app.routes.ingestion_routes.IngestionEngine")
    @patch("app.routes.ingestion_routes.MemoryRepository")
    @patch("app.routes.ingestion_routes.ServiceFactory")
    async def test_process_file_ingestion_success(self, mock_factory, mock_repo, mock_engine):
        """Test successful file processing"""
        from app.routes.ingestion_routes import process_file_ingestion

        # Setup mocks
        mock_ingestion_engine = AsyncMock()
        mock_result = IngestionResult(
            success=True,
            file_metadata=FileMetadata(
                filename="test.pdf", file_type="application/pdf", size=1024, hash="abc123"
            ),
            memories_created=[Mock(), Mock()],
            chunks_processed=2,
            processing_time=1.5,
        )
        mock_ingestion_engine.ingest_file.return_value = mock_result
        mock_engine.return_value = mock_ingestion_engine

        # Mock file
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"file content")

        # Create job
        job_id = "test_job_123"
        ingestion_jobs[job_id] = IngestionStatus(
            job_id=job_id,
            status="pending",
            filename="test.pdf",
            file_type="application/pdf",
            created_at=datetime.utcnow(),
        )

        # Process file
        await process_file_ingestion(
            job_id=job_id,
            file=mock_file,
            filename="test.pdf",
            user_id="user123",
            tags=["test"],
            metadata={"key": "value"},
            db=Mock(),
        )

        # Check job was updated
        job = ingestion_jobs[job_id]
        assert job.status == "completed"
        assert job.result["success"] is True
        assert job.result["memories_created"] == 2
        assert job.result["file_hash"] == "abc123"

    @pytest.mark.asyncio
    @patch("app.routes.ingestion_routes.IngestionEngine")
    async def test_process_file_ingestion_failure(self, mock_engine):
        """Test failed file processing"""
        from app.routes.ingestion_routes import process_file_ingestion

        # Setup mock to fail
        mock_engine.side_effect = Exception("Processing failed")

        # Create job
        job_id = "test_job_456"
        ingestion_jobs[job_id] = IngestionStatus(
            job_id=job_id,
            status="pending",
            filename="bad.pdf",
            file_type="application/pdf",
            created_at=datetime.utcnow(),
        )

        # Mock file
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"bad content")

        # Process file
        await process_file_ingestion(
            job_id=job_id,
            file=mock_file,
            filename="bad.pdf",
            user_id="user123",
            tags=[],
            metadata={},
            db=Mock(),
        )

        # Check job was marked as failed
        job = ingestion_jobs[job_id]
        assert job.status == "failed"
        assert job.error == "Processing failed"
        assert job.completed_at is not None

    @pytest.mark.asyncio
    @patch("app.routes.ingestion_routes.IngestionEngine")
    async def test_process_batch_ingestion(self, mock_engine):
        """Test batch file processing"""
        from app.routes.ingestion_routes import process_batch_ingestion

        # Setup mocks
        mock_ingestion_engine = AsyncMock()

        # Mock results for each file
        results = []
        for i in range(3):
            result = IngestionResult(
                success=True if i < 2 else False,
                file_metadata=FileMetadata(
                    filename=f"file{i}.txt", file_type="text/plain", size=100, hash=f"hash{i}"
                ),
                memories_created=[Mock()] if i < 2 else [],
                chunks_processed=1 if i < 2 else 0,
                errors=[] if i < 2 else ["Failed to process"],
            )
            results.append(result)

        mock_ingestion_engine.ingest_file.side_effect = results
        mock_engine.return_value = mock_ingestion_engine

        # Create job
        job_id = "batch_job_789"
        ingestion_jobs[job_id] = IngestionStatus(
            job_id=job_id,
            status="pending",
            filename="3 files",
            file_type="batch",
            created_at=datetime.utcnow(),
        )

        # Mock files
        mock_files = []
        for i in range(3):
            mock_file = AsyncMock()
            mock_file.read = AsyncMock(return_value=f"content{i}".encode())
            mock_file.filename = f"file{i}.txt"
            mock_files.append(mock_file)

        # Process batch
        await process_batch_ingestion(
            job_id=job_id,
            files=mock_files,
            user_id="user123",
            tags=["batch"],
            metadata={},
            db=Mock(),
        )

        # Check job results
        job = ingestion_jobs[job_id]
        assert job.status == "completed"
        assert job.result["total_files"] == 3
        assert job.result["successful_files"] == 2
        assert job.result["failed_files"] == 1
        assert job.result["total_memories_created"] == 2
        assert len(job.result["failures"]) == 1


class TestIngestionValidation:
    """Test input validation for ingestion routes"""

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_upload_empty_filename(self, mock_user, client, auth_headers, mock_current_user):
        """Test upload with empty filename"""
        mock_user.return_value = mock_current_user

        # Create file with empty filename
        files = {"file": ("", b"content", "text/plain")}

        response = client.post("/api/v1/ingest/upload", files=files, headers=auth_headers)

        assert response.status_code == 400
        assert response.json()["detail"] == "No filename provided"

    @patch("app.routes.ingestion_routes.get_current_user")
    def test_batch_upload_no_files(self, mock_user, client, auth_headers, mock_current_user):
        """Test batch upload without files"""
        mock_user.return_value = mock_current_user

        data = {"request": json.dumps({"tags": ["test"]})}

        response = client.post("/api/v1/ingest/upload/batch", data=data, headers=auth_headers)

        assert response.status_code == 422  # No files provided

    def test_invalid_job_id(self, client, auth_headers):
        """Test getting status for non-existent job"""
        response = client.get("/api/v1/ingest/status/nonexistent_job", headers=auth_headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"
