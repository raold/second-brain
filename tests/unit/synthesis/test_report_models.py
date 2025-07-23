"""
Unit tests for report generation models - v2.8.2
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.models.synthesis.report_models import (
    ReportType,
    ReportFormat,
    ReportSection,
    ReportTemplate,
    ReportConfig,
    ReportSchedule,
    ReportRequest,
    ReportMetrics,
    ReportResponse,
    ReportFilter,
)


class TestReportModels:
    """Test report generation models."""
    
    def test_report_type_enum(self):
        """Test ReportType enum values."""
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"
        assert ReportType.MONTHLY.value == "monthly"
        assert ReportType.QUARTERLY.value == "quarterly"
        assert ReportType.ANNUAL.value == "annual"
        assert ReportType.INSIGHTS.value == "insights"
        assert ReportType.PROGRESS.value == "progress"
        assert ReportType.KNOWLEDGE_MAP.value == "knowledge_map"
        assert ReportType.LEARNING_PATH.value == "learning_path"
        assert ReportType.CUSTOM.value == "custom"
    
    def test_report_format_enum(self):
        """Test ReportFormat enum values."""
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.MARKDOWN.value == "markdown"
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.EMAIL.value == "email"
        assert ReportFormat.DOCX.value == "docx"
        assert ReportFormat.CSV.value == "csv"
    
    def test_report_section_model(self):
        """Test ReportSection model."""
        section = ReportSection(
            title="Test Section",
            content="Test content",
            order=1,
            include_visualization=True,
            visualization_type="bar_chart",
            metadata={"key": "value"}
        )
        
        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.order == 1
        assert section.include_visualization is True
        assert section.visualization_type == "bar_chart"
        assert section.metadata == {"key": "value"}
    
    def test_report_template_model(self):
        """Test ReportTemplate model."""
        template = ReportTemplate(
            name="Monthly Summary",
            description="Monthly summary report template",
            report_type=ReportType.MONTHLY,
            sections=["overview", "memories", "insights"],
            default_format=ReportFormat.PDF,
            custom_css=".header { color: blue; }",
            include_summary=True
        )
        
        assert template.name == "Monthly Summary"
        assert template.report_type == ReportType.MONTHLY
        assert len(template.sections) == 3
        assert template.default_format == ReportFormat.PDF
        assert template.include_summary is True
        assert isinstance(template.created_at, datetime)
    
    def test_report_config_model(self):
        """Test ReportConfig model."""
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            format=ReportFormat.HTML,
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            include_memories=True,
            include_insights=True,
            include_graphs=True,
            include_recommendations=True,
            use_gpt4_summary=True,
            summary_length=500,
            analysis_depth="deep",
            email_recipients=["user@example.com"],
            webhook_url="https://example.com/webhook"
        )
        
        assert config.report_type == ReportType.WEEKLY
        assert config.format == ReportFormat.HTML
        assert config.include_memories is True
        assert config.use_gpt4_summary is True
        assert config.summary_length == 500
        assert len(config.email_recipients) == 1
    
    def test_report_config_timeframe_validation(self):
        """Test ReportConfig timeframe validation."""
        # Valid timeframe
        config = ReportConfig(
            report_type=ReportType.DAILY,
            relative_timeframe="last_7_days"
        )
        assert config.relative_timeframe == "last_7_days"
        
        # Invalid timeframe
        with pytest.raises(ValidationError) as exc_info:
            ReportConfig(
                report_type=ReportType.DAILY,
                relative_timeframe="invalid_timeframe"
            )
        assert "Invalid timeframe" in str(exc_info.value)
    
    def test_report_schedule_model(self):
        """Test ReportSchedule model."""
        config = ReportConfig(report_type=ReportType.WEEKLY)
        schedule = ReportSchedule(
            name="Weekly Report",
            config=config,
            enabled=True,
            cron_expression="0 9 * * MON",
            timezone="UTC",
            auto_deliver=True,
            delivery_format=ReportFormat.PDF
        )
        
        assert schedule.name == "Weekly Report"
        assert schedule.enabled is True
        assert schedule.cron_expression == "0 9 * * MON"
        assert schedule.timezone == "UTC"
        assert schedule.auto_deliver is True
        assert isinstance(schedule.created_at, datetime)
    
    def test_report_schedule_cron_validation(self):
        """Test ReportSchedule cron validation."""
        config = ReportConfig(report_type=ReportType.DAILY)
        
        # Valid cron expressions
        valid_crons = [
            "0 9 * * *",  # Daily at 9 AM
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
            "0 0 1 1,4,7,10 *",  # Quarterly
            "0 0 0 0 0 0",  # With seconds
        ]
        
        for cron in valid_crons:
            schedule = ReportSchedule(
                name="Test",
                config=config,
                cron_expression=cron,
                delivery_format=ReportFormat.PDF
            )
            assert schedule.cron_expression == cron
        
        # Invalid cron expression
        with pytest.raises(ValidationError):
            ReportSchedule(
                name="Test",
                config=config,
                cron_expression="invalid",
                delivery_format=ReportFormat.PDF
            )
    
    def test_report_request_model(self):
        """Test ReportRequest model."""
        config = ReportConfig(report_type=ReportType.MONTHLY)
        request = ReportRequest(
            config=config,
            immediate=True,
            priority="high",
            callback_url="https://example.com/callback"
        )
        
        assert request.config.report_type == ReportType.MONTHLY
        assert request.immediate is True
        assert request.priority == "high"
        assert str(request.callback_url) == "https://example.com/callback"
    
    def test_report_metrics_model(self):
        """Test ReportMetrics model."""
        metrics = ReportMetrics(
            total_memories=100,
            new_memories=25,
            memories_reviewed=50,
            active_days=20,
            peak_activity_time="09:00",
            average_daily_memories=3.5,
            topics_covered=["AI", "Python", "Machine Learning"],
            knowledge_growth_rate=15.5,
            retention_rate=0.85,
            top_insights=[
                {"title": "Insight 1", "confidence": 0.9},
                {"title": "Insight 2", "confidence": 0.8}
            ],
            recommendations=[
                "Add more memories daily",
                "Review older memories"
            ]
        )
        
        assert metrics.total_memories == 100
        assert metrics.new_memories == 25
        assert metrics.average_daily_memories == 3.5
        assert len(metrics.topics_covered) == 3
        assert metrics.retention_rate == 0.85
        assert len(metrics.top_insights) == 2
        assert len(metrics.recommendations) == 2
    
    def test_report_response_model(self):
        """Test ReportResponse model."""
        config = ReportConfig(report_type=ReportType.WEEKLY)
        metrics = ReportMetrics()
        sections = [
            ReportSection(title="Overview", content="Test overview", order=1),
            ReportSection(title="Details", content="Test details", order=2)
        ]
        
        response = ReportResponse(
            id="report_123",
            config=config,
            title="Weekly Report",
            summary="Executive summary",
            sections=sections,
            metrics=metrics,
            generation_time_ms=1500,
            format=ReportFormat.PDF,
            file_url="https://storage.example.com/report.pdf",
            file_size_bytes=150000,
            delivered=True,
            delivery_status="Email sent"
        )
        
        assert response.id == "report_123"
        assert response.title == "Weekly Report"
        assert response.summary == "Executive summary"
        assert len(response.sections) == 2
        assert response.generation_time_ms == 1500
        assert response.format == ReportFormat.PDF
        assert response.delivered is True
        assert isinstance(response.generated_at, datetime)
    
    def test_report_filter_model(self):
        """Test ReportFilter model."""
        filter = ReportFilter(
            report_type=ReportType.MONTHLY,
            format=ReportFormat.PDF,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            delivered=True,
            limit=20,
            offset=0
        )
        
        assert filter.report_type == ReportType.MONTHLY
        assert filter.format == ReportFormat.PDF
        assert filter.delivered is True
        assert filter.limit == 20
        assert filter.offset == 0
    
    def test_report_filter_limits(self):
        """Test ReportFilter limit validation."""
        # Valid limits
        filter1 = ReportFilter(limit=1)
        assert filter1.limit == 1
        
        filter2 = ReportFilter(limit=100)
        assert filter2.limit == 100
        
        # Invalid limits
        with pytest.raises(ValidationError):
            ReportFilter(limit=0)
        
        with pytest.raises(ValidationError):
            ReportFilter(limit=101)
        
        with pytest.raises(ValidationError):
            ReportFilter(offset=-1)


class TestReportModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_report_config_serialization(self):
        """Test ReportConfig serialization."""
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            format=ReportFormat.JSON,
            include_insights=True,
            email_recipients=["test@example.com"]
        )
        
        # Serialize
        data = config.dict()
        assert data["report_type"] == "weekly"
        assert data["format"] == "json"
        assert data["include_insights"] is True
        
        # Deserialize
        config2 = ReportConfig(**data)
        assert config2.report_type == ReportType.WEEKLY
        assert config2.format == ReportFormat.JSON
    
    def test_report_response_json_serialization(self):
        """Test ReportResponse JSON serialization."""
        config = ReportConfig(report_type=ReportType.DAILY)
        response = ReportResponse(
            id="test_123",
            config=config,
            title="Test Report",
            sections=[],
            metrics=ReportMetrics(),
            generation_time_ms=100,
            format=ReportFormat.JSON
        )
        
        # Serialize to JSON
        json_data = response.json()
        assert "test_123" in json_data
        assert "Test Report" in json_data
        
        # Parse back
        import json
        data = json.loads(json_data)
        assert data["id"] == "test_123"
        assert data["title"] == "Test Report"