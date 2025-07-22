"""
Comprehensive Route Tests for Second Brain v2.6.0-dev

Tests all API routes including memory, batch, insights, and multimodal endpoints.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models import Memory
from app.batch_processor import BatchStatus


class TestMemoryRoutes:
    """Test memory-related routes"""
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, client: AsyncClient, api_key):
        """Test successful memory creation"""
        memory_data = {
            "content": "Test memory content",
            "importance": 7.5,
            "tags": ["test", "api"],
            "metadata": {"source": "test"}
        }
        
        response = await client.post(
            "/memories",
            json=memory_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == memory_data["content"]
        assert data["importance"] == memory_data["importance"]
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_memory_validation_error(self, client: AsyncClient, api_key):
        """Test memory creation with invalid data"""
        # Missing required field
        memory_data = {
            "importance": 7.5
        }
        
        response = await client.post(
            "/memories",
            json=memory_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_memories(self, client: AsyncClient, api_key):
        """Test listing memories with pagination"""
        response = await client.get(
            "/memories?limit=10&offset=0",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    @pytest.mark.asyncio
    async def test_list_memories_with_filters(self, client: AsyncClient, api_key):
        """Test listing memories with filters"""
        response = await client.get(
            "/memories?tags=test&importance_min=5.0",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify filters are applied
        for memory in data:
            assert memory["importance"] >= 5.0
            if "tags" in memory:
                assert "test" in memory["tags"]
    
    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, client: AsyncClient, api_key):
        """Test retrieving specific memory"""
        # Create a memory first
        create_response = await client.post(
            "/memories",
            json={"content": "Test memory", "importance": 5.0},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        memory_id = create_response.json()["id"]
        
        # Get the memory
        response = await client.get(
            f"/memories/{memory_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id
        assert data["content"] == "Test memory"
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, client: AsyncClient, api_key):
        """Test retrieving non-existent memory"""
        fake_id = str(uuid4())
        
        response = await client.get(
            f"/memories/{fake_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, client: AsyncClient, api_key):
        """Test deleting memory"""
        # Create a memory first
        create_response = await client.post(
            "/memories",
            json={"content": "To be deleted", "importance": 5.0},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        memory_id = create_response.json()["id"]
        
        # Delete the memory
        response = await client.delete(
            f"/memories/{memory_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = await client.get(
            f"/memories/{memory_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_search_memories(self, client: AsyncClient, api_key):
        """Test memory search functionality"""
        search_data = {
            "query": "test search",
            "limit": 10,
            "threshold": 0.7,
            "importance_min": 5.0
        }
        
        response = await client.post(
            "/search",
            json=search_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify search results
        for result in data:
            assert "id" in result
            assert "content" in result
            assert "similarity" in result
            assert result["similarity"] >= 0.7


class TestBatchRoutes:
    """Test batch processing routes"""
    
    @pytest.mark.asyncio
    async def test_batch_process_memories(self, client: AsyncClient, api_key):
        """Test batch processing of memories"""
        batch_request = {
            "name": "Test Batch",
            "memory_ids": [str(uuid4()) for _ in range(5)],
            "operation": "reprocess",
            "batch_size": 10,
            "max_concurrent": 5
        }
        
        with patch("app.routes.batch_routes.BatchProcessor") as mock_processor:
            mock_job = Mock()
            mock_job.id = "job-123"
            mock_job.status = BatchStatus.RUNNING
            mock_processor.return_value.process_memories_batch = AsyncMock(return_value=mock_job)
            
            response = await client.post(
                "/batch/process/memories",
                json=batch_request,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-123"
            assert "status" in data
    
    @pytest.mark.asyncio
    async def test_batch_process_files(self, client: AsyncClient, api_key):
        """Test batch processing of files"""
        # Create mock files
        files = [
            ("files", ("test1.jpg", b"fake image data", "image/jpeg")),
            ("files", ("test2.pdf", b"fake pdf data", "application/pdf"))
        ]
        
        with patch("app.routes.batch_routes.BatchProcessor") as mock_processor:
            mock_job = Mock()
            mock_job.id = "file-job-123"
            mock_job.status = BatchStatus.RUNNING
            mock_processor.return_value.process_files_batch = AsyncMock(return_value=mock_job)
            
            response = await client.post(
                "/batch/process/files",
                files=files,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "file-job-123"
            assert data["files_count"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_import(self, client: AsyncClient, api_key):
        """Test batch import from file"""
        import_data = {
            "name": "Import Test",
            "format": "json",
            "batch_size": 100
        }
        
        # Create mock file
        file_content = json.dumps([
            {"content": "Memory 1", "importance": 5.0},
            {"content": "Memory 2", "importance": 7.0}
        ])
        
        files = [("file", ("import.json", file_content.encode(), "application/json"))]
        
        with patch("app.routes.batch_routes.BatchProcessor") as mock_processor:
            mock_job = Mock()
            mock_job.id = "import-job-123"
            mock_job.status = BatchStatus.RUNNING
            mock_processor.return_value.import_from_export = AsyncMock(return_value=mock_job)
            
            response = await client.post(
                "/batch/import",
                data=import_data,
                files=files,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "import-job-123"
            assert data["format"] == "json"
    
    @pytest.mark.asyncio
    async def test_get_batch_job_status(self, client: AsyncClient, api_key):
        """Test retrieving batch job status"""
        job_id = "test-job-123"
        
        with patch("app.routes.batch_routes.batch_processor") as mock_processor:
            mock_job = Mock()
            mock_job.id = job_id
            mock_job.name = "Test Job"
            mock_job.status = BatchStatus.COMPLETED
            mock_job.progress = {"total": 100, "processed": 100}
            mock_job.created_at = datetime.utcnow()
            mock_job.started_at = datetime.utcnow()
            mock_job.completed_at = datetime.utcnow()
            mock_job.result_summary = {"success": True}
            
            mock_processor.get_job_status = AsyncMock(return_value=mock_job)
            
            response = await client.get(
                f"/batch/jobs/{job_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == job_id
            assert data["status"] == BatchStatus.COMPLETED
            assert data["progress"]["processed"] == 100
    
    @pytest.mark.asyncio
    async def test_cancel_batch_job(self, client: AsyncClient, api_key):
        """Test cancelling batch job"""
        job_id = "cancel-job-123"
        
        with patch("app.routes.batch_routes.batch_processor") as mock_processor:
            mock_processor.cancel_job = AsyncMock(return_value=True)
            
            response = await client.post(
                f"/batch/jobs/{job_id}/cancel",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == job_id
            assert "cancelled" in data["message"]
    
    @pytest.mark.asyncio
    async def test_list_batch_jobs(self, client: AsyncClient, api_key):
        """Test listing batch jobs"""
        with patch("app.routes.batch_routes.batch_processor") as mock_processor:
            mock_jobs = [
                Mock(
                    id=f"job-{i}",
                    name=f"Job {i}",
                    status=BatchStatus.COMPLETED,
                    created_at=datetime.utcnow()
                )
                for i in range(3)
            ]
            
            mock_processor.jobs = {j.id: j for j in mock_jobs}
            
            response = await client.get(
                "/batch/jobs?limit=10",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 3
            assert data["total"] == 3


class TestInsightsRoutes:
    """Test insights and analytics routes"""
    
    @pytest.mark.asyncio
    async def test_generate_insights(self, client: AsyncClient, api_key):
        """Test generating insights"""
        with patch("app.routes.insights.InsightGenerator") as mock_generator:
            mock_insights = {
                "patterns": ["pattern1", "pattern2"],
                "recommendations": ["rec1", "rec2"],
                "summary": "Test insights"
            }
            mock_generator.return_value.generate_insights = AsyncMock(return_value=mock_insights)
            
            response = await client.post(
                "/insights/generate",
                json={"time_range": "last_week"},
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "patterns" in data
            assert len(data["patterns"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_patterns(self, client: AsyncClient, api_key):
        """Test retrieving patterns"""
        with patch("app.routes.insights.PatternDetector") as mock_detector:
            mock_patterns = {
                "temporal": [{"type": "daily", "strength": 0.8}],
                "semantic": [{"cluster": "work", "size": 50}]
            }
            mock_detector.return_value.get_patterns = AsyncMock(return_value=mock_patterns)
            
            response = await client.get(
                "/insights/patterns?type=temporal",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "temporal" in data
            assert len(data["temporal"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_analytics(self, client: AsyncClient, api_key):
        """Test retrieving analytics"""
        with patch("app.routes.insights.AnalyticsEngine") as mock_engine:
            mock_analytics = {
                "total_memories": 1000,
                "avg_importance": 6.5,
                "growth_rate": 0.15,
                "top_tags": ["work", "personal", "ideas"]
            }
            mock_engine.return_value.get_analytics = AsyncMock(return_value=mock_analytics)
            
            response = await client.get(
                "/insights/analytics",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_memories"] == 1000
            assert "top_tags" in data


class TestMultimodalRoutes:
    """Test multimodal content routes"""
    
    @pytest.mark.asyncio
    async def test_upload_image(self, client: AsyncClient, api_key):
        """Test image upload and processing"""
        # Create mock image file
        files = [("file", ("test.jpg", b"fake image data", "image/jpeg"))]
        
        data = {
            "importance": "7.5",
            "tags": "test,image"
        }
        
        with patch("multimodal.api.process_image") as mock_process:
            mock_process.return_value = {
                "text": "Extracted text",
                "objects": ["person", "car"],
                "embedding": [0.1] * 1536
            }
            
            response = await client.post(
                "/multimodal/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert "memory_id" in result
            assert result["file_type"] == "image"
    
    @pytest.mark.asyncio
    async def test_upload_audio(self, client: AsyncClient, api_key):
        """Test audio upload and transcription"""
        files = [("file", ("test.mp3", b"fake audio data", "audio/mpeg"))]
        
        data = {
            "importance": "8.0",
            "tags": "meeting,audio"
        }
        
        with patch("multimodal.api.process_audio") as mock_process:
            mock_process.return_value = {
                "transcription": "This is a test transcription",
                "duration": 120.5,
                "embedding": [0.2] * 1536
            }
            
            response = await client.post(
                "/multimodal/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["file_type"] == "audio"
            assert "transcription" in result.get("metadata", {})
    
    @pytest.mark.asyncio
    async def test_upload_document(self, client: AsyncClient, api_key):
        """Test document upload and extraction"""
        files = [("file", ("test.pdf", b"fake pdf data", "application/pdf"))]
        
        data = {
            "importance": "9.0",
            "tags": "document,report"
        }
        
        with patch("multimodal.api.process_document") as mock_process:
            mock_process.return_value = {
                "text": "Document content",
                "pages": 10,
                "tables": 2,
                "embedding": [0.3] * 1536
            }
            
            response = await client.post(
                "/multimodal/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["file_type"] == "document"


class TestVisualizationRoutes:
    """Test visualization and dashboard routes"""
    
    @pytest.mark.asyncio
    async def test_get_memory_graph(self, client: AsyncClient, api_key):
        """Test memory relationship graph data"""
        response = await client.get(
            "/visualization/graph",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
    
    @pytest.mark.asyncio
    async def test_get_timeline_data(self, client: AsyncClient, api_key):
        """Test timeline visualization data"""
        response = await client.get(
            "/visualization/timeline?days=30",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert isinstance(data["timeline"], list)
    
    @pytest.mark.asyncio
    async def test_get_tag_cloud(self, client: AsyncClient, api_key):
        """Test tag cloud data"""
        response = await client.get(
            "/visualization/tags",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        
        # Verify tag structure
        for tag in data["tags"]:
            assert "name" in tag
            assert "count" in tag
            assert "weight" in tag


class TestHealthAndStatusRoutes:
    """Test health check and status routes"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "database" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_openapi_schema(self, client: AsyncClient):
        """Test OpenAPI schema endpoint"""
        response = await client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data


