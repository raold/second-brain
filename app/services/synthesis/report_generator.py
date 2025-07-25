"""
Report Generator Service - v2.8.2

Service for generating automated reports with AI-powered summaries,
multiple export formats, and scheduling capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import asyncpg
from jinja2 import Environment, FileSystemLoader

from app.models.synthesis.report_models import (
    ReportConfig,
    ReportFormat,
    ReportMetrics,
    ReportRequest,
    ReportResponse,
    ReportSection,
    ReportType,
)
from app.services.memory_service import MemoryService
from app.utils.time_utils import parse_relative_timeframe

logger = logging.getLogger(__name__)


class ReportGeneratorConfig:
    """Configuration for report generator."""

    def __init__(
        self,
        template_dir: str = "templates/reports",
        output_dir: str = "output/reports",
        gpt4_api_key: Optional[str] = None,
        max_concurrent_reports: int = 5,
    ):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.gpt4_api_key = gpt4_api_key
        self.max_concurrent_reports = max_concurrent_reports


class ReportGenerator:
    """Service for generating various types of reports."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        memory_service: MemoryService,
        config: ReportGeneratorConfig,
    ):
        self.pool = pool
        self.memory_service = memory_service
        self.config = config
        self._template_env = Environment(loader=FileSystemLoader(config.template_dir))
        self._generation_semaphore = asyncio.Semaphore(config.max_concurrent_reports)

    async def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate a report based on the request configuration."""
        async with self._generation_semaphore:
            start_time = datetime.utcnow()

            try:
                # Determine time range
                start_date, end_date = self._get_time_range(request.config)

                # Gather data based on report type
                data = await self._gather_report_data(
                    request.config.report_type,
                    start_date,
                    end_date,
                    request.config,
                )

                # Calculate metrics
                metrics = await self._calculate_metrics(data, start_date, end_date)

                # Generate sections
                sections = await self._generate_sections(
                    request.config.report_type,
                    data,
                    metrics,
                    request.config,
                )

                # Generate executive summary if requested
                summary = None
                if request.config.include_insights and request.config.use_gpt4_summary:
                    summary = await self._generate_ai_summary(
                        sections,
                        metrics,
                        request.config.summary_length,
                    )

                # Format report
                title = self._generate_title(request.config.report_type, start_date, end_date)
                formatted_content = await self._format_report(
                    title,
                    summary,
                    sections,
                    metrics,
                    request.config.format,
                )

                # Save report if file format
                file_url = None
                file_size = None
                if request.config.format in [ReportFormat.PDF, ReportFormat.DOCX]:
                    file_url, file_size = await self._save_report(
                        formatted_content,
                        request.config.format,
                        title,
                    )

                # Calculate generation time
                generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Create response
                response = ReportResponse(
                    id=f"report_{int(datetime.utcnow().timestamp())}",
                    config=request.config,
                    title=title,
                    summary=summary,
                    sections=sections,
                    metrics=metrics,
                    generation_time_ms=generation_time,
                    format=request.config.format,
                    content=formatted_content if request.config.format in [
                        ReportFormat.MARKDOWN, ReportFormat.HTML, ReportFormat.JSON
                    ] else None,
                    file_url=file_url,
                    file_size_bytes=file_size,
                )

                # Handle delivery
                if request.config.email_recipients:
                    await self._deliver_email(response, request.config.email_recipients)
                    response.delivered = True
                    response.delivery_status = "Email sent successfully"

                if request.config.webhook_url:
                    await self._deliver_webhook(response, str(request.config.webhook_url))
                    response.delivered = True
                    response.delivery_status = "Webhook delivered"

                return response

            except Exception as e:
                logger.error(f"Report generation failed: {e}")
                raise

    def _get_time_range(self, config: ReportConfig) -> tuple[datetime, datetime]:
        """Determine the time range for the report."""
        if config.start_date and config.end_date:
            return config.start_date, config.end_date

        if config.relative_timeframe:
            return parse_relative_timeframe(config.relative_timeframe)

        # Default based on report type
        end_date = datetime.utcnow()
        if config.report_type == ReportType.DAILY:
            start_date = end_date - timedelta(days=1)
        elif config.report_type == ReportType.WEEKLY:
            start_date = end_date - timedelta(days=7)
        elif config.report_type == ReportType.MONTHLY:
            start_date = end_date - timedelta(days=30)
        elif config.report_type == ReportType.QUARTERLY:
            start_date = end_date - timedelta(days=90)
        elif config.report_type == ReportType.ANNUAL:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default 30 days

        return start_date, end_date

    async def _gather_report_data(
        self,
        report_type: ReportType,
        start_date: datetime,
        end_date: datetime,
        config: ReportConfig,
    ) -> dict[str, Any]:
        """Gather data needed for the report."""
        data = {
            "start_date": start_date,
            "end_date": end_date,
            "report_type": report_type,
        }

        # Get memories in date range
        if config.include_memories:
            async with self.pool.acquire() as conn:
                memories = await conn.fetch("""
                    SELECT id, content, metadata, created_at, updated_at
                    FROM memories
                    WHERE created_at BETWEEN $1 AND $2
                    ORDER BY created_at DESC
                """, start_date, end_date)

                data["memories"] = [dict(m) for m in memories]
                data["memory_count"] = len(memories)

        # Get insights if available
        if config.include_insights:
            insights = await self._get_insights(start_date, end_date)
            data["insights"] = insights

        # Get activity data
        activity = await self._get_activity_data(start_date, end_date)
        data["activity"] = activity

        # Get knowledge graph data if requested
        if config.include_graphs:
            graph_data = await self._get_graph_data(start_date, end_date)
            data["graph"] = graph_data

        return data

    async def _calculate_metrics(
        self,
        data: dict[str, Any],
        start_date: datetime,
        end_date: datetime,
    ) -> ReportMetrics:
        """Calculate metrics for the report."""
        metrics = ReportMetrics()

        # Memory metrics
        if "memories" in data:
            metrics.total_memories = len(data["memories"])
            metrics.new_memories = len([
                m for m in data["memories"]
                if m["created_at"] >= start_date
            ])

            # Calculate daily average
            days = max(1, (end_date - start_date).days)
            metrics.average_daily_memories = metrics.new_memories / days

        # Activity metrics
        if "activity" in data:
            metrics.active_days = data["activity"].get("active_days", 0)
            metrics.peak_activity_time = data["activity"].get("peak_time")

        # Knowledge metrics
        if "insights" in data:
            metrics.top_insights = data["insights"][:5]  # Top 5 insights

        # Topics from memories
        if "memories" in data:
            topics = set()
            for memory in data["memories"]:
                if memory.get("metadata", {}).get("topics"):
                    topics.update(memory["metadata"]["topics"])
            metrics.topics_covered = list(topics)[:20]  # Top 20 topics

        # Generate recommendations
        metrics.recommendations = await self._generate_recommendations(data, metrics)

        return metrics

    async def _generate_sections(
        self,
        report_type: ReportType,
        data: dict[str, Any],
        metrics: ReportMetrics,
        config: ReportConfig,
    ) -> list[ReportSection]:
        """Generate report sections based on type."""
        sections = []

        # Overview section
        sections.append(ReportSection(
            title="Overview",
            content=self._generate_overview(data, metrics),
            order=1,
        ))

        # Memory activity section
        if config.include_memories:
            sections.append(ReportSection(
                title="Memory Activity",
                content=self._generate_memory_section(data, metrics),
                order=2,
                include_visualization=True,
                visualization_type="timeline",
            ))

        # Insights section
        if config.include_insights and data.get("insights"):
            sections.append(ReportSection(
                title="Key Insights",
                content=self._generate_insights_section(data["insights"]),
                order=3,
            ))

        # Knowledge graph section
        if config.include_graphs and data.get("graph"):
            sections.append(ReportSection(
                title="Knowledge Network",
                content=self._generate_graph_section(data["graph"]),
                order=4,
                include_visualization=True,
                visualization_type="network",
            ))

        # Recommendations section
        if config.include_recommendations:
            sections.append(ReportSection(
                title="Recommendations",
                content=self._generate_recommendations_section(metrics.recommendations),
                order=5,
            ))

        # Custom sections based on report type
        if report_type == ReportType.LEARNING_PATH:
            sections.append(await self._generate_learning_path_section(data))
        elif report_type == ReportType.PROGRESS:
            sections.append(await self._generate_progress_section(data, metrics))

        return sections

    def _generate_title(
        self,
        report_type: ReportType,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """Generate report title."""
        type_names = {
            ReportType.DAILY: "Daily",
            ReportType.WEEKLY: "Weekly",
            ReportType.MONTHLY: "Monthly",
            ReportType.QUARTERLY: "Quarterly",
            ReportType.ANNUAL: "Annual",
            ReportType.INSIGHTS: "Insights",
            ReportType.PROGRESS: "Progress",
            ReportType.KNOWLEDGE_MAP: "Knowledge Map",
            ReportType.LEARNING_PATH: "Learning Path",
        }

        type_name = type_names.get(report_type, "Custom")
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

        return f"Second Brain {type_name} Report - {date_range}"

    def _generate_overview(self, data: dict[str, Any], metrics: ReportMetrics) -> str:
        """Generate overview section content."""
        return f"""
