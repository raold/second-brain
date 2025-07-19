#!/usr/bin/env python3
"""
Project Pipeline Dashboard - Live Updating Project Management System
Real-time visual tracking of goals, sprints, testing, logging, and architectural progress

Features:
- Live project metrics and KPI tracking
- Visual timeseries data and progress charts
- Automatic goal/timeline updates based on context
- Sprint management and milestone tracking
- Testing coverage and performance metrics
- Architectural decision tracking
- CTO-level strategic overview
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.docs import Priority


class ProjectPhase(Enum):
    """Project development phases"""

    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"


# Priority enum moved to app.docs for centralized definition


class Status(Enum):
    """Task/milestone status"""

    PLANNING = "planning"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class Milestone:
    """Project milestone tracking"""

    id: str
    name: str
    description: str
    target_date: str
    completion_date: Optional[str]
    status: Status
    progress: float  # 0.0 to 1.0
    dependencies: list[str]
    created_at: str


@dataclass
class Task:
    """Individual task tracking"""

    id: str
    name: str
    description: str
    assignee: str
    priority: Priority
    status: Status
    estimated_hours: int
    actual_hours: int
    milestone_id: str
    created_at: str
    completed_at: Optional[str]
    tags: list[str]


@dataclass
class Sprint:
    """Sprint management"""

    id: str
    name: str
    start_date: str
    end_date: str
    goals: list[str]
    tasks: list[str]  # Task IDs
    status: Status
    velocity: float
    burn_down_data: list[tuple[str, int]]  # (date, remaining_points)


@dataclass
class TechnicalMetric:
    """Technical performance metrics"""

    timestamp: str
    metric_name: str
    value: float
    unit: str
    target: Optional[float]
    status: str  # "on_track", "warning", "critical"


@dataclass
class ArchitecturalDecision:
    """ADR (Architectural Decision Record) tracking"""

    id: str
    title: str
    status: str  # "proposed", "accepted", "superseded"
    context: str
    decision: str
    consequences: list[str]
    created_at: str
    updated_at: str


class ProjectDashboard:
    """
    Comprehensive project dashboard for live tracking and CTO oversight
    """

    def __init__(self, project_name: str = "Project Pipeline"):
        self.project_name = project_name
        self.dashboard_dir = Path("dashboard_data")
        self.dashboard_dir.mkdir(exist_ok=True)

        # Data storage
        self.milestones: dict[str, Milestone] = {}
        self.tasks: dict[str, Task] = {}
        self.sprints: dict[str, Sprint] = {}
        self.metrics: list[TechnicalMetric] = []
        self.adrs: dict[str, ArchitecturalDecision] = {}

        # Load existing data
        self.load_dashboard_data()

        # Initialize project if empty
        if not self.milestones:
            self.initialize_project_pipeline()

    def initialize_project_pipeline(self):
        """Initialize Project Pipeline with baseline milestones and structure"""
        print("🚀 Initializing Project Pipeline Dashboard...")

        # Phase 1: Pipeline Foundation
        milestone_1 = Milestone(
            id="milestone_pipeline_foundation",
            name="Pipeline Foundation",
            description="Core pipeline engine and processing framework",
            target_date=(datetime.now() + timedelta(weeks=1)).isoformat(),
            completion_date=None,
            status=Status.IN_PROGRESS,
            progress=0.2,
            dependencies=[],
            created_at=datetime.now().isoformat(),
        )

        # Phase 2: Batch Operations
        milestone_2 = Milestone(
            id="milestone_batch_operations",
            name="Batch Operations",
            description="Bulk memory operations and migration tools",
            target_date=(datetime.now() + timedelta(weeks=2)).isoformat(),
            completion_date=None,
            status=Status.NOT_STARTED,
            progress=0.0,
            dependencies=["milestone_pipeline_foundation"],
            created_at=datetime.now().isoformat(),
        )

        # Phase 3: Analytics Engine
        milestone_3 = Milestone(
            id="milestone_analytics_engine",
            name="Analytics Engine",
            description="Memory analytics and insights generation",
            target_date=(datetime.now() + timedelta(weeks=3)).isoformat(),
            completion_date=None,
            status=Status.NOT_STARTED,
            progress=0.0,
            dependencies=["milestone_batch_operations"],
            created_at=datetime.now().isoformat(),
        )

        # Phase 4: Workflow Automation
        milestone_4 = Milestone(
            id="milestone_workflow_automation",
            name="Workflow Automation",
            description="Rule-based automation and scheduling",
            target_date=(datetime.now() + timedelta(weeks=4)).isoformat(),
            completion_date=None,
            status=Status.NOT_STARTED,
            progress=0.0,
            dependencies=["milestone_analytics_engine"],
            created_at=datetime.now().isoformat(),
        )

        self.milestones = {
            milestone_1.id: milestone_1,
            milestone_2.id: milestone_2,
            milestone_3.id: milestone_3,
            milestone_4.id: milestone_4,
        }

        # Initial sprint
        current_sprint = Sprint(
            id="sprint_001",
            name="Sprint 1: Pipeline Foundation",
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(weeks=1)).isoformat(),
            goals=[
                "Implement pipeline engine architecture",
                "Create memory processing queue",
                "Add error handling and logging",
                "Develop unit tests",
            ],
            tasks=[],
            status=Status.IN_PROGRESS,
            velocity=0.0,
            burn_down_data=[],
        )

        self.sprints = {current_sprint.id: current_sprint}

        # Initial tasks for Phase 1
        self.create_initial_tasks()

        # Baseline metrics
        self.record_baseline_metrics()

        self.save_dashboard_data()
        print("✅ Project Pipeline Dashboard initialized")

    def create_initial_tasks(self):
        """Create initial tasks for pipeline foundation"""
        initial_tasks = [
            {
                "name": "Design Pipeline Engine Architecture",
                "description": "Create core pipeline processing framework design",
                "assignee": "Principal Engineer",
                "priority": Priority.CRITICAL,
                "estimated_hours": 8,
                "milestone_id": "milestone_pipeline_foundation",
                "tags": ["architecture", "design"],
            },
            {
                "name": "Implement Memory Processing Queue",
                "description": "Build asynchronous memory processing queue system",
                "assignee": "Principal Engineer",
                "priority": Priority.HIGH,
                "estimated_hours": 12,
                "milestone_id": "milestone_pipeline_foundation",
                "tags": ["implementation", "queue"],
            },
            {
                "name": "Add Pipeline Error Handling",
                "description": "Comprehensive error handling and retry logic",
                "assignee": "Principal Engineer",
                "priority": Priority.HIGH,
                "estimated_hours": 6,
                "milestone_id": "milestone_pipeline_foundation",
                "tags": ["error-handling", "reliability"],
            },
            {
                "name": "Create Pipeline Unit Tests",
                "description": "Unit test suite for pipeline components",
                "assignee": "Principal Engineer",
                "priority": Priority.MEDIUM,
                "estimated_hours": 8,
                "milestone_id": "milestone_pipeline_foundation",
                "tags": ["testing", "quality"],
            },
        ]

        for task_data in initial_tasks:
            task = Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                name=task_data["name"],
                description=task_data["description"],
                assignee=task_data["assignee"],
                priority=task_data["priority"],
                status=Status.NOT_STARTED,
                estimated_hours=task_data["estimated_hours"],
                actual_hours=0,
                milestone_id=task_data["milestone_id"],
                created_at=datetime.now().isoformat(),
                completed_at=None,
                tags=task_data["tags"],
            )
            self.tasks[task.id] = task

    def record_baseline_metrics(self):
        """Record baseline technical metrics"""
        baseline_metrics = [
            TechnicalMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="pipeline_throughput",
                value=0.0,
                unit="memories/minute",
                target=1000.0,
                status="not_started",
            ),
            TechnicalMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="analytics_accuracy",
                value=0.0,
                unit="percentage",
                target=95.0,
                status="not_started",
            ),
            TechnicalMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="automation_efficiency",
                value=0.0,
                unit="percentage",
                target=80.0,
                status="not_started",
            ),
            TechnicalMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="performance_overhead",
                value=0.0,
                unit="percentage",
                target=10.0,
                status="on_track",
            ),
        ]

        self.metrics.extend(baseline_metrics)

    def add_new_feature_context(self, feature_name: str, description: str, priority: Priority = Priority.HIGH):
        """
        Automatically add new feature/goal based on conversation context
        This method is called when CTO discusses new architectural features
        """
        print(f"🎯 Adding new feature context: {feature_name}")

        # Create new milestone for the feature
        feature_milestone = Milestone(
            id=f"milestone_{feature_name.lower().replace(' ', '_')}",
            name=feature_name,
            description=description,
            target_date=(datetime.now() + timedelta(weeks=2)).isoformat(),
            completion_date=None,
            status=Status.PLANNING,
            progress=0.0,
            dependencies=[],
            created_at=datetime.now().isoformat(),
        )

        self.milestones[feature_milestone.id] = feature_milestone

        # Create planning tasks
        planning_tasks = [
            {
                "name": f"Architecture Design - {feature_name}",
                "description": f"Design architecture for {feature_name} implementation",
                "estimated_hours": 6,
                "tags": ["architecture", "planning"],
            },
            {
                "name": f"Technical Specification - {feature_name}",
                "description": f"Create detailed technical specification for {feature_name}",
                "estimated_hours": 4,
                "tags": ["specification", "documentation"],
            },
            {
                "name": f"Implementation Plan - {feature_name}",
                "description": f"Break down implementation phases for {feature_name}",
                "estimated_hours": 3,
                "tags": ["planning", "roadmap"],
            },
        ]

        for task_data in planning_tasks:
            task = Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                name=task_data["name"],
                description=task_data["description"],
                assignee="Principal Engineer",
                priority=priority,
                status=Status.NOT_STARTED,
                estimated_hours=task_data["estimated_hours"],
                actual_hours=0,
                milestone_id=feature_milestone.id,
                created_at=datetime.now().isoformat(),
                completed_at=None,
                tags=task_data["tags"],
            )
            self.tasks[task.id] = task

        # Update project timeline
        self.update_project_timeline()

        # Save updated data
        self.save_dashboard_data()

        print(f"✅ Added {feature_name} to project roadmap with {len(planning_tasks)} planning tasks")
        return feature_milestone.id

    def update_project_timeline(self):
        """Recalculate project timeline based on current milestones and dependencies"""
        # Sort milestones by dependencies
        sorted_milestones = self.topological_sort_milestones()

        current_date = datetime.now()
        for milestone_id in sorted_milestones:
            milestone = self.milestones[milestone_id]

            # Calculate estimated completion based on tasks
            milestone_tasks = [t for t in self.tasks.values() if t.milestone_id == milestone_id]
            total_estimated_hours = sum(t.estimated_hours for t in milestone_tasks)

            # Assume 8 hours per day, 5 days per week
            estimated_days = (total_estimated_hours / 8) * 1.2  # 20% buffer

            milestone.target_date = (current_date + timedelta(days=estimated_days)).isoformat()
            current_date += timedelta(days=estimated_days)

    def topological_sort_milestones(self) -> list[str]:
        """Sort milestones by dependency order"""
        visited = set()
        temp_visited = set()
        result = []

        def visit(milestone_id: str):
            if milestone_id in temp_visited:
                return  # Circular dependency - skip
            if milestone_id in visited:
                return

            temp_visited.add(milestone_id)
            milestone = self.milestones[milestone_id]

            for dep in milestone.dependencies:
                if dep in self.milestones:
                    visit(dep)

            temp_visited.remove(milestone_id)
            visited.add(milestone_id)
            result.append(milestone_id)

        for milestone_id in self.milestones:
            if milestone_id not in visited:
                visit(milestone_id)

        return result

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Generate comprehensive dashboard summary for CTO overview"""
        # Calculate overall project health
        total_milestones = len(self.milestones)
        completed_milestones = sum(1 for m in self.milestones.values() if m.status == Status.COMPLETED)
        overall_progress = completed_milestones / total_milestones if total_milestones > 0 else 0

        # Calculate sprint velocity
        current_sprint = self.get_current_sprint()
        sprint_progress = self.calculate_sprint_progress(current_sprint.id) if current_sprint else 0

        # Technical metrics summary
        latest_metrics = self.get_latest_metrics()

        # Risk assessment
        risks = self.assess_project_risks()

        return {
            "project_name": self.project_name,
            "last_updated": datetime.now().isoformat(),
            "overall_health": {
                "progress": overall_progress,
                "status": self.get_project_status(),
                "milestones_completed": f"{completed_milestones}/{total_milestones}",
                "sprint_progress": sprint_progress,
            },
            "current_sprint": {
                "name": current_sprint.name if current_sprint else "No active sprint",
                "progress": sprint_progress,
                "days_remaining": self.get_sprint_days_remaining(current_sprint.id) if current_sprint else 0,
            },
            "technical_metrics": latest_metrics,
            "risks": risks,
            "upcoming_milestones": self.get_upcoming_milestones(limit=3),
            "recent_completions": self.get_recent_completions(limit=5),
        }

    def get_project_status(self) -> str:
        """Determine overall project health status"""
        risks = self.assess_project_risks()
        high_risks = [r for r in risks if r["level"] == "high"]

        if high_risks:
            return "at_risk"

        # Check if milestones are on track
        overdue_milestones = [
            m
            for m in self.milestones.values()
            if m.status != Status.COMPLETED and datetime.fromisoformat(m.target_date) < datetime.now()
        ]

        if overdue_milestones:
            return "behind_schedule"

        return "on_track"

    def assess_project_risks(self) -> list[dict[str, Any]]:
        """Assess current project risks for CTO awareness"""
        risks = []

        # Check for overdue milestones
        overdue_milestones = [
            m
            for m in self.milestones.values()
            if m.status != Status.COMPLETED and datetime.fromisoformat(m.target_date) < datetime.now()
        ]

        for milestone in overdue_milestones:
            risks.append(
                {
                    "type": "schedule",
                    "level": "high",
                    "description": f"Milestone '{milestone.name}' is overdue",
                    "impact": "Project timeline delay",
                    "mitigation": "Reassess scope and resources",
                }
            )

        # Check for blocked tasks
        blocked_tasks = [t for t in self.tasks.values() if t.status == Status.BLOCKED]
        if blocked_tasks:
            risks.append(
                {
                    "type": "blocking",
                    "level": "medium",
                    "description": f"{len(blocked_tasks)} tasks are blocked",
                    "impact": "Development velocity reduction",
                    "mitigation": "Resolve blocking dependencies",
                }
            )

        # Check technical metrics
        latest_metrics = self.get_latest_metrics()
        for metric in latest_metrics:
            if metric["status"] == "critical":
                risks.append(
                    {
                        "type": "technical",
                        "level": "high",
                        "description": f"{metric['name']} is in critical state",
                        "impact": "Performance/quality degradation",
                        "mitigation": "Immediate technical review required",
                    }
                )

        return risks

    def get_current_sprint(self) -> Optional[Sprint]:
        """Get currently active sprint"""
        now = datetime.now()
        for sprint in self.sprints.values():
            start = datetime.fromisoformat(sprint.start_date)
            end = datetime.fromisoformat(sprint.end_date)
            if start <= now <= end and sprint.status == Status.IN_PROGRESS:
                return sprint
        return None

    def calculate_sprint_progress(self, sprint_id: str) -> float:
        """Calculate sprint completion progress"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return 0.0

        sprint_tasks = [t for t in self.tasks.values() if t.id in sprint.tasks]
        if not sprint_tasks:
            return 0.0

        completed_tasks = sum(1 for t in sprint_tasks if t.status == Status.COMPLETED)
        return completed_tasks / len(sprint_tasks)

    def get_sprint_days_remaining(self, sprint_id: str) -> int:
        """Get days remaining in sprint"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return 0

        end_date = datetime.fromisoformat(sprint.end_date)
        remaining = end_date - datetime.now()
        return max(0, remaining.days)

    def get_latest_metrics(self) -> list[dict[str, Any]]:
        """Get latest technical metrics with status"""
        metrics_by_name = {}

        # Get most recent metric for each type
        for metric in sorted(self.metrics, key=lambda x: x.timestamp, reverse=True):
            if metric.metric_name not in metrics_by_name:
                metrics_by_name[metric.metric_name] = {
                    "name": metric.metric_name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "target": metric.target,
                    "status": metric.status,
                    "timestamp": metric.timestamp,
                }

        return list(metrics_by_name.values())

    def get_upcoming_milestones(self, limit: int = 3) -> list[dict[str, Any]]:
        """Get upcoming milestones"""
        upcoming = [
            m
            for m in self.milestones.values()
            if m.status != Status.COMPLETED and datetime.fromisoformat(m.target_date) >= datetime.now()
        ]

        upcoming.sort(key=lambda x: x.target_date)

        return [
            {
                "name": m.name,
                "target_date": m.target_date,
                "progress": m.progress,
                "status": m.status.value if hasattr(m.status, "value") else m.status,
            }
            for m in upcoming[:limit]
        ]

    def get_recent_completions(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recently completed tasks/milestones"""
        completed_tasks = [t for t in self.tasks.values() if t.status == Status.COMPLETED and t.completed_at]

        completed_tasks.sort(key=lambda x: x.completed_at or "", reverse=True)

        return [
            {
                "name": t.name,
                "type": "task",
                "completed_at": t.completed_at,
                "milestone": self.milestones[t.milestone_id].name if t.milestone_id in self.milestones else "Unknown",
            }
            for t in completed_tasks[:limit]
        ]

    def record_metric(self, metric_name: str, value: float, unit: str, target: Optional[float] = None):
        """Record a new technical metric"""
        # Determine status based on target
        status = "on_track"
        if target:
            if metric_name in ["pipeline_throughput", "analytics_accuracy", "automation_efficiency"]:
                # Higher is better
                if value < target * 0.5:
                    status = "critical"
                elif value < target * 0.8:
                    status = "warning"
            else:
                # Lower is better (e.g., performance_overhead)
                if value > target * 2:
                    status = "critical"
                elif value > target * 1.5:
                    status = "warning"

        metric = TechnicalMetric(
            timestamp=datetime.now().isoformat(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            target=target,
            status=status,
        )

        self.metrics.append(metric)
        self.save_dashboard_data()

    def save_dashboard_data(self):
        """Save dashboard data to persistent storage"""
        data = {
            "milestones": {k: asdict(v) for k, v in self.milestones.items()},
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "sprints": {k: asdict(v) for k, v in self.sprints.items()},
            "metrics": [asdict(m) for m in self.metrics],
            "adrs": {k: asdict(v) for k, v in self.adrs.items()},
        }

        dashboard_file = self.dashboard_dir / "dashboard_data.json"
        with open(dashboard_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_dashboard_data(self):
        """Load dashboard data from persistent storage"""
        dashboard_file = self.dashboard_dir / "dashboard_data.json"

        if not dashboard_file.exists():
            return

        try:
            with open(dashboard_file) as f:
                data = json.load(f)

            # Load milestones with proper status conversion
            if "milestones" in data:
                self.milestones = {}
                for k, v in data["milestones"].items():
                    # Convert string status to Status enum if needed
                    if "status" in v and isinstance(v["status"], str):
                        try:
                            v["status"] = Status(v["status"])
                        except ValueError:
                            v["status"] = Status.NOT_STARTED  # Default fallback
                    self.milestones[k] = Milestone(**v)

            # Load tasks
            if "tasks" in data:
                self.tasks = {
                    k: Task(**{**v, "priority": Priority(v["priority"]), "status": Status(v["status"])})
                    for k, v in data["tasks"].items()
                }

            # Load sprints
            if "sprints" in data:
                self.sprints = {k: Sprint(**{**v, "status": Status(v["status"])}) for k, v in data["sprints"].items()}

            # Load metrics
            if "metrics" in data:
                self.metrics = [TechnicalMetric(**m) for m in data["metrics"]]

            # Load ADRs
            if "adrs" in data:
                self.adrs = {k: ArchitecturalDecision(**v) for k, v in data["adrs"].items()}

        except Exception as e:
            print(f"⚠️ Error loading dashboard data: {e}")

    def generate_visual_report(self) -> str:
        """Generate visual dashboard report for CTO overview"""
        summary = self.get_dashboard_summary()

        report = f"""
🎯 PROJECT PIPELINE DASHBOARD - CTO OVERVIEW
============================================

📊 PROJECT HEALTH: {summary['overall_health']['status'].upper()}
📈 Overall Progress: {summary['overall_health']['progress']:.1%}
🚀 Milestones: {summary['overall_health']['milestones_completed']}

🏃‍♂️ CURRENT SPRINT: {summary['current_sprint']['name']}
📅 Sprint Progress: {summary['current_sprint']['progress']:.1%}
⏰ Days Remaining: {summary['current_sprint']['days_remaining']}

📈 TECHNICAL METRICS:
"""

        for metric in summary["technical_metrics"]:
            status_emoji = {"on_track": "✅", "warning": "⚠️", "critical": "❌"}.get(metric["status"], "❓")
            target_info = f" (Target: {metric['target']}{metric['unit']})" if metric["target"] else ""
            report += f"   {status_emoji} {metric['name']}: {metric['value']}{metric['unit']}{target_info}\n"

        report += f"\n⚠️ RISKS ({len(summary['risks'])}):\n"
        for risk in summary["risks"]:
            level_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk["level"], "❓")
            report += f"   {level_emoji} {risk['description']}\n"

        report += "\n🎯 UPCOMING MILESTONES:\n"
        for milestone in summary["upcoming_milestones"]:
            target_date = datetime.fromisoformat(milestone["target_date"]).strftime("%m/%d")
            report += f"   📅 {milestone['name']} - {target_date} ({milestone['progress']:.0%})\n"

        if summary["recent_completions"]:
            report += "\n✅ RECENT COMPLETIONS:\n"
            for completion in summary["recent_completions"]:
                completed_date = datetime.fromisoformat(completion["completed_at"]).strftime("%m/%d")
                report += f"   ✅ {completion['name']} - {completed_date}\n"

        report += f"\n📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"

        return report


# Global dashboard instance
_dashboard_instance = None


def get_dashboard() -> ProjectDashboard:
    """Get or create global dashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = ProjectDashboard()
    return _dashboard_instance


def update_dashboard_for_feature(feature_name: str, description: str = "") -> str:
    """
    Automatically update dashboard when CTO discusses new features
    Returns updated dashboard view
    """
    dashboard = get_dashboard()
    milestone_id = dashboard.add_new_feature_context(feature_name, description)

    # Generate updated visual report
    return dashboard.generate_visual_report()


def get_dashboard_summary() -> str:
    """Get current dashboard summary for CTO"""
    dashboard = get_dashboard()
    return dashboard.generate_visual_report()


if __name__ == "__main__":
    # Demo dashboard initialization
    dashboard = ProjectDashboard()
    print(dashboard.generate_visual_report())
