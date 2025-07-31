"""
Test report models for synthesis features
"""

from datetime import datetime

from app.models.synthesis.report_models import (
    ReportFormat,
    ReportRequest,
    ReportResponse,
    ReportSchedule,
    ReportSection,
    ReportType,
)


class TestReportModels:
    """Test synthesis report models"""

    def test_report_request_creation(self):
        """Test creating a report request"""
        request = ReportRequest(
            report_type=ReportType.DAILY_SUMMARY,
            format=ReportFormat.MARKDOWN,
            user_id="user-123"
        )

        assert request.report_type == ReportType.DAILY_SUMMARY
        assert request.format == ReportFormat.MARKDOWN
        assert request.user_id == "user-123"

    def test_report_response_creation(self):
        """Test creating a report response"""
        sections = [
            ReportSection(
                title="Executive Summary",
                content="This is the summary content",
                order=1
            ),
            ReportSection(
                title="Details",
                content="Detailed analysis here",
                order=2
            )
        ]

        response = ReportResponse(
            report_id="report-123",
            report_type=ReportType.WEEKLY_INSIGHTS,
            format=ReportFormat.HTML,
            sections=sections,
            generated_at=datetime.utcnow().isoformat()
        )

        assert response.report_id == "report-123"
        assert response.report_type == ReportType.WEEKLY_INSIGHTS
        assert response.format == ReportFormat.HTML
        assert len(response.sections) == 2
        assert response.sections[0].title == "Executive Summary"

    def test_report_schedule_creation(self):
        """Test creating a report schedule"""
        schedule = ReportSchedule(
            schedule_id="schedule-456",
            report_type=ReportType.MONTHLY_REVIEW,
            cron_expression="0 9 1 * *",  # First day of month at 9 AM
            is_active=True,
            last_run=None,
            next_run=datetime.utcnow().isoformat()
        )

        assert schedule.schedule_id == "schedule-456"
        assert schedule.report_type == ReportType.MONTHLY_REVIEW
        assert schedule.cron_expression == "0 9 1 * *"
        assert schedule.is_active is True
        assert schedule.last_run is None

    def test_report_section_ordering(self):
        """Test report section ordering"""
        sections = [
            ReportSection(title="Third", content="Content 3", order=3),
            ReportSection(title="First", content="Content 1", order=1),
            ReportSection(title="Second", content="Content 2", order=2)
        ]

        # Sort by order
        sorted_sections = sorted(sections, key=lambda s: s.order)

        assert sorted_sections[0].title == "First"
        assert sorted_sections[1].title == "Second"
        assert sorted_sections[2].title == "Third"