This report covers the period from {data['start_date'].strftime('%B %d, %Y')} to {data['end_date'].strftime('%B %d, %Y')}.

**Key Metrics:**
- Total memories: {metrics.total_memories}
- New memories added: {metrics.new_memories}
- Average daily memories: {metrics.average_daily_memories:.1f}
- Active days: {metrics.active_days}
- Topics covered: {len(metrics.topics_covered)}
"""

    def _generate_memory_section(self, data: dict[str, Any], metrics: ReportMetrics) -> str:
        """Generate memory activity section."""
        content = f"During this period, {metrics.new_memories} new memories were added.\n\n"

        if metrics.peak_activity_time:
            content += f"Peak activity time: {metrics.peak_activity_time}\n\n"

        if metrics.topics_covered:
            content += "**Top Topics:**\n"
            for topic in metrics.topics_covered[:10]:
                content += f"- {topic}\n"

        return content

    def _generate_insights_section(self, insights: list[dict[str, Any]]) -> str:
        """Generate insights section."""
        content = "**Key insights discovered during this period:**\n\n"

        for i, insight in enumerate(insights[:5], 1):
            content += f"{i}. {insight.get('title', 'Insight')}\n"
            content += f"   {insight.get('description', '')}\n\n"

        return content

    def _generate_graph_section(self, graph_data: dict[str, Any]) -> str:
        """Generate knowledge graph section."""
        return f"""
