"""
Bulk Operations Monitoring and Analytics System

Provides comprehensive monitoring, analytics, and business intelligence for bulk operations:
- Real-time operation tracking and dashboards
- Advanced performance analytics and reporting
- Predictive performance modeling
- Business intelligence and insights
- Automated alerting and notifications
- Historical trend analysis
- Cost and efficiency optimization analytics
"""

import asyncio
import logging
import statistics
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .bulk_memory_operations import BulkOperationProgress, BulkOperationResult, BulkOperationStatus, BulkOperationType

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AnalyticsTimeframe(Enum):
    """Timeframes for analytics reporting."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class MetricPoint:
    """Individual metric data point."""

    timestamp: datetime
    metric_name: str
    metric_type: MetricType
    value: float
    tags: dict[str, str]
    operation_id: str | None = None


@dataclass
class Alert:
    """Alert definition and state."""

    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    threshold: float
    triggered_at: datetime | None = None
    resolved_at: datetime | None = None
    is_active: bool = False
    trigger_count: int = 0


@dataclass
class OperationInsight:
    """Business intelligence insight for operations."""

    insight_id: str
    operation_type: BulkOperationType
    insight_type: str  # efficiency, cost, performance, quality
    title: str
    description: str
    impact_score: float  # 0-1 scale
    recommendations: list[str]
    supporting_data: dict[str, Any]
    confidence: float  # 0-1 scale
    generated_at: datetime


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""

    metric_name: str
    timeframe: AnalyticsTimeframe
    trend_direction: str  # increasing, decreasing, stable
    change_percentage: float
    confidence_interval: tuple[float, float]
    seasonality_detected: bool
    anomalies: list[dict[str, Any]]


@dataclass
class CostAnalysis:
    """Cost analysis for bulk operations."""

    operation_type: BulkOperationType
    total_operations: int
    total_items_processed: int
    total_processing_time: float
    average_cost_per_item: float
    peak_resource_usage: dict[str, float]
    efficiency_score: float
    cost_trends: dict[str, float]


class MetricsCollector:
    """
    Advanced metrics collection system.

    Collects, aggregates, and stores metrics from bulk operations.
    """

    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.metrics_buffer = deque(maxlen=10000)
        self.aggregated_metrics = defaultdict(list)
        self.metric_definitions = {}
        self.collection_stats = {"total_points": 0, "buffer_overflows": 0, "last_aggregation": None}

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: dict[str, str] | None = None,
        operation_id: str | None = None,
    ):
        """Record a metric point."""
        metric_point = MetricPoint(
            timestamp=datetime.now(),
            metric_name=name,
            metric_type=metric_type,
            value=value,
            tags=tags or {},
            operation_id=operation_id,
        )

        self.metrics_buffer.append(metric_point)
        self.collection_stats["total_points"] += 1

        # Check for buffer overflow
        if len(self.metrics_buffer) >= 9900:
            await self._aggregate_metrics()

    async def _aggregate_metrics(self):
        """Aggregate buffered metrics for long-term storage."""
        if not self.metrics_buffer:
            return

        # Group metrics by name and hour
        hourly_groups = defaultdict(list)

        for metric in self.metrics_buffer:
            hour_key = metric.timestamp.replace(minute=0, second=0, microsecond=0)
            group_key = f"{metric.metric_name}_{hour_key.isoformat()}"
            hourly_groups[group_key].append(metric)

        # Aggregate each group
        for group_key, metrics in hourly_groups.items():
            if metrics[0].metric_type == MetricType.COUNTER:
                aggregated_value = sum(m.value for m in metrics)
            elif metrics[0].metric_type == MetricType.GAUGE:
                aggregated_value = metrics[-1].value  # Latest value
            elif metrics[0].metric_type == MetricType.TIMER:
                aggregated_value = statistics.mean(m.value for m in metrics)
            else:
                aggregated_value = statistics.mean(m.value for m in metrics)

            self.aggregated_metrics[metrics[0].metric_name].append(
                {
                    "timestamp": metrics[0].timestamp.replace(minute=0, second=0, microsecond=0),
                    "value": aggregated_value,
                    "count": len(metrics),
                    "min": min(m.value for m in metrics),
                    "max": max(m.value for m in metrics),
                    "std": statistics.stdev(m.value for m in metrics) if len(metrics) > 1 else 0,
                }
            )

        self.metrics_buffer.clear()
        self.collection_stats["last_aggregation"] = datetime.now()

    async def get_metrics(self, metric_name: str, start_time: datetime, end_time: datetime) -> list[dict[str, Any]]:
        """Retrieve metrics for a time range."""
        # Aggregate any remaining buffer
        await self._aggregate_metrics()

        if metric_name not in self.aggregated_metrics:
            return []

        return [
            metric for metric in self.aggregated_metrics[metric_name] if start_time <= metric["timestamp"] <= end_time
        ]

    async def get_latest_metrics(self, metric_names: list[str]) -> dict[str, Any]:
        """Get latest values for specified metrics."""
        latest = {}

        for metric_name in metric_names:
            # Check buffer first
            buffer_metrics = [m for m in self.metrics_buffer if m.metric_name == metric_name]
            if buffer_metrics:
                latest[metric_name] = buffer_metrics[-1].value
            elif metric_name in self.aggregated_metrics and self.aggregated_metrics[metric_name]:
                latest[metric_name] = self.aggregated_metrics[metric_name][-1]["value"]
            else:
                latest[metric_name] = None

        return latest


class OperationTracker:
    """
    Real-time operation tracking and status management.

    Tracks all bulk operations with detailed status and progress information.
    """

    def __init__(self):
        self.active_operations = {}
        self.completed_operations = deque(maxlen=1000)
        self.operation_history = defaultdict(list)
        self.tracking_stats = {"total_operations": 0, "active_count": 0, "completion_rate": 0.0}

    async def start_tracking(self, operation: BulkOperationProgress):
        """Start tracking a new operation."""
        self.active_operations[operation.operation_id] = operation
        self.tracking_stats["total_operations"] += 1
        self.tracking_stats["active_count"] = len(self.active_operations)

        logger.info(f"Started tracking operation: {operation.operation_id}")

    async def update_progress(self, operation_id: str, progress_update: dict[str, Any]):
        """Update operation progress."""
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]

            # Update progress fields
            for field, value in progress_update.items():
                if hasattr(operation, field):
                    setattr(operation, field, value)

            operation.last_update = datetime.now()

            # Calculate estimated completion time
            if operation.processed_items > 0 and operation.total_items > 0:
                elapsed = datetime.now() - operation.start_time
                rate = operation.processed_items / elapsed.total_seconds()
                remaining_items = operation.total_items - operation.processed_items

                if rate > 0:
                    remaining_seconds = remaining_items / rate
                    operation.estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)

    async def complete_operation(self, operation_id: str, result: BulkOperationResult):
        """Mark operation as completed and move to history."""
        if operation_id in self.active_operations:
            operation = self.active_operations.pop(operation_id)
            operation.status = result.status

            # Store in completed operations
            self.completed_operations.append({"operation": operation, "result": result, "completed_at": datetime.now()})

            # Update stats
            self.tracking_stats["active_count"] = len(self.active_operations)

            # Store in history by type
            self.operation_history[operation.operation_type].append(
                {
                    "operation_id": operation_id,
                    "status": result.status,
                    "total_items": result.total_items,
                    "execution_time": result.execution_time,
                    "completed_at": datetime.now(),
                }
            )

            logger.info(f"Completed tracking operation: {operation_id}")

    async def get_operation_status(self, operation_id: str) -> BulkOperationProgress | None:
        """Get current status of an operation."""
        return self.active_operations.get(operation_id)

    async def get_active_operations(self) -> list[BulkOperationProgress]:
        """Get all currently active operations."""
        return list(self.active_operations.values())

    async def get_operation_statistics(self) -> dict[str, Any]:
        """Get comprehensive operation statistics."""
        # Calculate completion rates by type
        completion_rates = {}
        for op_type, history in self.operation_history.items():
            if history:
                successful = sum(1 for op in history if op["status"] == BulkOperationStatus.COMPLETED)
                completion_rates[op_type.value] = successful / len(history)

        # Calculate average execution times
        avg_execution_times = {}
        for op_type, history in self.operation_history.items():
            if history:
                times = [op["execution_time"] for op in history if op["execution_time"] > 0]
                if times:
                    avg_execution_times[op_type.value] = statistics.mean(times)

        return {
            "tracking_stats": self.tracking_stats,
            "active_operations": len(self.active_operations),
            "completed_operations": len(self.completed_operations),
            "completion_rates": completion_rates,
            "average_execution_times": avg_execution_times,
            "operation_counts_by_type": {
                op_type.value: len(history) for op_type, history in self.operation_history.items()
            },
        }


class AlertManager:
    """
    Intelligent alerting system for bulk operations.

    Monitors metrics and operations for anomalies and issues.
    """

    def __init__(self):
        self.alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_channels = []
        self.alert_rules = {}
        self.suppression_rules = {}

    async def define_alert(
        self,
        name: str,
        description: str,
        condition: str,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> str:
        """Define a new alert rule."""
        alert_id = str(uuid.uuid4())

        alert = Alert(
            alert_id=alert_id,
            name=name,
            description=description,
            severity=severity,
            condition=condition,
            threshold=threshold,
        )

        self.alerts[alert_id] = alert
        logger.info(f"Defined alert: {name} (ID: {alert_id})")

        return alert_id

    async def check_alerts(self, metrics: dict[str, float], operation_data: dict[str, Any]):
        """Check all alert conditions against current metrics."""
        for alert_id, alert in self.alerts.items():
            should_trigger = await self._evaluate_alert_condition(alert, metrics, operation_data)

            if should_trigger and not alert.is_active:
                await self._trigger_alert(alert)
            elif not should_trigger and alert.is_active:
                await self._resolve_alert(alert)

    async def _evaluate_alert_condition(
        self, alert: Alert, metrics: dict[str, float], operation_data: dict[str, Any]
    ) -> bool:
        """Evaluate if alert condition is met."""
        try:
            # Simple condition evaluation (in production, would use a more robust parser)
            if "cpu_usage" in alert.condition:
                return metrics.get("cpu_usage", 0) > alert.threshold
            elif "memory_usage" in alert.condition:
                return metrics.get("memory_usage", 0) > alert.threshold
            elif "error_rate" in alert.condition:
                return metrics.get("error_rate", 0) > alert.threshold
            elif "response_time" in alert.condition:
                return metrics.get("response_time", 0) > alert.threshold
            elif "failed_operations" in alert.condition:
                return operation_data.get("failed_operations", 0) > alert.threshold

            return False

        except Exception as e:
            logger.error(f"Error evaluating alert condition {alert.alert_id}: {e}")
            return False

    async def _trigger_alert(self, alert: Alert):
        """Trigger an alert."""
        alert.is_active = True
        alert.triggered_at = datetime.now()
        alert.trigger_count += 1

        # Add to history
        self.alert_history.append(
            {
                "alert_id": alert.alert_id,
                "action": "triggered",
                "timestamp": datetime.now(),
                "severity": alert.severity.value,
            }
        )

        # Send notifications (simplified)
        await self._send_alert_notification(alert, "triggered")

        logger.warning(f"Alert triggered: {alert.name} (Severity: {alert.severity.value})")

    async def _resolve_alert(self, alert: Alert):
        """Resolve an active alert."""
        alert.is_active = False
        alert.resolved_at = datetime.now()

        # Add to history
        self.alert_history.append(
            {
                "alert_id": alert.alert_id,
                "action": "resolved",
                "timestamp": datetime.now(),
                "duration": (alert.resolved_at - alert.triggered_at).total_seconds() if alert.triggered_at else 0,
            }
        )

        # Send notifications (simplified)
        await self._send_alert_notification(alert, "resolved")

        logger.info(f"Alert resolved: {alert.name}")

    async def _send_alert_notification(self, alert: Alert, action: str):
        """Send alert notification (simplified implementation)."""
        # In production, would integrate with notification services
        notification = {
            "alert_name": alert.name,
            "action": action,
            "severity": alert.severity.value,
            "timestamp": datetime.now().isoformat(),
            "description": alert.description,
        }

        logger.info(f"Alert notification: {notification}")

    async def get_active_alerts(self) -> list[Alert]:
        """Get all currently active alerts."""
        return [alert for alert in self.alerts.values() if alert.is_active]

    async def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert system statistics."""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts.values() if a.is_active])

        # Count alerts by severity
        severity_counts = defaultdict(int)
        for alert in self.alerts.values():
            severity_counts[alert.severity.value] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "alert_history_count": len(self.alert_history),
            "alerts_by_severity": dict(severity_counts),
            "most_triggered_alerts": sorted(self.alerts.values(), key=lambda a: a.trigger_count, reverse=True)[:5],
        }


