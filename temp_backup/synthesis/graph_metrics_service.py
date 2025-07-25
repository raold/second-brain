"""
Real-time graph metrics calculation service
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import networkx as nx
import numpy as np
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.memory import Memory
from app.models.synthesis.metrics_models import (
    Anomaly,
    GraphMetrics,
    MetricsAlert,
    MetricsDashboard,
    MetricsSnapshot,
    MetricsTrend,
)
from app.services.synthesis.graph_cache import GraphCacheService
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GraphMetricsService:
    """Service for calculating and monitoring graph metrics"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_service = GraphCacheService()
        self._graph_cache = {}
        self._metrics_history = []
        self._anomaly_detector = AnomalyDetector()

    async def calculate_metrics(
        self,
        user_id: str,
        graph_id: str = "main",
        use_cache: bool = True
    ) -> GraphMetrics:
        """Calculate current graph metrics"""
        start_time = datetime.utcnow()

        try:
            # Check cache first
            if use_cache:
                cached_metrics = await self.cache_service.get_metrics(user_id, graph_id)
                if cached_metrics:
                    cached_metrics.cache_hit = True
                    return cached_metrics

            # Build or retrieve graph
            graph = await self._build_graph(user_id)

            # Calculate basic metrics
            basic_metrics = self._calculate_basic_metrics(graph)

            # Calculate structural metrics
            structural_metrics = await self._calculate_structural_metrics(graph)

            # Calculate centrality metrics
            centrality_metrics = await self._calculate_centrality_metrics(graph)

            # Calculate growth metrics
            growth_metrics = await self._calculate_growth_metrics(user_id)

            # Combine all metrics
            calculation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            metrics = GraphMetrics(
                graph_id=graph_id,
                timestamp=datetime.utcnow(),
                calculation_time_ms=calculation_time_ms,
                cache_hit=False,
                **basic_metrics,
                **structural_metrics,
                **centrality_metrics,
                **growth_metrics
            )

            # Cache the metrics
            await self.cache_service.set_metrics(user_id, graph_id, metrics)

            # Store in history
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-1000:]

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise

    async def get_metrics_dashboard(
        self,
        user_id: str,
        time_range_days: int = 7,
        graph_id: str = "main"
    ) -> MetricsDashboard:
        """Get comprehensive metrics dashboard"""
        start_time = datetime.utcnow()

        try:
            # Get current metrics
            current_metrics = await self.calculate_metrics(user_id, graph_id)

            # Get historical metrics
            historical_metrics = await self._get_historical_metrics(
                user_id, graph_id, time_range_days
            )

            # Calculate trends
            trends = await self._calculate_trends(historical_metrics)

            # Detect anomalies
            anomalies = await self._detect_anomalies(
                current_metrics, historical_metrics
            )

            # Generate insights
            insights = await self._generate_insights(
                current_metrics, trends, anomalies
            )

            # Generate recommendations
            recommendations = await self._generate_recommendations(
                current_metrics, trends, anomalies
            )

            # Make predictions
            predictions = await self._make_predictions(historical_metrics)

            # Create summary
            summary = self._create_summary(
                current_metrics, trends, anomalies
            )

            generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MetricsDashboard(
                current_metrics=current_metrics,
                historical_metrics=historical_metrics,
                trends=trends,
                active_anomalies=[a for a in anomalies if not a.resolved],
                recent_anomalies=anomalies[:10],
                insights=insights,
                recommendations=recommendations,
                predictions=predictions,
                summary=summary,
                time_range_days=time_range_days,
                generation_time_ms=generation_time_ms
            )

        except Exception as e:
            logger.error(f"Error creating metrics dashboard: {e}")
            raise

    async def create_snapshot(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> MetricsSnapshot:
        """Create a snapshot of current metrics"""
        try:
            # Calculate current metrics
            metrics = await self.calculate_metrics(user_id)

            # Get notable nodes
            graph = await self._build_graph(user_id)
            notable_nodes = await self._get_notable_nodes(graph, metrics)

            # Get notable communities
            notable_communities = await self._get_notable_communities(graph)

            # Create snapshot
            snapshot = MetricsSnapshot(
                name=name,
                description=description,
                metrics=metrics,
                notable_nodes=notable_nodes,
                notable_communities=notable_communities,
                tags=tags or [],
                created_by=user_id
            )

            # Store snapshot (in production, save to database)
            # await self._save_snapshot(snapshot)

            return snapshot

        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            raise

    async def check_alerts(
        self,
        user_id: str,
        alerts: list[MetricsAlert]
    ) -> list[tuple[MetricsAlert, bool]]:
        """Check if any alerts should be triggered"""
        results = []

        try:
            metrics = await self.calculate_metrics(user_id)

            for alert in alerts:
                if not alert.enabled:
                    continue

                triggered = await self._check_alert_condition(
                    alert, metrics
                )

                if triggered:
                    alert.last_triggered = datetime.utcnow()
                    alert.trigger_count += 1

                results.append((alert, triggered))

            return results

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []

    async def _build_graph(self, user_id: str) -> nx.DiGraph:
        """Build NetworkX graph from memories and relationships"""
        # Check cache
        cache_key = f"graph_{user_id}"
        if cache_key in self._graph_cache:
            cached_time, graph = self._graph_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(minutes=5):
                return graph

        graph = nx.DiGraph()

        try:
            # Get all memories
            memories_query = select(Memory).where(
                and_(
                    Memory.user_id == user_id,
                    Memory.deleted_at.is_(None)
                )
            )
            memories_result = await self.db.execute(memories_query)
            memories = memories_result.scalars().all()

            # Add nodes
            for memory in memories:
                graph.add_node(
                    str(memory.id),
                    title=memory.title,
                    importance=memory.importance,
                    created_at=memory.created_at,
                    memory_type=memory.memory_type
                )

            # Get all relationships
            relationships_query = text("""
                SELECT source_id, target_id, relationship_type, strength
                FROM memory_relationships
                WHERE source_id IN (
                    SELECT id FROM memories
                    WHERE user_id = :user_id AND deleted_at IS NULL
                )
            """)

            relationships_result = await self.db.execute(
                relationships_query,
                {"user_id": user_id}
            )
            relationships = relationships_result.fetchall()

            # Add edges
            for rel in relationships:
                graph.add_edge(
                    str(rel.source_id),
                    str(rel.target_id),
                    relationship_type=rel.relationship_type,
                    weight=rel.strength
                )

            # Cache the graph
            self._graph_cache[cache_key] = (datetime.utcnow(), graph)

            return graph

        except Exception as e:
            logger.error(f"Error building graph: {e}")
            return nx.DiGraph()

    def _calculate_basic_metrics(self, graph: nx.DiGraph) -> dict[str, Any]:
        """Calculate basic graph metrics"""
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()

        if node_count > 0:
            density = nx.density(graph)
            average_degree = sum(dict(graph.degree()).values()) / node_count
        else:
            density = 0.0
            average_degree = 0.0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
            "average_degree": average_degree
        }

    async def _calculate_structural_metrics(
        self,
        graph: nx.DiGraph
    ) -> dict[str, Any]:
        """Calculate structural graph metrics"""
        if graph.number_of_nodes() == 0:
            return {
                "clustering_coefficient": 0.0,
                "connected_components": 0,
                "largest_component_size": 0,
                "diameter": 0,
                "average_path_length": 0.0
            }

        # Convert to undirected for some metrics
        undirected_graph = graph.to_undirected()

        # Clustering coefficient
        clustering_coefficient = nx.average_clustering(undirected_graph)

        # Connected components
        components = list(nx.connected_components(undirected_graph))
        connected_components = len(components)
        largest_component_size = max(len(c) for c in components) if components else 0

        # Diameter and average path length (for largest component)
        if largest_component_size > 1:
            largest_component = undirected_graph.subgraph(max(components, key=len))
            diameter = nx.diameter(largest_component)
            average_path_length = nx.average_shortest_path_length(largest_component)
        else:
            diameter = 0
            average_path_length = 0.0

        return {
            "clustering_coefficient": clustering_coefficient,
            "connected_components": connected_components,
            "largest_component_size": largest_component_size,
            "diameter": diameter,
            "average_path_length": average_path_length
        }

    async def _calculate_centrality_metrics(
        self,
        graph: nx.DiGraph
    ) -> dict[str, Any]:
        """Calculate centrality metrics"""
        if graph.number_of_nodes() == 0:
            return {
                "degree_centrality": {},
                "betweenness_centrality": {},
                "closeness_centrality": {},
                "eigenvector_centrality": {}
            }

        # Calculate various centrality measures
        degree_centrality = nx.degree_centrality(graph)
        betweenness_centrality = nx.betweenness_centrality(graph)
        closeness_centrality = nx.closeness_centrality(graph)

        # Eigenvector centrality (may fail for some graphs)
        try:
            eigenvector_centrality = nx.eigenvector_centrality(graph, max_iter=1000)
        except:
            eigenvector_centrality = {}

        # Get top 10 nodes for each metric
        top_n = 10

        return {
            "degree_centrality": dict(sorted(
                degree_centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]),
            "betweenness_centrality": dict(sorted(
                betweenness_centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]),
            "closeness_centrality": dict(sorted(
                closeness_centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]),
            "eigenvector_centrality": dict(sorted(
                eigenvector_centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]) if eigenvector_centrality else {}
        }

    async def _calculate_growth_metrics(
        self,
        user_id: str
    ) -> dict[str, Any]:
        """Calculate growth metrics"""
        try:
            # Get memory creation stats
            query = text("""
                WITH daily_stats AS (
                    SELECT
                        DATE(created_at) as date,
                        COUNT(*) as memories_created,
                        COUNT(DISTINCT id) as unique_memories
                    FROM memories
                    WHERE
                        user_id = :user_id
                        AND deleted_at IS NULL
                        AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                ),
                edge_stats AS (
                    SELECT
                        DATE(mr.created_at) as date,
                        COUNT(*) as edges_created
                    FROM memory_relationships mr
                    JOIN memories m ON m.id = mr.source_id
                    WHERE
                        m.user_id = :user_id
                        AND mr.created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(mr.created_at)
                )
                SELECT
                    AVG(memories_created) as avg_nodes_per_day,
                    AVG(edges_created) as avg_edges_per_day
                FROM daily_stats
                LEFT JOIN edge_stats USING(date)
            """)

            result = await self.db.execute(query, {"user_id": user_id})
            growth_stats = result.fetchone()

            # Get last hour stats
            hour_query = text("""
                SELECT
                    (SELECT COUNT(*) FROM memories
                     WHERE user_id = :user_id
                     AND created_at >= NOW() - INTERVAL '1 hour'
                     AND deleted_at IS NULL) as new_nodes_last_hour,
                    (SELECT COUNT(*) FROM memory_relationships mr
                     JOIN memories m ON m.id = mr.source_id
                     WHERE m.user_id = :user_id
                     AND mr.created_at >= NOW() - INTERVAL '1 hour') as new_edges_last_hour
            """)

            hour_result = await self.db.execute(hour_query, {"user_id": user_id})
            hour_stats = hour_result.fetchone()

            return {
                "growth_rate_nodes_per_day": float(growth_stats.avg_nodes_per_day or 0),
                "growth_rate_edges_per_day": float(growth_stats.avg_edges_per_day or 0),
                "new_nodes_last_hour": hour_stats.new_nodes_last_hour or 0,
                "new_edges_last_hour": hour_stats.new_edges_last_hour or 0
            }

        except Exception as e:
            logger.error(f"Error calculating growth metrics: {e}")
            return {
                "growth_rate_nodes_per_day": 0.0,
                "growth_rate_edges_per_day": 0.0,
                "new_nodes_last_hour": 0,
                "new_edges_last_hour": 0
            }

    async def _get_historical_metrics(
        self,
        user_id: str,
        graph_id: str,
        days: int
    ) -> list[GraphMetrics]:
        """Get historical metrics from cache/database"""
        # In production, load from database
        # For now, return recent metrics from memory
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        historical = [
            m for m in self._metrics_history
            if m.graph_id == graph_id and m.timestamp > cutoff_time
        ]

        # If not enough history, generate some
        if len(historical) < days:
            current = await self.calculate_metrics(user_id, graph_id)
            historical = [current]

        return historical

    async def _calculate_trends(
        self,
        historical_metrics: list[GraphMetrics]
    ) -> dict[str, MetricsTrend]:
        """Calculate trends for various metrics"""
        if len(historical_metrics) < 2:
            return {}

        trends = {}

        # Metrics to track
        metric_names = [
            "node_count", "edge_count", "density", "average_degree",
            "clustering_coefficient", "largest_component_size"
        ]

        for metric_name in metric_names:
            time_series = [
                {
                    "timestamp": m.timestamp,
                    "value": getattr(m, metric_name)
                }
                for m in historical_metrics
            ]

            values = [ts["value"] for ts in time_series]

            # Calculate trend statistics
            trend = MetricsTrend(
                metric_name=metric_name,
                time_series=time_series,
                trend_direction=self._determine_trend_direction(values),
                trend_strength=self._calculate_trend_strength(values),
                average_value=np.mean(values),
                min_value=min(values),
                max_value=max(values),
                standard_deviation=np.std(values)
            )

            # Simple linear forecast
            if len(values) >= 3:
                forecast = self._simple_forecast(values)
                trend.forecast_next_value = forecast
                trend.confidence_interval = (
                    forecast - trend.standard_deviation,
                    forecast + trend.standard_deviation
                )

            trends[metric_name] = trend

        return trends

    def _determine_trend_direction(self, values: list[float]) -> str:
        """Determine trend direction from values"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]

        # Determine volatility
        volatility = np.std(values) / (np.mean(values) + 1e-10)

        if volatility > 0.5:
            return "volatile"
        elif slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"

    def _calculate_trend_strength(self, values: list[float]) -> float:
        """Calculate trend strength (0-1)"""
        if len(values) < 2:
            return 0.0

        # Calculate R-squared of linear fit
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)
        yhat = poly(x)
        ybar = np.mean(values)
        ssreg = np.sum((yhat - ybar) ** 2)
        sstot = np.sum((values - ybar) ** 2)

        if sstot == 0:
            return 0.0

        r_squared = ssreg / sstot
        return min(max(r_squared, 0.0), 1.0)

    def _simple_forecast(self, values: list[float]) -> float:
        """Simple linear forecast for next value"""
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)
        return float(poly(len(values)))

    async def _detect_anomalies(
        self,
        current: GraphMetrics,
        historical: list[GraphMetrics]
    ) -> list[Anomaly]:
        """Detect anomalies in metrics"""
        return self._anomaly_detector.detect(current, historical)

    async def _generate_insights(
        self,
        current: GraphMetrics,
        trends: dict[str, MetricsTrend],
        anomalies: list[Anomaly]
    ) -> list[str]:
        """Generate insights from metrics"""
        insights = []

        # Density insights
        if current.density < 0.1:
            insights.append("Your knowledge graph is sparse. Consider creating more connections between related memories.")
        elif current.density > 0.5:
            insights.append("Your knowledge graph is highly connected, indicating strong knowledge integration.")

        # Growth insights
        if current.growth_rate_nodes_per_day > 10:
            insights.append("You're adding memories at a high rate. Consider consolidating similar memories.")

        # Component insights
        if current.connected_components > 5:
            insights.append(f"Your graph has {current.connected_components} separate components. Consider connecting isolated memory clusters.")

        # Clustering insights
        if current.clustering_coefficient > 0.5:
            insights.append("High clustering indicates tight knowledge communities. Good for specialized topics.")

        # Trend insights
        for metric_name, trend in trends.items():
            if trend.trend_direction == "increasing" and trend.trend_strength > 0.7:
                insights.append(f"{metric_name.replace('_', ' ').title()} is growing strongly.")

        # Anomaly insights
        critical_anomalies = [a for a in anomalies if a.severity == "critical"]
        if critical_anomalies:
            insights.append(f"Detected {len(critical_anomalies)} critical anomalies requiring attention.")

        return insights[:10]  # Top 10 insights

    async def _generate_recommendations(
        self,
        current: GraphMetrics,
        trends: dict[str, MetricsTrend],
        anomalies: list[Anomaly]
    ) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Connection recommendations
        if current.density < 0.05:
            recommendations.append("Review recent memories and create connections between related topics.")

        # Consolidation recommendations
        if current.node_count > 1000 and current.growth_rate_nodes_per_day > 20:
            recommendations.append("Consider using memory consolidation to merge similar memories.")

        # Review recommendations
        isolated_nodes = current.node_count - current.largest_component_size
        if isolated_nodes > current.node_count * 0.2:
            recommendations.append(f"Review {isolated_nodes} isolated memories and connect them to your main knowledge graph.")

        # Performance recommendations
        if current.calculation_time_ms > 1000:
            recommendations.append("Enable caching to improve dashboard performance.")

        # Anomaly recommendations
        for anomaly in anomalies[:3]:  # Top 3 anomalies
            if anomaly.suggested_investigation:
                recommendations.extend(anomaly.suggested_investigation[:1])

        return recommendations[:10]  # Top 10 recommendations

    async def _make_predictions(
        self,
        historical: list[GraphMetrics]
    ) -> dict[str, dict[str, Any]]:
        """Make predictions about future metrics"""
        predictions = {}

        if len(historical) < 3:
            return predictions

        # Node count prediction
        node_counts = [m.node_count for m in historical]
        next_node_count = self._simple_forecast(node_counts)

        predictions["node_count"] = {
            "next_value": int(next_node_count),
            "confidence": 0.7,
            "timeframe": "next_day"
        }

        # Edge count prediction
        edge_counts = [m.edge_count for m in historical]
        next_edge_count = self._simple_forecast(edge_counts)

        predictions["edge_count"] = {
            "next_value": int(next_edge_count),
            "confidence": 0.7,
            "timeframe": "next_day"
        }

        # Growth rate prediction
        growth_rates = [m.growth_rate_nodes_per_day for m in historical[-7:]]
        if growth_rates:
            predictions["growth_rate"] = {
                "next_value": np.mean(growth_rates),
                "confidence": 0.6,
                "timeframe": "next_week"
            }

        return predictions

    def _create_summary(
        self,
        current: GraphMetrics,
        trends: dict[str, MetricsTrend],
        anomalies: list[Anomaly]
    ) -> dict[str, Any]:
        """Create summary statistics"""
        return {
            "total_knowledge_items": current.node_count,
            "total_connections": current.edge_count,
            "knowledge_density": f"{current.density:.1%}",
            "largest_topic_cluster": current.largest_component_size,
            "active_anomalies": len([a for a in anomalies if not a.resolved]),
            "strongest_trend": max(
                trends.items(),
                key=lambda x: x[1].trend_strength,
                default=(None, None)
            )[0] if trends else None
        }

    async def _get_notable_nodes(
        self,
        graph: nx.DiGraph,
        metrics: GraphMetrics
    ) -> list[dict[str, Any]]:
        """Get notable nodes from the graph"""
        notable = []

        # Top nodes by degree centrality
        for node_id, centrality in list(metrics.degree_centrality.items())[:5]:
            if node_id in graph:
                node_data = graph.nodes[node_id]
                notable.append({
                    "id": node_id,
                    "title": node_data.get("title", "Unknown"),
                    "metric": "degree_centrality",
                    "value": centrality,
                    "description": "Highly connected memory"
                })

        # Top nodes by betweenness centrality
        for node_id, centrality in list(metrics.betweenness_centrality.items())[:3]:
            if node_id in graph and node_id not in [n["id"] for n in notable]:
                node_data = graph.nodes[node_id]
                notable.append({
                    "id": node_id,
                    "title": node_data.get("title", "Unknown"),
                    "metric": "betweenness_centrality",
                    "value": centrality,
                    "description": "Important bridge memory"
                })

        return notable

    async def _get_notable_communities(
        self,
        graph: nx.DiGraph
    ) -> list[dict[str, Any]]:
        """Get notable communities from the graph"""
        if graph.number_of_nodes() < 5:
            return []

        # Convert to undirected for community detection
        undirected = graph.to_undirected()

        # Detect communities (simple connected components for now)
        communities = list(nx.connected_components(undirected))

        # Sort by size
        communities.sort(key=len, reverse=True)

        notable = []
        for i, community in enumerate(communities[:5]):
            # Get representative nodes
            subgraph = graph.subgraph(community)

            # Find most central node as representative
            if len(community) > 0:
                centrality = nx.degree_centrality(subgraph)
                representative = max(centrality.items(), key=lambda x: x[1])[0]

                notable.append({
                    "id": f"community_{i}",
                    "size": len(community),
                    "representative_node": representative,
                    "representative_title": graph.nodes[representative].get("title", "Unknown"),
                    "description": f"Knowledge cluster with {len(community)} memories"
                })

        return notable

    async def _check_alert_condition(
        self,
        alert: MetricsAlert,
        metrics: GraphMetrics
    ) -> bool:
        """Check if alert condition is met"""
        try:
            # Get metric value
            metric_value = getattr(metrics, alert.metric_name, None)
            if metric_value is None:
                return False

            # For dictionary metrics, use the count
            if isinstance(metric_value, dict):
                metric_value = len(metric_value)

            # Check condition
            if alert.condition == "greater_than":
                return metric_value > alert.threshold
            elif alert.condition == "less_than":
                return metric_value < alert.threshold
            elif alert.condition == "equals":
                return abs(metric_value - alert.threshold) < 0.001
            elif alert.condition == "change_rate":
                # Need historical data for change rate
                # This is simplified
                return False

            return False

        except Exception as e:
            logger.error(f"Error checking alert condition: {e}")
            return False


class AnomalyDetector:
    """Detects anomalies in graph metrics"""

    def detect(
        self,
        current: GraphMetrics,
        historical: list[GraphMetrics]
    ) -> list[Anomaly]:
        """Detect anomalies by comparing current to historical metrics"""
        anomalies = []

        if len(historical) < 3:
            return anomalies

        # Metrics to check
        metrics_to_check = [
            ("node_count", "Node Count"),
            ("edge_count", "Edge Count"),
            ("density", "Graph Density"),
            ("average_degree", "Average Degree"),
            ("clustering_coefficient", "Clustering Coefficient")
        ]

        for metric_name, display_name in metrics_to_check:
            # Get historical values
            historical_values = [
                getattr(m, metric_name) for m in historical
            ]

            # Calculate statistics
            mean_value = np.mean(historical_values)
            std_value = np.std(historical_values)

            # Get current value
            current_value = getattr(current, metric_name)

            # Check for anomalies (z-score method)
            if std_value > 0:
                z_score = abs(current_value - mean_value) / std_value

                if z_score > 3:  # 3 standard deviations
                    anomaly_type = "spike" if current_value > mean_value else "drop"
                    severity = self._determine_severity(z_score)

                    anomaly = Anomaly(
                        metric_name=metric_name,
                        detected_at=datetime.utcnow(),
                        anomaly_type=anomaly_type,
                        severity=severity,
                        current_value=current_value,
                        expected_value=mean_value,
                        deviation_percentage=((current_value - mean_value) / mean_value) * 100,
                        description=f"{display_name} is {z_score:.1f} standard deviations from normal",
                        suggested_investigation=[
                            f"Check recent changes to {display_name.lower()}",
                            "Review recent memory operations",
                            "Verify data integrity"
                        ]
                    )
                    anomalies.append(anomaly)

        return anomalies

    def _determine_severity(self, z_score: float) -> str:
        """Determine anomaly severity based on z-score"""
        if z_score > 5:
            return "critical"
        elif z_score > 4:
            return "high"
        elif z_score > 3:
            return "medium"
        else:
            return "low"
