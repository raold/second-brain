"""
Automated report generation service
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    colors = None
    letter = None
    SimpleDocTemplate = Table = TableStyle = Paragraph = Spacer = PageBreak = None
    getSampleStyleSheet = ParagraphStyle = None
    inch = None
    REPORTLAB_AVAILABLE = False
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.memory import Memory
from app.models.synthesis.report_models import (
    GeneratedReport,
    ReportFormat,
    ReportRequest,
    ReportSection,
    ReportType,
)
from app.services.memory_service import MemoryService
from app.services.synthesis.graph_metrics_service import GraphMetricsService
from app.services.synthesis.knowledge_summarizer import KnowledgeSummarizer
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ReportGenerator:
    """Service for generating automated reports"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
        self.metrics_service = GraphMetricsService(db)
        self.summarizer = KnowledgeSummarizer(db)
        self.template_env = self._setup_templates()

    def _setup_templates(self):
        """Setup Jinja2 templates for HTML reports"""
        template_dir = Path(__file__).parent.parent.parent / "templates" / "reports"
        if not template_dir.exists():
            template_dir.mkdir(parents=True, exist_ok=True)
            # Create default templates
            self._create_default_templates(template_dir)

        return Environment(loader=FileSystemLoader(str(template_dir)))

    async def generate_report(
        self,
        user_id: str,
        request: ReportRequest
    ) -> GeneratedReport:
        """Generate a report based on request parameters"""
        start_time = datetime.utcnow()

        try:
            # Determine report period
            period_start, period_end = self._determine_period(
                request.report_type,
                request.period_start,
                request.period_end
            )

            # Generate report based on type
            if request.report_type == ReportType.INSIGHTS:
                report_data = await self._generate_insights_report(
                    user_id, period_start, period_end
                )
            elif request.report_type == ReportType.PROGRESS:
                report_data = await self._generate_progress_report(
                    user_id, period_start, period_end
                )
            elif request.report_type == ReportType.KNOWLEDGE_MAP:
                report_data = await self._generate_knowledge_map_report(user_id)
            elif request.report_type == ReportType.LEARNING_PATH:
                report_data = await self._generate_learning_path_report(
                    user_id, request.options.get("goal", "general knowledge")
                )
            else:
                # Standard periodic report
                report_data = await self._generate_periodic_report(
                    user_id, request.report_type, period_start, period_end
                )

            # Build report sections
            sections = await self._build_report_sections(
                user_id, request, report_data, period_start, period_end
            )

            # Generate executive summary
            executive_summary = await self._generate_executive_summary(
                sections, report_data
            )

            # Format report
            file_path = await self._format_report(
                user_id,
                request.format,
                request.custom_title or f"{request.report_type.value.title()} Report",
                executive_summary,
                sections,
                report_data
            )

            # Calculate file size
            file_size = Path(file_path).stat().st_size if file_path else None

            # Create report record
            generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            report = GeneratedReport(
                user_id=user_id,
                template_id=request.template_id,
                report_type=request.report_type,
                title=request.custom_title or f"{request.report_type.value.title()} Report",
                subtitle=f"{period_start.strftime('%B %d, %Y')} - {period_end.strftime('%B %d, %Y')}",
                executive_summary=executive_summary,
                sections=sections,
                metadata=report_data.get("metadata", {}),
                metrics=report_data.get("metrics", {}),
                recommendations=report_data.get("recommendations", []),
                format=request.format,
                file_path=file_path,
                file_size=file_size,
                generation_time_ms=generation_time_ms,
                period_start=period_start,
                period_end=period_end
            )

            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise

    async def _generate_insights_report(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> dict[str, Any]:
        """Generate insights report data"""
        # Get memories from period
        memories = await self._get_period_memories(user_id, period_start, period_end)

        # Get metrics
        current_metrics = await self.metrics_service.calculate_metrics(user_id)
        dashboard = await self.metrics_service.get_metrics_dashboard(user_id, 30)

        # Analyze patterns
        patterns = await self._analyze_patterns(memories)

        # Identify emerging topics
        emerging_topics = await self._identify_emerging_topics(memories, period_start)

        # Find knowledge gaps
        knowledge_gaps = await self._identify_knowledge_gaps(user_id, memories)

        # Generate insights
        top_insights = [
            f"You created {len(memories)} memories in the past period",
            f"Your knowledge graph has {current_metrics.node_count} nodes with {current_metrics.edge_count} connections",
            f"Top emerging topic: {emerging_topics[0]['topic'] if emerging_topics else 'None identified'}"
        ]

        # Add metric-based insights
        if dashboard.insights:
            top_insights.extend(dashboard.insights[:5])

        return {
            "top_insights": top_insights,
            "key_patterns": patterns,
            "emerging_topics": emerging_topics,
            "knowledge_gaps": knowledge_gaps,
            "memory_growth": {
                "total": len(memories),
                "daily_average": len(memories) / max((period_end - period_start).days, 1),
                "by_type": self._count_by_type(memories)
            },
            "connection_growth": {
                "new_connections": current_metrics.new_edges_last_hour * 24 * 7,  # Estimate
                "density": current_metrics.density,
                "clustering": current_metrics.clustering_coefficient
            },
            "recommendations": dashboard.recommendations[:5],
            "metrics": {
                "total_memories": current_metrics.node_count,
                "total_connections": current_metrics.edge_count,
                "graph_density": current_metrics.density
            }
        }

    async def _generate_progress_report(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> dict[str, Any]:
        """Generate progress report data"""
        # Get memories and metrics
        memories = await self._get_period_memories(user_id, period_start, period_end)

        # Calculate progress metrics
        memories_created = len(memories)
        memories_reviewed = await self._count_reviewed_memories(user_id, period_start, period_end)
        connections_made = await self._count_new_connections(user_id, period_start, period_end)
        topics_explored = len(set(m.metadata.get("topic", "unknown") for m in memories if m.metadata))

        # Calculate learning metrics
        retention_score = await self._calculate_retention_score(user_id, memories)
        learning_velocity = memories_created / max((period_end - period_start).days, 1)
        topic_mastery = await self._calculate_topic_mastery(user_id, memories)

        # Check milestones
        milestones = []
        if memories_created >= 100:
            milestones.append("Created 100+ memories")
        if connections_made >= 50:
            milestones.append("Made 50+ connections")
        if topics_explored >= 10:
            milestones.append("Explored 10+ topics")

        # Calculate streaks
        streaks = await self._calculate_streaks(user_id, period_end)

        # Compare with previous period
        prev_start = period_start - (period_end - period_start)
        prev_memories = await self._get_period_memories(user_id, prev_start, period_start)

        vs_previous = {
            "memories_created": ((memories_created - len(prev_memories)) / max(len(prev_memories), 1)) * 100,
            "learning_velocity": ((learning_velocity - (len(prev_memories) / max((period_start - prev_start).days, 1))) / max(1, len(prev_memories) / max((period_start - prev_start).days, 1))) * 100
        }

        return {
            "memories_created": memories_created,
            "memories_reviewed": memories_reviewed,
            "connections_made": connections_made,
            "topics_explored": topics_explored,
            "knowledge_retention_score": retention_score,
            "learning_velocity": learning_velocity,
            "topic_mastery": topic_mastery,
            "milestones_reached": milestones,
            "streaks": streaks,
            "vs_previous_period": vs_previous,
            "focus_areas": list(topic_mastery.keys())[:3],
            "metrics": {
                "total_progress": memories_created,
                "daily_average": learning_velocity,
                "retention": retention_score
            }
        }

    async def _generate_knowledge_map_report(
        self,
        user_id: str
    ) -> dict[str, Any]:
        """Generate knowledge map report data"""
        # Get current graph metrics
        metrics = await self.metrics_service.calculate_metrics(user_id)

        # Analyze domains and clusters
        domains = await self._analyze_knowledge_domains(user_id)
        clusters = await self._identify_topic_clusters(user_id)
        bridges = await self._find_bridge_connections(user_id)

        # Calculate coverage and density
        domain_coverage = {d["name"]: d["coverage"] for d in domains}
        cluster_density = {c["name"]: c["density"] for c in clusters}

        # Identify strengths and weaknesses
        sorted_domains = sorted(domains, key=lambda d: d["size"], reverse=True)
        strongest_domains = [d["name"] for d in sorted_domains[:5]]
        weakest_domains = [d["name"] for d in sorted_domains[-5:] if d["size"] < 10]

        # Find isolated clusters
        isolated_clusters = [c["name"] for c in clusters if c["connections"] < 3]

        # Identify bridge opportunities
        bridge_opportunities = await self._find_bridge_opportunities(domains, clusters)

        # Generate graph data
        graph_data = await self._generate_graph_visualization_data(user_id)

        return {
            "domains": domains,
            "clusters": clusters,
            "bridges": bridges,
            "domain_coverage": domain_coverage,
            "cluster_density": cluster_density,
            "connectivity_score": min(metrics.density * 100, 1.0),
            "strongest_domains": strongest_domains,
            "weakest_domains": weakest_domains,
            "isolated_clusters": isolated_clusters,
            "bridge_opportunities": bridge_opportunities,
            "graph_data": graph_data,
            "metrics": {
                "total_domains": len(domains),
                "total_clusters": len(clusters),
                "connectivity": metrics.density
            }
        }

    async def _generate_learning_path_report(
        self,
        user_id: str,
        goal: str
    ) -> dict[str, Any]:
        """Generate personalized learning path report"""
        # Analyze current knowledge
        current_knowledge = await self._analyze_current_knowledge(user_id, goal)

        # Identify knowledge gaps
        knowledge_gaps = await self._identify_learning_gaps(user_id, goal, current_knowledge)

        # Generate learning path
        learning_path = await self._create_learning_path(
            current_knowledge, knowledge_gaps, goal
        )

        # Estimate duration
        estimated_duration = self._estimate_learning_duration(learning_path)

        # Determine difficulty
        difficulty = self._assess_difficulty_level(current_knowledge, knowledge_gaps)

        # Find related resources
        suggested_topics = [step["topic"] for step in learning_path]
        related_memories = await self._find_related_memories(user_id, suggested_topics)

        # Create milestones
        milestones = self._create_learning_milestones(learning_path, goal)

        # Define completion criteria
        completion_criteria = [
            f"Master {len(learning_path)} key topics",
            f"Create at least {len(learning_path) * 5} related memories",
            f"Establish {len(learning_path) * 3} knowledge connections",
            "Pass final knowledge assessment"
        ]

        return {
            "goal": goal,
            "current_knowledge": current_knowledge,
            "knowledge_gaps": knowledge_gaps,
            "recommended_path": learning_path,
            "estimated_duration": estimated_duration,
            "difficulty_level": difficulty,
            "suggested_topics": suggested_topics,
            "related_memories": [str(m.id) for m in related_memories[:20]],
            "milestones": milestones,
            "completion_criteria": completion_criteria,
            "metrics": {
                "path_length": len(learning_path),
                "gap_count": len(knowledge_gaps),
                "estimated_days": int(estimated_duration.split()[0])
            }
        }

    async def _generate_periodic_report(
        self,
        user_id: str,
        report_type: ReportType,
        period_start: datetime,
        period_end: datetime
    ) -> dict[str, Any]:
        """Generate standard periodic report (daily/weekly/monthly)"""
        # Get period summary
        period_summary = await self.summarizer.summarize_time_period(
            user_id, period_start, period_end, report_type.value
        )

        # Get metrics
        metrics = await self.metrics_service.calculate_metrics(user_id)

        # Get top memories
        memories = await self._get_period_memories(user_id, period_start, period_end)
        top_memories = sorted(memories, key=lambda m: m.importance, reverse=True)[:10]

        return {
            "summary": period_summary.summary,
            "highlights": period_summary.highlights,
            "new_topics": period_summary.new_topics,
            "new_entities": period_summary.new_entities,
            "top_memories": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "importance": m.importance
                } for m in top_memories
            ],
            "statistics": period_summary.statistics,
            "trends": period_summary.trends,
            "metrics": {
                "total_memories": len(memories),
                "avg_importance": sum(m.importance for m in memories) / len(memories) if memories else 0,
                "connections": metrics.edge_count
            },
            "recommendations": [
                f"Review {len([m for m in memories if m.importance > 0.8])} high-importance memories",
                f"Connect memories about {period_summary.new_topics[0] if period_summary.new_topics else 'recent topics'}",
                "Consider consolidating similar memories"
            ]
        }

    async def _build_report_sections(
        self,
        user_id: str,
        request: ReportRequest,
        report_data: dict[str, Any],
        period_start: datetime,
        period_end: datetime
    ) -> list[ReportSection]:
        """Build report sections based on type and data"""
        sections = []

        # Executive Summary Section
        sections.append(ReportSection(
            id="executive_summary",
            title="Executive Summary",
            content=self._format_executive_section(report_data),
            order=1
        ))

        # Type-specific sections
        if request.report_type == ReportType.INSIGHTS:
            sections.extend(self._build_insights_sections(report_data))
        elif request.report_type == ReportType.PROGRESS:
            sections.extend(self._build_progress_sections(report_data))
        elif request.report_type == ReportType.KNOWLEDGE_MAP:
            sections.extend(self._build_knowledge_map_sections(report_data))
        elif request.report_type == ReportType.LEARNING_PATH:
            sections.extend(self._build_learning_path_sections(report_data))
        else:
            sections.extend(self._build_periodic_sections(report_data))

        # Add recommendations section
        if report_data.get("recommendations"):
            sections.append(ReportSection(
                id="recommendations",
                title="Recommendations",
                content=self._format_recommendations(report_data["recommendations"]),
                order=len(sections) + 1
            ))

        return sections

    def _format_executive_section(self, report_data: dict[str, Any]) -> str:
        """Format executive summary section"""
        content = []

        if "summary" in report_data:
            content.append(report_data["summary"])

        if "top_insights" in report_data:
            content.append("\n### Key Insights\n")
            for insight in report_data["top_insights"][:5]:
                content.append(f"- {insight}")

        if "metrics" in report_data:
            content.append("\n### Key Metrics\n")
            for key, value in list(report_data["metrics"].items())[:5]:
                content.append(f"- **{key.replace('_', ' ').title()}**: {value}")

        return "\n".join(content)

    def _build_insights_sections(self, report_data: dict[str, Any]) -> list[ReportSection]:
        """Build sections for insights report"""
        sections = []
        order = 2

        # Patterns section
        if report_data.get("key_patterns"):
            sections.append(ReportSection(
                id="patterns",
                title="Key Patterns Discovered",
                content=self._format_patterns(report_data["key_patterns"]),
                order=order,
                data={"patterns": report_data["key_patterns"]}
            ))
            order += 1

        # Emerging topics section
        if report_data.get("emerging_topics"):
            sections.append(ReportSection(
                id="emerging_topics",
                title="Emerging Topics",
                content=self._format_emerging_topics(report_data["emerging_topics"]),
                order=order,
                data={"topics": report_data["emerging_topics"]}
            ))
            order += 1

        # Knowledge gaps section
        if report_data.get("knowledge_gaps"):
            sections.append(ReportSection(
                id="knowledge_gaps",
                title="Knowledge Gap Analysis",
                content=self._format_knowledge_gaps(report_data["knowledge_gaps"]),
                order=order,
                data={"gaps": report_data["knowledge_gaps"]}
            ))
            order += 1

        # Growth metrics section
        sections.append(ReportSection(
            id="growth_metrics",
            title="Growth Metrics",
            content=self._format_growth_metrics(
                report_data.get("memory_growth", {}),
                report_data.get("connection_growth", {})
            ),
            order=order,
            visualizations=[self._create_growth_chart_data(report_data)]
        ))

        return sections

    def _build_progress_sections(self, report_data: dict[str, Any]) -> list[ReportSection]:
        """Build sections for progress report"""
        sections = []
        order = 2

        # Progress overview
        sections.append(ReportSection(
            id="progress_overview",
            title="Progress Overview",
            content=self._format_progress_overview(report_data),
            order=order,
            data={
                "memories_created": report_data.get("memories_created", 0),
                "connections_made": report_data.get("connections_made", 0)
            }
        ))
        order += 1

        # Learning metrics
        sections.append(ReportSection(
            id="learning_metrics",
            title="Learning Metrics",
            content=self._format_learning_metrics(report_data),
            order=order,
            visualizations=[self._create_retention_chart_data(report_data)]
        ))
        order += 1

        # Achievements
        if report_data.get("milestones_reached"):
            sections.append(ReportSection(
                id="achievements",
                title="Achievements",
                content=self._format_achievements(
                    report_data["milestones_reached"],
                    report_data.get("streaks", {})
                ),
                order=order
            ))
            order += 1

        # Comparisons
        if report_data.get("vs_previous_period"):
            sections.append(ReportSection(
                id="comparisons",
                title="Period Comparison",
                content=self._format_comparisons(report_data["vs_previous_period"]),
                order=order,
                visualizations=[self._create_comparison_chart_data(report_data)]
            ))

        return sections

    def _build_knowledge_map_sections(self, report_data: dict[str, Any]) -> list[ReportSection]:
        """Build sections for knowledge map report"""
        sections = []
        order = 2

        # Domain analysis
        sections.append(ReportSection(
            id="domain_analysis",
            title="Knowledge Domain Analysis",
            content=self._format_domain_analysis(
                report_data.get("domains", []),
                report_data.get("domain_coverage", {})
            ),
            order=order,
            visualizations=[self._create_domain_chart_data(report_data)]
        ))
        order += 1

        # Cluster analysis
        sections.append(ReportSection(
            id="cluster_analysis",
            title="Topic Cluster Analysis",
            content=self._format_cluster_analysis(
                report_data.get("clusters", []),
                report_data.get("isolated_clusters", [])
            ),
            order=order
        ))
        order += 1

        # Connectivity analysis
        sections.append(ReportSection(
            id="connectivity",
            title="Knowledge Connectivity",
            content=self._format_connectivity_analysis(
                report_data.get("connectivity_score", 0),
                report_data.get("bridges", []),
                report_data.get("bridge_opportunities", [])
            ),
            order=order
        ))
        order += 1

        # Knowledge map visualization
        if report_data.get("graph_data"):
            sections.append(ReportSection(
                id="knowledge_map",
                title="Interactive Knowledge Map",
                content="See the interactive visualization below to explore your knowledge graph.",
                order=order,
                visualizations=[report_data["graph_data"]]
            ))

        return sections

    def _build_learning_path_sections(self, report_data: dict[str, Any]) -> list[ReportSection]:
        """Build sections for learning path report"""
        sections = []
        order = 2

        # Current state
        sections.append(ReportSection(
            id="current_state",
            title="Current Knowledge State",
            content=self._format_current_knowledge(
                report_data.get("current_knowledge", []),
                report_data.get("knowledge_gaps", [])
            ),
            order=order
        ))
        order += 1

        # Learning path
        sections.append(ReportSection(
            id="learning_path",
            title="Recommended Learning Path",
            content=self._format_learning_path(
                report_data.get("recommended_path", []),
                report_data.get("estimated_duration", "Unknown"),
                report_data.get("difficulty_level", "intermediate")
            ),
            order=order,
            visualizations=[self._create_learning_path_visualization(report_data)]
        ))
        order += 1

        # Milestones
        sections.append(ReportSection(
            id="milestones",
            title="Learning Milestones",
            content=self._format_milestones(report_data.get("milestones", [])),
            order=order
        ))
        order += 1

        # Resources
        sections.append(ReportSection(
            id="resources",
            title="Learning Resources",
            content=self._format_learning_resources(
                report_data.get("suggested_topics", []),
                report_data.get("related_memories", [])
            ),
            order=order
        ))

        return sections

    def _build_periodic_sections(self, report_data: dict[str, Any]) -> list[ReportSection]:
        """Build sections for periodic reports"""
        sections = []
        order = 2

        # Highlights
        if report_data.get("highlights"):
            sections.append(ReportSection(
                id="highlights",
                title="Period Highlights",
                content=self._format_highlights(report_data["highlights"]),
                order=order
            ))
            order += 1

        # New discoveries
        if report_data.get("new_topics") or report_data.get("new_entities"):
            sections.append(ReportSection(
                id="new_discoveries",
                title="New Discoveries",
                content=self._format_discoveries(
                    report_data.get("new_topics", []),
                    report_data.get("new_entities", [])
                ),
                order=order
            ))
            order += 1

        # Top memories
        if report_data.get("top_memories"):
            sections.append(ReportSection(
                id="top_memories",
                title="Most Important Memories",
                content=self._format_top_memories(report_data["top_memories"]),
                order=order
            ))
            order += 1

        # Statistics
        if report_data.get("statistics"):
            sections.append(ReportSection(
                id="statistics",
                title="Period Statistics",
                content=self._format_statistics(report_data["statistics"]),
                order=order,
                visualizations=[self._create_statistics_chart_data(report_data)]
            ))

        return sections

    async def _generate_executive_summary(
        self,
        sections: list[ReportSection],
        report_data: dict[str, Any]
    ) -> str:
        """Generate executive summary for the report"""
        summary_points = []

        # Extract key points from sections
        for section in sections[:3]:  # First 3 sections
            if section.content:
                # Extract first paragraph or bullet points
                lines = section.content.split('\n')
                for line in lines[:3]:
                    if line.strip() and not line.startswith('#'):
                        summary_points.append(line.strip('- '))

        # Add key metrics
        if "metrics" in report_data:
            for key, value in list(report_data["metrics"].items())[:3]:
                summary_points.append(f"{key.replace('_', ' ').title()}: {value}")

        # Combine into summary
        summary = " ".join(summary_points[:5])

        return summary if summary else "This report provides a comprehensive analysis of your knowledge management activities."

    async def _format_report(
        self,
        user_id: str,
        format: ReportFormat,
        title: str,
        executive_summary: str,
        sections: list[ReportSection],
        report_data: dict[str, Any]
    ) -> Optional[str]:
        """Format report in specified format"""
        report_dir = Path(f"reports/{user_id}")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format == ReportFormat.HTML:
            return await self._format_html_report(
                report_dir, timestamp, title, executive_summary, sections, report_data
            )
        elif format == ReportFormat.PDF:
            return await self._format_pdf_report(
                report_dir, timestamp, title, executive_summary, sections, report_data
            )
        elif format == ReportFormat.MARKDOWN:
            return await self._format_markdown_report(
                report_dir, timestamp, title, executive_summary, sections
            )
        elif format == ReportFormat.JSON:
            return await self._format_json_report(
                report_dir, timestamp, title, executive_summary, sections, report_data
            )
        else:
            # Email format returns None (sent directly)
            return None

    async def _format_html_report(
        self,
        report_dir: Path,
        timestamp: str,
        title: str,
        executive_summary: str,
        sections: list[ReportSection],
        report_data: dict[str, Any]
    ) -> str:
        """Format report as HTML"""
        template = self.template_env.get_template("report_template.html")

        html_content = template.render(
            title=title,
            executive_summary=executive_summary,
            sections=sections,
            report_data=report_data,
            generated_at=datetime.utcnow().strftime("%B %d, %Y at %I:%M %p")
        )

        file_path = report_dir / f"report_{timestamp}.html"
        file_path.write_text(html_content)

        return str(file_path)

    async def _format_pdf_report(
        self,
        report_dir: Path,
        timestamp: str,
        title: str,
        executive_summary: str,
        sections: list[ReportSection],
        report_data: dict[str, Any]
    ) -> str:
        """Format report as PDF using ReportLab"""
        file_path = report_dir / f"report_{timestamp}.pdf"

        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Paragraph(executive_summary, styles['BodyText']))
        story.append(Spacer(1, 12))

        # Sections
        for section in sections:
            story.append(Paragraph(section.title, styles['Heading2']))

            # Convert markdown to paragraphs
            for paragraph in section.content.split('\n\n'):
                if paragraph.strip():
                    story.append(Paragraph(paragraph, styles['BodyText']))

            story.append(Spacer(1, 12))

            # Add page break after major sections
            if section.order % 3 == 0:
                story.append(PageBreak())

        # Build PDF
        doc.build(story)

        return str(file_path)

    async def _format_markdown_report(
        self,
        report_dir: Path,
        timestamp: str,
        title: str,
        executive_summary: str,
        sections: list[ReportSection]
    ) -> str:
        """Format report as Markdown"""
        content = [f"# {title}\n"]
        content.append(f"*Generated on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}*\n")
        content.append(f"## Executive Summary\n\n{executive_summary}\n")

        for section in sections:
            content.append(f"## {section.title}\n")
            content.append(f"{section.content}\n")

        file_path = report_dir / f"report_{timestamp}.md"
        file_path.write_text("\n".join(content))

        return str(file_path)

    async def _format_json_report(
        self,
        report_dir: Path,
        timestamp: str,
        title: str,
        executive_summary: str,
        sections: list[ReportSection],
        report_data: dict[str, Any]
    ) -> str:
        """Format report as JSON"""
        report_json = {
            "title": title,
            "executive_summary": executive_summary,
            "sections": [s.dict() for s in sections],
            "data": report_data,
            "generated_at": datetime.utcnow().isoformat()
        }

        file_path = report_dir / f"report_{timestamp}.json"
        file_path.write_text(json.dumps(report_json, indent=2, default=str))

        return str(file_path)

    # Helper methods for data analysis and formatting

    def _determine_period(
        self,
        report_type: ReportType,
        start: Optional[datetime],
        end: Optional[datetime]
    ) -> tuple[datetime, datetime]:
        """Determine report period based on type"""
        if start and end:
            return start, end

        now = datetime.utcnow()

        if report_type == ReportType.DAILY:
            start = now - timedelta(days=1)
        elif report_type == ReportType.WEEKLY:
            start = now - timedelta(weeks=1)
        elif report_type == ReportType.MONTHLY:
            start = now - timedelta(days=30)
        elif report_type == ReportType.QUARTERLY:
            start = now - timedelta(days=90)
        elif report_type == ReportType.ANNUAL:
            start = now - timedelta(days=365)
        else:
            start = now - timedelta(days=7)  # Default to week

        return start, now

    async def _get_period_memories(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> list[Memory]:
        """Get memories from a specific period"""
        query = select(Memory).where(
            and_(
                Memory.user_id == user_id,
                Memory.created_at >= start,
                Memory.created_at <= end,
                Memory.deleted_at.is_(None)
            )
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _analyze_patterns(self, memories: list[Memory]) -> list[dict[str, Any]]:
        """Analyze patterns in memories"""
        patterns = []

        # Time-based patterns
        hour_counts = {}
        for memory in memories:
            hour = memory.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
        patterns.append({
            "type": "temporal",
            "pattern": f"Peak activity at {peak_hour}:00",
            "strength": 0.8
        })

        # Topic patterns (simplified)
        topic_counts = {}
        for memory in memories:
            if memory.metadata and "topic" in memory.metadata:
                topic = memory.metadata["topic"]
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        if topic_counts:
            top_topic = max(topic_counts.items(), key=lambda x: x[1])[0]
            patterns.append({
                "type": "topical",
                "pattern": f"Focus on {top_topic}",
                "strength": 0.7
            })

        return patterns

    async def _identify_emerging_topics(
        self,
        memories: list[Memory],
        period_start: datetime
    ) -> list[dict[str, Any]]:
        """Identify emerging topics"""
        # Simplified implementation
        recent_topics = {}
        midpoint = period_start + (datetime.utcnow() - period_start) / 2

        for memory in memories:
            if memory.created_at > midpoint and memory.metadata and "topic" in memory.metadata:
                topic = memory.metadata["topic"]
                recent_topics[topic] = recent_topics.get(topic, 0) + 1

        emerging = [
            {
                "topic": topic,
                "growth_rate": count / max(len(memories), 1),
                "mention_count": count
            }
            for topic, count in sorted(recent_topics.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return emerging

    async def _identify_knowledge_gaps(
        self,
        user_id: str,
        memories: list[Memory]
    ) -> list[dict[str, Any]]:
        """Identify knowledge gaps"""
        # Simplified implementation
        gaps = []

        # Check for topics with few memories
        topic_counts = {}
        for memory in memories:
            if memory.metadata and "topic" in memory.metadata:
                topic = memory.metadata["topic"]
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        for topic, count in topic_counts.items():
            if count < 3:
                gaps.append({
                    "area": topic,
                    "type": "insufficient_depth",
                    "current_count": count,
                    "recommended_count": 10,
                    "priority": 0.7
                })

        return gaps[:5]  # Top 5 gaps

    def _count_by_type(self, memories: list[Memory]) -> dict[str, int]:
        """Count memories by type"""
        type_counts = {}
        for memory in memories:
            memory_type = memory.memory_type or "unknown"
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1
        return type_counts

    async def _count_reviewed_memories(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> int:
        """Count memories reviewed in period"""
        query = select(func.count(Memory.id)).where(
            and_(
                Memory.user_id == user_id,
                Memory.last_accessed >= start,
                Memory.last_accessed <= end
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _count_new_connections(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> int:
        """Count new connections made in period"""
        # Simplified - would query relationship table in real implementation
        return 42  # Placeholder

    async def _calculate_retention_score(
        self,
        user_id: str,
        memories: list[Memory]
    ) -> float:
        """Calculate knowledge retention score"""
        if not memories:
            return 0.0

        # Simple calculation based on access patterns
        accessed_count = sum(1 for m in memories if m.last_accessed)
        return min(accessed_count / len(memories), 1.0)

    async def _calculate_topic_mastery(
        self,
        user_id: str,
        memories: list[Memory]
    ) -> dict[str, float]:
        """Calculate mastery level for topics"""
        topic_scores = {}
        topic_counts = {}

        for memory in memories:
            if memory.metadata and "topic" in memory.metadata:
                topic = memory.metadata["topic"]
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

                # Simple mastery calculation
                score = min(topic_counts[topic] / 10, 1.0) * memory.importance
                topic_scores[topic] = max(topic_scores.get(topic, 0), score)

        return dict(sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:10])

    async def _calculate_streaks(
        self,
        user_id: str,
        end_date: datetime
    ) -> dict[str, int]:
        """Calculate activity streaks"""
        # Simplified implementation
        return {
            "current_streak": 7,
            "longest_streak": 14,
            "weekly_streak": 3
        }

    def _create_default_templates(self, template_dir: Path):
        """Create default report templates"""
        # Basic HTML template
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        h1 { color: #1f77b4; }
        h2 { color: #333; margin-top: 30px; }
        .section { margin-bottom: 30px; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; color: #1f77b4; }
        .metric-label { font-size: 14px; color: #666; }
        ul { list-style-type: disc; margin-left: 20px; }
        .chart { margin: 20px 0; }
        .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p><em>Generated on {{ generated_at }}</em></p>

    <div class="section">
        <h2>Executive Summary</h2>
        <p>{{ executive_summary }}</p>
    </div>

    {% for section in sections %}
    <div class="section">
        <h2>{{ section.title }}</h2>
        {{ section.content | safe }}

        {% if section.visualizations %}
        <div class="chart">
            <!-- Visualization placeholder -->
        </div>
        {% endif %}
    </div>
    {% endfor %}

    <div class="footer">
        <p>This report was automatically generated by Second Brain v2.8.2</p>
    </div>
</body>
</html>
        """

        (template_dir / "report_template.html").write_text(html_template)

    # Formatting helper methods

    def _format_patterns(self, patterns: list[dict[str, Any]]) -> str:
        """Format patterns for display"""
        lines = []
        for pattern in patterns:
            lines.append(f"- **{pattern['pattern']}** (Strength: {pattern['strength']:.0%})")
        return "\n".join(lines)

    def _format_emerging_topics(self, topics: list[dict[str, Any]]) -> str:
        """Format emerging topics"""
        lines = ["The following topics are gaining momentum:\n"]
        for topic in topics:
            lines.append(f"- **{topic['topic']}**: {topic['mention_count']} mentions (Growth: {topic['growth_rate']:.0%})")
        return "\n".join(lines)

    def _format_knowledge_gaps(self, gaps: list[dict[str, Any]]) -> str:
        """Format knowledge gaps"""
        lines = ["Areas that could benefit from more exploration:\n"]
        for gap in gaps:
            lines.append(f"- **{gap['area']}**: Currently {gap['current_count']} memories (Recommended: {gap['recommended_count']})")
        return "\n".join(lines)

    def _format_growth_metrics(self, memory_growth: dict, connection_growth: dict) -> str:
        """Format growth metrics"""
        return f"""
### Memory Growth
- Total new memories: **{memory_growth.get('total', 0)}**
- Daily average: **{memory_growth.get('daily_average', 0):.1f}**
- By type: {', '.join(f"{k}: {v}" for k, v in memory_growth.get('by_type', {}).items())}

### Connection Growth
- Graph density: **{connection_growth.get('density', 0):.1%}**
- Clustering coefficient: **{connection_growth.get('clustering', 0):.2f}**
        """

    def _format_recommendations(self, recommendations: list[str]) -> str:
        """Format recommendations"""
        lines = ["Based on the analysis, we recommend:\n"]
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        return "\n".join(lines)

    def _create_growth_chart_data(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Create growth chart visualization data"""
        return {
            "type": "line",
            "title": "Knowledge Growth Trend",
            "data": {
                "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
                "datasets": [{
                    "label": "Memories",
                    "data": [10, 25, 40, 55],  # Placeholder data
                    "borderColor": "#1f77b4"
                }]
            }
        }

    # Additional helper methods for other report types...

    async def _analyze_knowledge_domains(self, user_id: str) -> list[dict[str, Any]]:
        """Analyze knowledge domains"""
        # Simplified implementation
        return [
            {"name": "Technology", "size": 234, "coverage": 0.8, "connections": 145},
            {"name": "Science", "size": 156, "coverage": 0.6, "connections": 89},
            {"name": "Business", "size": 98, "coverage": 0.4, "connections": 56}
        ]

    async def _identify_topic_clusters(self, user_id: str) -> list[dict[str, Any]]:
        """Identify topic clusters"""
        return [
            {"name": "Machine Learning", "size": 45, "density": 0.7, "connections": 5},
            {"name": "Web Development", "size": 38, "density": 0.6, "connections": 4}
        ]

    async def _find_bridge_connections(self, user_id: str) -> list[dict[str, Any]]:
        """Find bridge connections between domains"""
        return [
            {"from": "Technology", "to": "Business", "strength": 0.6, "count": 12}
        ]

    async def _find_bridge_opportunities(
        self,
        domains: list[dict[str, Any]],
        clusters: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find opportunities for new bridges"""
        return [
            {"from": "Science", "to": "Technology", "potential": 0.8, "reason": "Many overlapping concepts"}
        ]

    async def _generate_graph_visualization_data(self, user_id: str) -> dict[str, Any]:
        """Generate graph visualization data"""
        return {
            "type": "force-directed-graph",
            "nodes": [
                {"id": "1", "label": "ML", "group": 1, "size": 20},
                {"id": "2", "label": "AI", "group": 1, "size": 15}
            ],
            "edges": [
                {"source": "1", "target": "2", "weight": 0.8}
            ]
        }

    def _format_progress_overview(self, data: dict[str, Any]) -> str:
        """Format progress overview section"""
        return f"""
You've made significant progress in your learning journey:

- Created **{data.get('memories_created', 0)}** new memories
- Established **{data.get('connections_made', 0)}** knowledge connections
- Explored **{data.get('topics_explored', 0)}** different topics
- Reviewed **{data.get('memories_reviewed', 0)}** existing memories

Your learning velocity is **{data.get('learning_velocity', 0):.1f}** memories per day.
        """

    def _format_learning_metrics(self, data: dict[str, Any]) -> str:
        """Format learning metrics section"""
        retention = data.get('knowledge_retention_score', 0)
        return f"""
### Knowledge Retention
Your retention score is **{retention:.0%}**, indicating {'excellent' if retention > 0.8 else 'good' if retention > 0.6 else 'room for improvement in'} knowledge retention.

### Topic Mastery
Your top areas of expertise:
{chr(10).join(f"- **{topic}**: {score:.0%} mastery" for topic, score in list(data.get('topic_mastery', {}).items())[:5])}
        """

    def _format_achievements(self, milestones: list[str], streaks: dict[str, int]) -> str:
        """Format achievements section"""
        lines = ["### Milestones Reached\n"]
        for milestone in milestones:
            lines.append(f"🏆 {milestone}")

        lines.append("\n### Activity Streaks\n")
        if streaks:
            lines.append(f"- Current streak: **{streaks.get('current_streak', 0)}** days")
            lines.append(f"- Longest streak: **{streaks.get('longest_streak', 0)}** days")

        return "\n".join(lines)

    def _create_retention_chart_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create retention chart data"""
        return {
            "type": "gauge",
            "title": "Knowledge Retention Score",
            "value": data.get('knowledge_retention_score', 0) * 100,
            "max": 100,
            "thresholds": [60, 80, 90]
        }

    def _format_domain_analysis(
        self,
        domains: list[dict[str, Any]],
        coverage: dict[str, float]
    ) -> str:
        """Format domain analysis section"""
        lines = ["Your knowledge spans across multiple domains:\n"]

        for domain in domains[:5]:
            lines.append(f"### {domain['name']}")
            lines.append(f"- Size: **{domain['size']}** memories")
            lines.append(f"- Coverage: **{domain['coverage']:.0%}**")
            lines.append(f"- Internal connections: **{domain['connections']}**\n")

        return "\n".join(lines)

    def _create_domain_chart_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create domain chart visualization"""
        domains = data.get('domains', [])
        return {
            "type": "treemap",
            "title": "Knowledge Domain Distribution",
            "data": [
                {
                    "name": d['name'],
                    "value": d['size'],
                    "color": f"hsl({i * 60}, 70%, 50%)"
                }
                for i, d in enumerate(domains[:10])
            ]
        }
