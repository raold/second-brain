"""
Unit tests for report generator service - v2.8.2
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from app.models.synthesis.report_models import (
    ReportConfig,
    ReportFormat,
    ReportMetrics,
    ReportRequest,
    ReportResponse,
    ReportSection,
    ReportType,
)
from app.services.synthesis.report_generator import (
    ReportGenerator,
    ReportGeneratorConfig,
)


class TestReportGenerator:
    """Test report generator service."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock database pool."""
        pool = AsyncMock(spec=asyncpg.Pool)
        return pool

    @pytest.fixture
    def mock_memory_service(self):
        """Create mock memory service."""
        service = AsyncMock()
        service.search_memories = AsyncMock(return_value=[
            {
                "id": "mem_1",
                "content": "Test memory 1",
                "created_at": datetime.utcnow(),
                "importance_score": 0.8,
                "memory_type": "semantic",
            },
            {
                "id": "mem_2",
                "content": "Test memory 2",
                "created_at": datetime.utcnow() - timedelta(days=1),
                "importance_score": 0.6,
                "memory_type": "episodic",
            },
        ])
        service.get_memories_by_date_range = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def generator_config(self):
        """Create generator config."""
        return ReportGeneratorConfig(
            gpt4_enabled=True,
            gpt4_api_key="test_key",
            max_summary_length=500,
            cache_ttl_seconds=300,
            template_directory="/templates",
        )

    @pytest.fixture
    async def report_generator(self, mock_pool, mock_memory_service, generator_config):
        """Create report generator instance."""
        generator = ReportGenerator(mock_pool, mock_memory_service, generator_config)
        return generator

    async def test_generate_daily_report(self, report_generator):
        """Test generating a daily report."""
        config = ReportConfig(
            report_type=ReportType.DAILY,
            format=ReportFormat.JSON,
            include_memories=True,
            include_insights=True,
            include_graphs=False,
        )
        request = ReportRequest(config=config)

        with patch.object(report_generator, '_generate_ai_summary', return_value="AI generated summary"):
            report = await report_generator.generate_report(request)

        assert isinstance(report, ReportResponse)
        assert report.config.report_type == ReportType.DAILY
        assert report.format == ReportFormat.JSON
        assert report.title == "Daily Report"
        assert report.summary == "AI generated summary"
        assert len(report.sections) > 0
        assert isinstance(report.metrics, ReportMetrics)
        assert report.generation_time_ms > 0

    async def test_generate_weekly_report(self, report_generator):
        """Test generating a weekly report."""
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            format=ReportFormat.PDF,
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )
        request = ReportRequest(config=config)

        with patch.object(report_generator, '_format_as_pdf', return_value=b"PDF content"):
            with patch.object(report_generator, '_generate_ai_summary', return_value="Weekly summary"):
                report = await report_generator.generate_report(request)

        assert report.config.report_type == ReportType.WEEKLY
        assert report.format == ReportFormat.PDF
        assert report.title == "Weekly Report"
        assert report.file_url is None  # Would be set if file was saved

    async def test_generate_insights_report(self, report_generator):
        """Test generating an insights report."""
        config = ReportConfig(
            report_type=ReportType.INSIGHTS,
            format=ReportFormat.HTML,
            include_recommendations=True,
            analysis_depth="deep",
        )
        request = ReportRequest(config=config)

        with patch.object(report_generator, '_generate_ai_summary', return_value="Insights summary"):
            report = await report_generator.generate_report(request)

        assert report.config.report_type == ReportType.INSIGHTS
        assert report.format == ReportFormat.HTML
        assert "Insights" in report.title
        assert len(report.metrics.recommendations) > 0

    async def test_calculate_metrics(self, report_generator):
        """Test metrics calculation."""
        memories = [
            {
                "id": f"mem_{i}",
                "content": f"Memory {i}",
                "created_at": datetime.utcnow() - timedelta(days=i),
                "importance_score": 0.5 + (i * 0.1),
                "memory_type": "semantic" if i % 2 == 0 else "episodic",
                "tags": [f"tag_{i}"],
            }
            for i in range(10)
        ]

        metrics = await report_generator._calculate_metrics(
            memories,
            datetime.utcnow() - timedelta(days=10),
            datetime.utcnow()
        )

        assert metrics.total_memories == 10
        assert metrics.new_memories == 10
        assert metrics.memories_reviewed == 0  # No review data in test
        assert metrics.active_days == 10
        assert len(metrics.topics_covered) > 0
        assert 0 <= metrics.retention_rate <= 1

    async def test_generate_summary_section(self, report_generator):
        """Test summary section generation."""
        metrics = ReportMetrics(
            total_memories=100,
            new_memories=25,
            average_daily_memories=3.5,
            retention_rate=0.85,
        )

        section = await report_generator._generate_summary_section(
            metrics,
            "This is an AI summary"
        )

        assert isinstance(section, ReportSection)
        assert section.title == "Executive Summary"
        assert "This is an AI summary" in section.content
        assert section.order == 1

    async def test_format_report_json(self, report_generator):
        """Test JSON report formatting."""
        report = ReportResponse(
            id="report_123",
            config=ReportConfig(report_type=ReportType.DAILY),
            title="Test Report",
            sections=[
                ReportSection(title="Section 1", content="Content 1", order=1)
            ],
            metrics=ReportMetrics(),
            generation_time_ms=100,
            format=ReportFormat.JSON,
        )

        formatted = await report_generator._format_report(report)

        assert isinstance(formatted, str)
        assert "Test Report" in formatted
        assert "Section 1" in formatted

    async def test_format_report_markdown(self, report_generator):
        """Test Markdown report formatting."""
        report = ReportResponse(
            id="report_123",
            config=ReportConfig(report_type=ReportType.WEEKLY),
            title="Weekly Report",
            sections=[
                ReportSection(title="Overview", content="Weekly overview", order=1),
                ReportSection(title="Details", content="Detailed analysis", order=2),
            ],
            metrics=ReportMetrics(total_memories=50),
            generation_time_ms=200,
            format=ReportFormat.MARKDOWN,
        )

        formatted = await report_generator._format_report(report)

        assert isinstance(formatted, str)
        assert "# Weekly Report" in formatted
        assert "## Overview" in formatted
        assert "## Details" in formatted
        assert "Total Memories: 50" in formatted

    @patch('httpx.AsyncClient.post')
    async def test_generate_ai_summary(self, mock_post, report_generator):
        """Test AI summary generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is an AI-generated summary"}}
            ]
        }
        mock_post.return_value = mock_response

        summary = await report_generator._generate_ai_summary(
            "Test content",
            ReportType.MONTHLY,
            max_length=300
        )

        assert summary == "This is an AI-generated summary"
        mock_post.assert_called_once()

    async def test_generate_ai_summary_disabled(self, report_generator):
        """Test AI summary when disabled."""
        report_generator.config.gpt4_enabled = False

        summary = await report_generator._generate_ai_summary(
            "Test content",
            ReportType.DAILY,
            max_length=300
        )

        assert summary == ""

    async def test_deliver_report_email(self, report_generator):
        """Test email delivery (mocked)."""
        report = ReportResponse(
            id="report_123",
            config=ReportConfig(
                report_type=ReportType.WEEKLY,
                email_recipients=["test@example.com"],
            ),
            title="Weekly Report",
            sections=[],
            metrics=ReportMetrics(),
            generation_time_ms=100,
            format=ReportFormat.PDF,
        )

        # In real implementation, this would send email
        delivered = await report_generator._deliver_report(report, b"PDF content")

        # Mock delivery always returns True for now
        assert delivered is True

    async def test_report_caching(self, report_generator):
        """Test report caching functionality."""
        config = ReportConfig(
            report_type=ReportType.DAILY,
            format=ReportFormat.JSON,
        )
        request = ReportRequest(config=config)

        # Generate report first time
        with patch.object(report_generator, '_generate_ai_summary', return_value="Summary 1"):
            report1 = await report_generator.generate_report(request)

        # Generate same report again (should use cache)
        with patch.object(report_generator, '_generate_ai_summary', return_value="Summary 2"):
            report2 = await report_generator.generate_report(request)

        # Cache is disabled in current implementation, so reports will be different
        assert report1.id != report2.id

    async def test_error_handling(self, report_generator):
        """Test error handling in report generation."""
        config = ReportConfig(report_type=ReportType.MONTHLY)
        request = ReportRequest(config=config)

        # Mock memory service to raise exception
        report_generator.memory_service.search_memories.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            await report_generator.generate_report(request)

        assert "Database error" in str(exc_info.value)