class AnalyticsEngine:
    """
    Advanced analytics engine for bulk operations.

    Provides business intelligence, trend analysis, and predictive insights.
    """

    def __init__(self, metrics_collector: MetricsCollector, operation_tracker: OperationTracker):
        self.metrics_collector = metrics_collector
        self.operation_tracker = operation_tracker
        self.insights_cache = {}
        self.trend_cache = {}
        self.prediction_models = {}

    async def analyze_performance_trends(
        self, timeframe: AnalyticsTimeframe = AnalyticsTimeframe.WEEK
    ) -> list[PerformanceTrend]:
        """Analyze performance trends over specified timeframe."""
        end_time = datetime.now()

        if timeframe == AnalyticsTimeframe.HOUR:
            start_time = end_time - timedelta(hours=1)
        elif timeframe == AnalyticsTimeframe.DAY:
            start_time = end_time - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.MONTH:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=7)

        trends = []

        # Analyze key performance metrics
        key_metrics = ["items_per_second", "cpu_usage", "memory_usage", "error_rate", "response_time", "throughput"]

        for metric_name in key_metrics:
            metric_data = await self.metrics_collector.get_metrics(metric_name, start_time, end_time)

            if len(metric_data) < 2:
                continue

            trend = await self._calculate_trend(metric_name, metric_data, timeframe)
            trends.append(trend)

        return trends

    async def _calculate_trend(
        self, metric_name: str, data: list[dict[str, Any]], timeframe: AnalyticsTimeframe
    ) -> PerformanceTrend:
        """Calculate trend for a metric."""
        if len(data) < 2:
            return PerformanceTrend(
                metric_name=metric_name,
                timeframe=timeframe,
                trend_direction="stable",
                change_percentage=0.0,
                confidence_interval=(0.0, 0.0),
                seasonality_detected=False,
                anomalies=[],
            )

        values = [point["value"] for point in data]

        # Calculate linear trend
        n = len(values)
        x = list(range(n))

        # Simple linear regression
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Determine trend direction and change percentage
        first_value = values[0]
        last_value = values[-1]

        if abs(slope) < 0.01:  # Threshold for "stable"
            trend_direction = "stable"
            change_percentage = 0.0
        elif slope > 0:
            trend_direction = "increasing"
            change_percentage = ((last_value - first_value) / first_value) * 100 if first_value != 0 else 0
        else:
            trend_direction = "decreasing"
            change_percentage = ((last_value - first_value) / first_value) * 100 if first_value != 0 else 0

        # Detect anomalies (simplified)
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        anomalies = []
        for i, value in enumerate(values):
            if abs(value - mean_val) > 2 * std_val:  # 2 sigma rule
                anomalies.append(
                    {
                        "timestamp": data[i]["timestamp"].isoformat(),
                        "value": value,
                        "deviation": abs(value - mean_val) / std_val if std_val > 0 else 0,
                    }
                )

        return PerformanceTrend(
            metric_name=metric_name,
            timeframe=timeframe,
            trend_direction=trend_direction,
            change_percentage=change_percentage,
            confidence_interval=(min(values), max(values)),
            seasonality_detected=len(anomalies) > len(values) * 0.1,  # Simple seasonality check
            anomalies=anomalies,
        )

    async def generate_operation_insights(self) -> list[OperationInsight]:
        """Generate business intelligence insights about operations."""
        insights = []

        # Get operation statistics
        stats = await self.operation_tracker.get_operation_statistics()

        # Efficiency insights
        for op_type, completion_rate in stats.get("completion_rates", {}).items():
            if completion_rate < 0.9:  # Less than 90% success rate
                insight = OperationInsight(
                    insight_id=str(uuid.uuid4()),
                    operation_type=BulkOperationType(op_type),
                    insight_type="efficiency",
                    title=f"Low Success Rate for {op_type.title()} Operations",
                    description=f"Success rate of {completion_rate:.1%} is below optimal threshold",
                    impact_score=1.0 - completion_rate,
                    recommendations=[
                        "Review error logs for common failure patterns",
                        "Implement better validation and error handling",
                        "Consider reducing batch sizes for better reliability",
                    ],
                    supporting_data={"completion_rate": completion_rate},
                    confidence=0.9,
                    generated_at=datetime.now(),
                )
                insights.append(insight)

        # Performance insights
        for op_type, avg_time in stats.get("average_execution_times", {}).items():
            if avg_time > 300:  # More than 5 minutes average
                insight = OperationInsight(
                    insight_id=str(uuid.uuid4()),
                    operation_type=BulkOperationType(op_type),
                    insight_type="performance",
                    title=f"Slow {op_type.title()} Operations",
                    description=f"Average execution time of {avg_time:.1f}s exceeds recommended threshold",
                    impact_score=min(1.0, avg_time / 600),  # Normalize to 10 minutes
                    recommendations=[
                        "Optimize database queries and indexes",
                        "Increase parallel processing workers",
                        "Implement better connection pooling",
                    ],
                    supporting_data={"average_execution_time": avg_time},
                    confidence=0.8,
                    generated_at=datetime.now(),
                )
                insights.append(insight)

        return insights

    async def analyze_cost_efficiency(self) -> dict[BulkOperationType, CostAnalysis]:
        """Analyze cost efficiency of different operation types."""
        cost_analysis = {}

        for op_type, history in self.operation_tracker.operation_history.items():
            if not history:
                continue

            total_operations = len(history)
            total_items = sum(op["total_items"] for op in history)
            total_time = sum(op["execution_time"] for op in history)

            # Calculate efficiency metrics
            avg_items_per_second = total_items / total_time if total_time > 0 else 0
            avg_time_per_operation = total_time / total_operations if total_operations > 0 else 0

            # Simple cost model (in production, would use actual resource costs)
            cost_per_item = avg_time_per_operation * 0.001  # $0.001 per second per operation

            cost_analysis[op_type] = CostAnalysis(
                operation_type=op_type,
                total_operations=total_operations,
                total_items_processed=total_items,
                total_processing_time=total_time,
                average_cost_per_item=cost_per_item,
                peak_resource_usage={"cpu": 80.0, "memory": 1024.0},  # Mock data
                efficiency_score=min(1.0, avg_items_per_second / 1000),  # Normalize
                cost_trends={"last_week": cost_per_item * 0.9},  # Mock trend
            )

        return cost_analysis

    async def predict_operation_performance(self, operation_type: BulkOperationType, item_count: int) -> dict[str, Any]:
        """Predict performance metrics for a planned operation."""
        # Get historical data for this operation type
        history = self.operation_tracker.operation_history.get(operation_type, [])

        if not history:
            return {
                "predicted_duration": "unknown",
                "confidence": 0.0,
                "recommendations": ["No historical data available for prediction"],
            }

        # Simple prediction based on historical averages
        avg_execution_time = statistics.mean(op["execution_time"] for op in history)
        avg_items = statistics.mean(op["total_items"] for op in history)

        if avg_items > 0:
            time_per_item = avg_execution_time / avg_items
            predicted_duration = time_per_item * item_count
        else:
            predicted_duration = avg_execution_time

        # Calculate confidence based on data variance
        if len(history) > 1:
            execution_times = [op["execution_time"] for op in history]
            std_dev = statistics.stdev(execution_times)
            confidence = max(0.1, 1.0 - (std_dev / avg_execution_time))
        else:
            confidence = 0.5

        recommendations = []
        if predicted_duration > 1800:  # More than 30 minutes
            recommendations.append("Consider splitting into smaller batches")
        if confidence < 0.7:
            recommendations.append("Prediction confidence is low - monitor closely")

        return {
            "predicted_duration_seconds": predicted_duration,
            "predicted_duration_formatted": f"{int(predicted_duration // 60)}m {int(predicted_duration % 60)}s",
            "confidence": confidence,
            "based_on_operations": len(history),
            "recommendations": recommendations,
        }