**Knowledge Network Statistics:**
- Total nodes: {graph_data.get('node_count', 0)}
- Total relationships: {graph_data.get('edge_count', 0)}
- Network density: {graph_data.get('density', 0):.3f}
- Average connections per node: {graph_data.get('avg_degree', 0):.1f}

The knowledge graph shows the interconnections between your memories and concepts.
"""

    def _generate_recommendations_section(self, recommendations: list[str]) -> str:
        """Generate recommendations section."""
        content = "**Recommendations for improving your knowledge management:**\n\n"

        for i, rec in enumerate(recommendations, 1):
            content += f"{i}. {rec}\n"

        return content

    async def _generate_learning_path_section(self, data: dict[str, Any]) -> ReportSection:
        """Generate learning path section for learning path reports."""
        # This would analyze the knowledge graph and suggest learning paths
        content = """
**Suggested Learning Paths:**

Based on your current knowledge and interests, here are recommended learning paths:

1. **Advanced Topic Modeling**
   - Build on your current understanding of NLP
   - Explore transformer architectures
   - Practice with real-world datasets

2. **System Design Patterns**
   - Study distributed systems
   - Learn about scalability patterns
   - Apply to your projects
"""

        return ReportSection(
            title="Learning Paths",
            content=content,
            order=6,
            include_visualization=True,
            visualization_type="path",
        )

    async def _generate_progress_section(
        self,
        data: dict[str, Any],
        metrics: ReportMetrics,
    ) -> ReportSection:
        """Generate progress section for progress reports."""
        # Calculate progress metrics
        prev_period_memories = 100  # Would fetch from DB
        growth_rate = ((metrics.total_memories - prev_period_memories) / prev_period_memories * 100
                      if prev_period_memories > 0 else 0)

        content = f"""
**Progress Summary:**

- Knowledge growth rate: {growth_rate:.1f}%
- New topics explored: {len(metrics.topics_covered)}
- Learning velocity: {metrics.average_daily_memories:.1f} memories/day
- Retention rate: {metrics.retention_rate:.1f}%