class TestErrorHandling:
    """Test error handling across routes"""
    
    @pytest.mark.asyncio
    async def test_401_unauthorized(self, client: AsyncClient):
        """Test unauthorized access"""
        # No auth header
        response = await client.get("/memories")
        assert response.status_code == 403
        
        # Invalid token
        response = await client.get(
            "/memories",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_404_not_found(self, client: AsyncClient, api_key):
        """Test not found errors"""
        # Non-existent endpoint
        response = await client.get(
            "/nonexistent",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 404
        
        # Non-existent resource
        fake_id = str(uuid4())
        response = await client.get(
            f"/memories/{fake_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_422_validation_error(self, client: AsyncClient, api_key):
        """Test validation errors"""
        # Invalid data type
        response = await client.post(
            "/memories",
            json={"content": "Test", "importance": "not-a-number"},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 422
        
        # Missing required field
        response = await client.post(
            "/memories",
            json={"importance": 5.0},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_500_internal_error(self, client: AsyncClient, api_key):
        """Test internal server error handling"""
        with patch("app.services.memory_service.MemoryService.create") as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            response = await client.post(
                "/memories",
                json={"content": "Test", "importance": 5.0},
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


class TestPaginationAndFiltering:
    """Test pagination and filtering across routes"""
    
    @pytest.mark.asyncio
    async def test_pagination_parameters(self, client: AsyncClient, api_key):
        """Test pagination parameters work correctly"""
        # Test different page sizes
        for limit in [5, 10, 20]:
            response = await client.get(
                f"/memories?limit={limit}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) <= limit
    
    @pytest.mark.asyncio
    async def test_offset_pagination(self, client: AsyncClient, api_key):
        """Test offset-based pagination"""
        # Get first page
        response1 = await client.get(
            "/memories?limit=5&offset=0",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        page1 = response1.json()
        
        # Get second page
        response2 = await client.get(
            "/memories?limit=5&offset=5",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        page2 = response2.json()
        
        # Verify no overlap
        if page1 and page2:
            page1_ids = [m["id"] for m in page1]
            page2_ids = [m["id"] for m in page2]
            assert not set(page1_ids).intersection(set(page2_ids))
    
    @pytest.mark.asyncio
    async def test_filtering_combinations(self, client: AsyncClient, api_key):
        """Test multiple filter combinations"""
        # Single filter
        response = await client.get(
            "/memories?importance_min=7.0",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200
        
        # Multiple filters
        response = await client.get(
            "/memories?tags=work&importance_min=5.0&limit=10",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200
        
        # Date range filter
        response = await client.get(
            "/memories?date_from=2025-01-01&date_to=2025-12-31",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])