class BulkMonitoringDashboard:
    """
    Comprehensive monitoring dashboard orchestrating all monitoring components.

    Provides unified interface for monitoring, analytics, and alerting.
    """

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.operation_tracker = OperationTracker()
        self.alert_manager = AlertManager()
        self.analytics_engine = AnalyticsEngine(self.metrics_collector, self.operation_tracker)

        self.dashboard_config = {
            "refresh_interval": 5.0,
            "retention_days": 30,
            "enable_predictions": True,
            "enable_insights": True,
        }

        self.monitoring_task = None

    async def initialize(self):
        """Initialize monitoring dashboard."""
        # Setup default alerts
        await self._setup_default_alerts()

        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Bulk monitoring dashboard initialized")

    async def _setup_default_alerts(self):
        """Setup default alert rules."""
        await self.alert_manager.define_alert(
            "High CPU Usage", "CPU usage exceeds 85%", "cpu_usage > threshold", 85.0, AlertSeverity.WARNING
        )

        await self.alert_manager.define_alert(
            "High Memory Usage", "Memory usage exceeds 90%", "memory_usage > threshold", 90.0, AlertSeverity.ERROR
        )

        await self.alert_manager.define_alert(
            "High Error Rate", "Operation error rate exceeds 10%", "error_rate > threshold", 10.0, AlertSeverity.ERROR
        )

        await self.alert_manager.define_alert(
            "Slow Operations",
            "Average response time exceeds 30 seconds",
            "response_time > threshold",
            30.0,
            AlertSeverity.WARNING,
        )

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                # Collect current metrics
                current_metrics = await self._collect_dashboard_metrics()

                # Record metrics
                for metric_name, value in current_metrics.items():
                    await self.metrics_collector.record_metric(metric_name, value)

                # Get operation data
                operation_stats = await self.operation_tracker.get_operation_statistics()

                # Check alerts
                await self.alert_manager.check_alerts(current_metrics, operation_stats)

                await asyncio.sleep(self.dashboard_config["refresh_interval"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _collect_dashboard_metrics(self) -> dict[str, float]:
        """Collect current dashboard metrics."""
        # In production, would collect actual system metrics
        import psutil

        return {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "active_operations": len(self.operation_tracker.active_operations),
            "error_rate": 2.1,  # Mock data
            "response_time": 15.3,  # Mock data
            "throughput": 850.2,  # Mock data
        }

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data."""
        # Get current metrics
        current_metrics = await self.metrics_collector.get_latest_metrics(
            ["cpu_usage", "memory_usage", "active_operations", "error_rate", "throughput"]
        )

        # Get operation statistics
        operation_stats = await self.operation_tracker.get_operation_statistics()

        # Get active alerts
        active_alerts = await self.alert_manager.get_active_alerts()

        # Get performance trends
        trends = await self.analytics_engine.analyze_performance_trends()

        # Get insights
        insights = await self.analytics_engine.generate_operation_insights()

        # Get cost analysis
        cost_analysis = await self.analytics_engine.analyze_cost_efficiency()

        return {
            "current_metrics": current_metrics,
            "operation_statistics": operation_stats,
            "active_alerts": [asdict(alert) for alert in active_alerts],
            "performance_trends": [asdict(trend) for trend in trends],
            "insights": [asdict(insight) for insight in insights],
            "cost_analysis": {op_type.value: asdict(analysis) for op_type, analysis in cost_analysis.items()},
            "dashboard_health": {
                "monitoring_active": self.monitoring_task is not None,
                "metrics_buffer_size": len(self.metrics_collector.metrics_buffer),
                "active_operations_count": len(self.operation_tracker.active_operations),
                "total_alerts": len(self.alert_manager.alerts),
            },
            "last_updated": datetime.now().isoformat(),
        }

    async def shutdown(self):
        """Gracefully shutdown monitoring dashboard."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Bulk monitoring dashboard shutdown complete")


# Global instance
_monitoring_dashboard_instance: BulkMonitoringDashboard | None = None


async def get_monitoring_dashboard() -> BulkMonitoringDashboard:
    """Get or create the global monitoring dashboard instance."""
    global _monitoring_dashboard_instance

    if _monitoring_dashboard_instance is None:
        _monitoring_dashboard_instance = BulkMonitoringDashboard()
        await _monitoring_dashboard_instance.initialize()

    return _monitoring_dashboard_instance