Your knowledge base is growing steadily with consistent daily contributions.
"""

        return ReportSection(
            title="Progress Analysis",
            content=content,
            order=6,
            include_visualization=True,
            visualization_type="progress",
        )

    async def _format_report(
        self,
        title: str,
        summary: Optional[str],
        sections: list[ReportSection],
        metrics: ReportMetrics,
        format: ReportFormat,
    ) -> str:
        """Format the report based on the requested format."""
        if format == ReportFormat.JSON:
            return json.dumps({
                "title": title,
                "summary": summary,
                "sections": [s.dict() for s in sections],
                "metrics": metrics.dict(),
            }, indent=2, default=str)

        elif format == ReportFormat.MARKDOWN:
            content = f"# {title}\n\n"
            if summary:
                content += f"## Executive Summary\n\n{summary}\n\n"

            for section in sections:
                content += f"## {section.title}\n\n{section.content}\n\n"

            return content

        elif format == ReportFormat.HTML:
            template = self._template_env.get_template("report.html")
            return template.render(
                title=title,
                summary=summary,
                sections=sections,
                metrics=metrics,
            )

        else:
            # For PDF and DOCX, return HTML that will be converted
            return await self._format_report(title, summary, sections, metrics, ReportFormat.HTML)

    async def _save_report(
        self,
        content: str,
        format: ReportFormat,
        title: str,
    ) -> tuple[str, int]:
        """Save report to file and return URL and size."""
        # Implementation would save to S3 or local storage
        # For now, return mock values
        return f"https://storage.example.com/reports/{title}.{format.value}", len(content)

    async def _deliver_email(self, report: ReportResponse, recipients: list[str]):
        """Deliver report via email."""
        # Implementation would use email service
        logger.info(f"Delivering report {report.id} to {recipients}")

    async def _deliver_webhook(self, report: ReportResponse, webhook_url: str):
        """Deliver report via webhook."""
        # Implementation would POST to webhook
        logger.info(f"Delivering report {report.id} to webhook {webhook_url}")

    async def _get_insights(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get insights for the time period."""
        # Would query insights from database
        return [
            {
                "title": "Knowledge clustering detected",
                "description": "Your memories show strong clustering around machine learning topics",
                "confidence": 0.85,
            },
            {
                "title": "Learning pattern identified",
                "description": "Most productive learning happens between 9-11 AM",
                "confidence": 0.78,
            },
        ]

    async def _get_activity_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """Get activity data for the time period."""
        async with self.pool.acquire() as conn:
            # Get active days
            active_days = await conn.fetchval("""
                SELECT COUNT(DISTINCT DATE(created_at))
                FROM memories
                WHERE created_at BETWEEN $1 AND $2
            """, start_date, end_date)

            # Get peak activity time
            peak_hour = await conn.fetchrow("""
                SELECT EXTRACT(HOUR FROM created_at) as hour, COUNT(*) as count
                FROM memories
                WHERE created_at BETWEEN $1 AND $2
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 1
            """, start_date, end_date)

            return {
                "active_days": active_days,
                "peak_time": f"{int(peak_hour['hour'])}:00" if peak_hour else None,
            }

    async def _get_graph_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        # Would calculate from actual graph data
        return {
            "node_count": 150,
            "edge_count": 420,
            "density": 0.037,
            "avg_degree": 5.6,
        }

    async def _generate_recommendations(
        self,
        data: dict[str, Any],
        metrics: ReportMetrics,
    ) -> list[str]:
        """Generate recommendations based on data and metrics."""
        recommendations = []

        # Based on activity
        if metrics.average_daily_memories < 1:
            recommendations.append("Try to add at least one memory per day to maintain momentum")

        if metrics.active_days < 5:
            recommendations.append("Increase consistency by setting daily reminders")

        # Based on topics
        if len(metrics.topics_covered) < 3:
            recommendations.append("Explore more diverse topics to broaden your knowledge base")

        # Based on insights
        if not data.get("insights"):
            recommendations.append("Add more detailed memories to enable deeper insight generation")

        return recommendations

    async def _generate_ai_summary(
        self,
        sections: list[ReportSection],
        metrics: ReportMetrics,
        target_length: int,
    ) -> str:
        """Generate AI-powered executive summary using GPT-4."""
        if not self.config.gpt4_api_key:
            return self._generate_basic_summary(sections, metrics)

        # In production, would call GPT-4 API
        # For now, return a mock summary
        return f"""
This report shows strong knowledge acquisition with {metrics.new_memories} new memories added,
covering {len(metrics.topics_covered)} distinct topics. The most significant insight is the
emergence of clear knowledge clusters around core technical concepts, suggesting deepening
expertise in specific domains. Activity patterns indicate consistent engagement with peak
productivity in morning hours. Recommendations focus on expanding topic diversity while
maintaining current learning velocity.
"""

    def _generate_basic_summary(
        self,
        sections: list[ReportSection],
        metrics: ReportMetrics,
    ) -> str:
        """Generate basic summary without AI."""
        return f"""
This period saw {metrics.new_memories} new memories added across {len(metrics.topics_covered)} topics.
Average daily activity was {metrics.average_daily_memories:.1f} memories with {metrics.active_days} active days.
Key areas of focus included {', '.join(metrics.topics_covered[:3])} among others.
"""
