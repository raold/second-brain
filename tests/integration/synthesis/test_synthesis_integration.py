"""
Integration tests for synthesis features - v2.8.2

Tests the complete synthesis system including report generation,
spaced repetition, and WebSocket real-time updates.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.models.synthesis.repetition_models import (
    BulkReviewRequest,
    RepetitionAlgorithm,
)
from app.models.synthesis.report_models import (
    ReportConfig,
    ReportFormat,
    ReportType,
)


@pytest.mark.integration
class TestSynthesisIntegration:
    """Integration tests for synthesis features."""

    @pytest.fixture
    async def test_client(self):
        """Create test client with mocked dependencies."""
        from app.app import app

        # Mock database and services
        with patch('app.shared.get_db_instance') as mock_db:
            mock_db.return_value = AsyncMock()

            # Use TestClient for synchronous tests
            with TestClient(app) as client:
                yield client

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        from app.app import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_complete_report_generation_flow(self, async_client):
        """Test complete report generation workflow."""
        # 1. Generate a daily report
        report_config = ReportConfig(
            report_type=ReportType.DAILY,
            format=ReportFormat.JSON,
            include_memories=True,
            include_insights=True,
            use_gpt4_summary=False,  # Disable for testing
        )

        response = await async_client.post(
            "/api/v1/synthesis/reports/generate",
            json={"config": report_config.dict()},
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        report = response.json()
        assert report["config"]["report_type"] == "daily"
        assert report["format"] == "json"
        assert "sections" in report
        assert "metrics" in report

        # 2. List reports
        response = await async_client.get(
            "/api/v1/synthesis/reports",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        reports = response.json()
        assert isinstance(reports, list)

    async def test_complete_spaced_repetition_flow(self, async_client):
        """Test complete spaced repetition workflow."""
        # 1. Schedule a memory for review
        response = await async_client.post(
            "/api/v1/synthesis/repetition/schedule",
            params={
                "memory_id": "mem_test_123",
                "algorithm": "sm2"
            },
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        schedule = response.json()
        assert schedule["memory_id"] == "mem_test_123"
        assert schedule["algorithm"] == "sm2"
        assert "scheduled_date" in schedule

        # 2. Bulk schedule multiple memories
        bulk_request = BulkReviewRequest(
            memory_ids=["mem_1", "mem_2", "mem_3"],
            algorithm=RepetitionAlgorithm.ANKI
        )

        response = await async_client.post(
            "/api/v1/synthesis/repetition/bulk-schedule",
            json=bulk_request.dict(),
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        schedules = response.json()
        assert len(schedules) == 3

        # 3. Get due reviews
        response = await async_client.get(
            "/api/v1/synthesis/repetition/due",
            params={"limit": 10},
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        due_reviews = response.json()
        assert isinstance(due_reviews, list)

        # 4. Start a review session
        response = await async_client.post(
            "/api/v1/synthesis/repetition/sessions/start",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        session = response.json()
        assert "id" in session
        session_id = session["id"]

        # 5. Record a review
        response = await async_client.post(
            "/api/v1/synthesis/repetition/review/mem_test_123",
            params={
                "session_id": session_id,
                "difficulty": "good",
                "time_taken_seconds": 10,
                "confidence_level": 0.8
            },
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "next_review" in result

        # 6. End the session
        response = await async_client.post(
            f"/api/v1/synthesis/repetition/sessions/{session_id}/end",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        ended_session = response.json()
        assert ended_session["id"] == session_id
        assert "ended_at" in ended_session

        # 7. Get learning statistics
        response = await async_client.get(
            "/api/v1/synthesis/repetition/statistics",
            params={"period": "week"},
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        stats = response.json()
        assert "total_memories" in stats
        assert "average_retention_rate" in stats

    async def test_websocket_integration(self, test_client):
        """Test WebSocket integration."""
        # Note: FastAPI TestClient doesn't support WebSocket testing well
        # This is a simplified test showing the structure

        # 1. Test WebSocket connection endpoint exists
        response = test_client.get("/api/v1/synthesis/websocket/metrics",
                                  headers={"X-API-Key": "test_key"})

        assert response.status_code == 200
        metrics = response.json()
        assert "active_connections" in metrics
        assert "total_connections" in metrics

    async def test_synthesis_status_endpoint(self, async_client):
        """Test synthesis status endpoint."""
        response = await async_client.get(
            "/api/v1/synthesis/synthesis/status",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        status = response.json()

        assert "report_generator" in status
        assert status["report_generator"]["status"] == "operational"
        assert status["report_generator"]["version"] == "2.8.2"

        assert "repetition_scheduler" in status
        assert status["repetition_scheduler"]["status"] == "operational"
        assert "sm2" in status["repetition_scheduler"]["algorithms"]

        assert "websocket_service" in status
        assert status["websocket_service"]["status"] == "operational"

    async def test_report_scheduling(self, async_client):
        """Test report scheduling functionality."""
        # Create a report schedule
        schedule_config = {
            "name": "Weekly Summary",
            "config": {
                "report_type": "weekly",
                "format": "pdf",
                "email_recipients": ["test@example.com"]
            },
            "enabled": True,
            "cron_expression": "0 9 * * MON",
            "timezone": "UTC",
            "auto_deliver": True,
            "delivery_format": "pdf"
        }

        response = await async_client.post(
            "/api/v1/synthesis/reports/schedule",
            json=schedule_config,
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        schedule = response.json()
        assert schedule["name"] == "Weekly Summary"
        assert schedule["cron_expression"] == "0 9 * * MON"

        # List schedules
        response = await async_client.get(
            "/api/v1/synthesis/reports/schedules",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        schedules = response.json()
        assert isinstance(schedules, list)

    async def test_report_templates(self, async_client):
        """Test report template management."""
        # Create a template
        template = {
            "name": "Monthly Analysis",
            "description": "Comprehensive monthly analysis template",
            "report_type": "monthly",
            "sections": ["summary", "memories", "insights", "recommendations"],
            "default_format": "pdf",
            "include_summary": True
        }

        response = await async_client.post(
            "/api/v1/synthesis/reports/templates",
            json=template,
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        created_template = response.json()
        assert created_template["name"] == "Monthly Analysis"
        assert "id" in created_template

        # List templates
        response = await async_client.get(
            "/api/v1/synthesis/reports/templates",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)

    async def test_error_handling(self, async_client):
        """Test error handling in synthesis endpoints."""
        # Test invalid report type
        invalid_config = {
            "config": {
                "report_type": "invalid_type",
                "format": "json"
            }
        }

        response = await async_client.post(
            "/api/v1/synthesis/reports/generate",
            json=invalid_config,
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 422  # Validation error

        # Test missing authentication
        response = await async_client.get("/api/v1/synthesis/reports")
        assert response.status_code == 403  # Forbidden

        # Test non-existent report
        response = await async_client.get(
            "/api/v1/synthesis/reports/non_existent_id",
            headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 404
        error = response.json()
        assert "Report not found" in error["detail"]

    async def test_concurrent_operations(self, async_client):
        """Test concurrent synthesis operations."""
        # Generate multiple reports concurrently
        tasks = []
        for i in range(3):
            config = ReportConfig(
                report_type=ReportType.DAILY,
                format=ReportFormat.JSON,
                relative_timeframe=f"last_{i+1}_days"
            )

            task = async_client.post(
                "/api/v1/synthesis/reports/generate",
                json={"config": config.dict()},
                headers={"X-API-Key": "test_key"}
            )
            tasks.append(task)

        # Wait for all reports to complete
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for response in responses:
            assert response.status_code == 200
            report = response.json()
            assert "id" in report
            assert report["format"] == "json"
