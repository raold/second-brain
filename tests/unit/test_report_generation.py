"""
Comprehensive tests for report generation system
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.synthesis.report_models import (
    GeneratedReport,
    KnowledgeMapReport,
    LearningPathReport,
    ProgressReport,
    ReportFormat,
    ReportRequest,
    ReportSchedule,
    ReportTemplate,
    ReportType,
)
from app.services.synthesis.report_generator import ReportGenerator


@pytest.fixture
async def report_generator():
    """Create a report generator instance with mocked database."""
    mock_db = AsyncMock()
    generator = ReportGenerator(mock_db)
    return generator, mock_db


class TestReportGeneration:
    """Test suite for report generation functionality."""

    async def test_generate_daily_report(self, report_generator):
        """Test generating a daily activity report."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Today's memories
            [
                {"id": str(uuid4()), "title": "Memory 1", "content": "Content 1", "created_at": datetime.utcnow()},
                {"id": str(uuid4()), "title": "Memory 2", "content": "Content 2", "created_at": datetime.utcnow()}
            ],
            # Today's connections
            [{"count": 5}],
            # Today's reviews
            [
                {"memory_id": str(uuid4()), "difficulty": "good", "completed_at": datetime.utcnow()},
                {"memory_id": str(uuid4()), "difficulty": "easy", "completed_at": datetime.utcnow()}
            ]
        ]

        request = ReportRequest(
            report_type=ReportType.DAILY,
            format=ReportFormat.JSON,
            include_visualizations=False
        )

        with patch.object(generator, '_generate_ai_summary', return_value="Daily summary"):
            report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.DAILY
        assert report.title == "Daily Activity Report"
        assert report.executive_summary == "Daily summary"
        assert len(report.sections) > 0
        assert report.format == ReportFormat.JSON

    async def test_generate_weekly_report(self, report_generator):
        """Test generating a weekly progress report."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Week's memories
            [{"id": str(uuid4()), "title": f"Memory {i}", "created_at": datetime.utcnow() - timedelta(days=i)}
             for i in range(7)],
            # Week's metrics
            [{"metric": "memories_created", "value": 7, "date": datetime.utcnow()}],
            # Top topics
            [{"topic": "AI", "count": 5}, {"topic": "ML", "count": 3}]
        ]

        request = ReportRequest(
            report_type=ReportType.WEEKLY,
            format=ReportFormat.HTML,
            include_visualizations=True,
            include_recommendations=True
        )

        with patch.object(generator, '_generate_ai_summary', return_value="Weekly summary"):
            with patch.object(generator, '_generate_visualizations', return_value={"chart": "data"}):
                report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.WEEKLY
        assert report.executive_summary == "Weekly summary"
        assert report.visualizations == {"chart": "data"}
        assert any(s["type"] == "recommendations" for s in report.sections)

    async def test_generate_insights_report(self, report_generator):
        """Test generating an AI-powered insights report."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Memory patterns
            [{"pattern": "Learning AI", "frequency": 10}],
            # Knowledge clusters
            [{"cluster": "Machine Learning", "size": 25}],
            # User behaviors
            [{"behavior": "morning_learner", "confidence": 0.85}]
        ]

        request = ReportRequest(
            report_type=ReportType.INSIGHTS,
            format=ReportFormat.PDF
        )

        # Mock OpenAI call
        with patch('openai.ChatCompletion.create') as mock_openai:
            mock_openai.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "patterns": ["Pattern 1", "Pattern 2"],
                    "emerging_topics": ["Topic 1"],
                    "knowledge_gaps": ["Gap 1"],
                    "recommendations": ["Recommendation 1"]
                })))]
            )

            report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.INSIGHTS
        assert isinstance(report.metadata.get("insights_data"), dict)
        assert report.format == ReportFormat.PDF

    async def test_generate_progress_report(self, report_generator):
        """Test generating a learning progress report."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Learning metrics
            [{"metric": "retention_rate", "value": 0.85}],
            # Achievements
            [{"achievement": "100 day streak", "date": datetime.utcnow()}],
            # Progress over time
            [{"date": datetime.utcnow() - timedelta(days=i), "score": 70 + i}
             for i in range(30)]
        ]

        request = ReportRequest(
            report_type=ReportType.PROGRESS,
            format=ReportFormat.MARKDOWN,
            period_days=30
        )

        with patch.object(generator, '_generate_ai_summary', return_value="Progress summary"):
            report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.PROGRESS
        assert isinstance(report, ProgressReport)
        assert report.metrics.get("retention_rate") == 0.85
        assert len(report.achievements) == 1

    async def test_generate_knowledge_map(self, report_generator):
        """Test generating a knowledge map report."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Nodes (memories)
            [{"id": str(uuid4()), "title": f"Node {i}"} for i in range(5)],
            # Edges (connections)
            [{"source": str(uuid4()), "target": str(uuid4()), "weight": 0.8}]
        ]

        request = ReportRequest(
            report_type=ReportType.KNOWLEDGE_MAP,
            format=ReportFormat.JSON
        )

        report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.KNOWLEDGE_MAP
        assert isinstance(report, KnowledgeMapReport)
        assert len(report.nodes) == 5
        assert len(report.edges) == 1

    async def test_generate_learning_path(self, report_generator):
        """Test generating a personalized learning path."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock database queries
        mock_db.fetch.side_effect = [
            # Current knowledge
            [{"topic": "Python", "mastery": 0.8}],
            # Goals
            [{"goal": "Master ML", "priority": 1}],
            # Recommended topics
            [{"topic": "Statistics", "relevance": 0.9}]
        ]

        request = ReportRequest(
            report_type=ReportType.LEARNING_PATH,
            format=ReportFormat.HTML
        )

        with patch('openai.ChatCompletion.create') as mock_openai:
            mock_openai.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "milestones": ["Learn Statistics", "Study ML Basics"],
                    "resources": ["Book 1", "Course 1"],
                    "estimated_duration": "3 months"
                })))]
            )

            report = await generator.generate_report(user_id, request)

        assert report.report_type == ReportType.LEARNING_PATH
        assert isinstance(report, LearningPathReport)
        assert len(report.milestones) == 2

    async def test_export_formats(self, report_generator):
        """Test exporting reports in different formats."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Test each format
        formats = [
            ReportFormat.JSON,
            ReportFormat.HTML,
            ReportFormat.PDF,
            ReportFormat.MARKDOWN,
            ReportFormat.EMAIL
        ]

        for format in formats:
            request = ReportRequest(
                report_type=ReportType.DAILY,
                format=format
            )

            # Mock minimal data
            mock_db.fetch.return_value = []

            with patch.object(generator, '_generate_ai_summary', return_value="Summary"):
                report = await generator.generate_report(user_id, request)

            assert report.format == format
            if format == ReportFormat.HTML:
                assert report.content.startswith("<!DOCTYPE html>")
            elif format == ReportFormat.MARKDOWN:
                assert "# " in report.content
            elif format == ReportFormat.PDF:
                assert report.file_path is not None

    async def test_report_scheduling(self, report_generator):
        """Test report scheduling functionality."""
        generator, mock_db = report_generator
        user_id = "test_user"

        schedule = ReportSchedule(
            user_id=user_id,
            template_id=uuid4(),
            report_type=ReportType.WEEKLY,
            format=ReportFormat.EMAIL,
            schedule_type="weekly",
            schedule_config={"day_of_week": "monday", "time": "09:00"},
            recipients=["user@example.com"],
            enabled=True
        )

        # Test schedule validation
        assert schedule.enabled
        assert schedule.schedule_type == "weekly"
        assert schedule.recipients == ["user@example.com"]

    async def test_template_system(self, report_generator):
        """Test report template functionality."""
        generator, mock_db = report_generator

        template = ReportTemplate(
            name="Custom Weekly",
            description="Custom weekly report",
            report_type=ReportType.WEEKLY,
            sections=["summary", "metrics", "insights"],
            include_visualizations=True,
            include_metrics=True,
            include_recommendations=False
        )

        # Test template application
        request = ReportRequest(
            report_type=ReportType.WEEKLY,
            format=ReportFormat.JSON,
            template_id=template.id
        )

        # Verify template properties
        assert template.name == "Custom Weekly"
        assert len(template.sections) == 3
        assert template.include_visualizations
        assert not template.include_recommendations

    async def test_error_handling(self, report_generator):
        """Test error handling in report generation."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Test database error
        mock_db.fetch.side_effect = Exception("Database error")

        request = ReportRequest(
            report_type=ReportType.DAILY,
            format=ReportFormat.JSON
        )

        with pytest.raises(Exception) as exc_info:
            await generator.generate_report(user_id, request)

        assert "Database error" in str(exc_info.value)

    async def test_performance_optimization(self, report_generator):
        """Test performance optimizations in report generation."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Mock large dataset
        large_memory_set = [
            {"id": str(uuid4()), "title": f"Memory {i}", "content": f"Content {i}"}
            for i in range(1000)
        ]

        mock_db.fetch.return_value = large_memory_set

        request = ReportRequest(
            report_type=ReportType.MONTHLY,
            format=ReportFormat.JSON,
            include_visualizations=False  # Skip heavy processing
        )

        start_time = datetime.utcnow()

        with patch.object(generator, '_generate_ai_summary', return_value="Summary"):
            report = await generator.generate_report(user_id, request)

        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000

        assert report.generation_time_ms < 5000  # Should complete within 5 seconds
        assert report.metadata.get("memory_count") == 1000

    async def test_concurrent_report_generation(self, report_generator):
        """Test concurrent report generation."""
        generator, mock_db = report_generator
        user_id = "test_user"

        # Create multiple report requests
        requests = [
            ReportRequest(report_type=ReportType.DAILY, format=ReportFormat.JSON),
            ReportRequest(report_type=ReportType.WEEKLY, format=ReportFormat.HTML),
            ReportRequest(report_type=ReportType.INSIGHTS, format=ReportFormat.PDF)
        ]

        mock_db.fetch.return_value = []

        # Test concurrent generation
        import asyncio

        with patch.object(generator, '_generate_ai_summary', return_value="Summary"):
            tasks = [generator.generate_report(user_id, req) for req in requests]
            reports = await asyncio.gather(*tasks)

        assert len(reports) == 3
        assert all(isinstance(r, GeneratedReport) for r in reports)
        assert reports[0].report_type == ReportType.DAILY
        assert reports[1].report_type == ReportType.WEEKLY
        assert reports[2].report_type == ReportType.INSIGHTS


class TestReportAPI:
    """Test suite for report API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_report_endpoint(self, test_client):
        """Test the report generation endpoint."""
        request_data = {
            "report_type": "weekly",
            "format": "json",
            "include_visualizations": True
        }

        response = await test_client.post(
            "/synthesis/reports/generate",
            json=request_data,
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "weekly"
        assert data["format"] == "json"

    @pytest.mark.asyncio
    async def test_get_templates_endpoint(self, test_client):
        """Test getting report templates."""
        response = await test_client.get(
            "/synthesis/reports/templates",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        templates = response.json()
        assert len(templates) > 0
        assert all("name" in t for t in templates)

    @pytest.mark.asyncio
    async def test_schedule_report_endpoint(self, test_client):
        """Test scheduling a report."""
        schedule_data = {
            "template_id": str(uuid4()),
            "report_type": "weekly",
            "format": "email",
            "schedule_type": "weekly",
            "schedule_config": {"day_of_week": "monday", "time": "09:00"},
            "recipients": ["user@example.com"],
            "enabled": True
        }

        response = await test_client.post(
            "/synthesis/reports/schedules",
            json=schedule_data,
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        schedule = response.json()
        assert schedule["schedule_type"] == "weekly"
        assert schedule["enabled"] == True
