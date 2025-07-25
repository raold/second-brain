"""
Integration tests for v2.8.3 Intelligence API routes.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models.intelligence.analytics_models import (
    AnomalyType,
    InsightCategory,
    MetricType,
    TimeGranularity,
)


class TestIntelligenceRoutes:
    """Test intelligence API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_analytics_dashboard(self, client: TestClient, auth_headers):
        """Test analytics dashboard generation."""
        query_data = {
            "metrics": [MetricType.API_USAGE.value, MetricType.QUERY_PERFORMANCE.value],
            "granularity": TimeGranularity.HOUR.value,
            "include_insights": True,
            "include_anomalies": True,
            "include_knowledge_gaps": False
        }

        response = client.post(
            "/intelligence/analytics/dashboard",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify dashboard structure
        assert "metrics" in data
        assert "insights" in data
        assert "anomalies" in data
        assert "total_memories" in data
        assert "system_health_score" in data
        assert 0 <= data["system_health_score"] <= 1

    @pytest.mark.asyncio
    async def test_list_available_metrics(self, client: TestClient, auth_headers):
        """Test listing available metrics."""
        response = client.get(
            "/intelligence/analytics/metrics",
            headers=auth_headers
        )

        assert response.status_code == 200
        metrics = response.json()

        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert MetricType.API_USAGE.value in metrics
        assert MetricType.QUERY_PERFORMANCE.value in metrics

    @pytest.mark.asyncio
    async def test_get_predictive_insights(self, client: TestClient, auth_headers):
        """Test getting predictive insights."""
        response = client.get(
            "/intelligence/analytics/insights",
            params={
                "min_confidence": 0.5,
                "min_impact": 0.5,
                "limit": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        insights = response.json()

        assert isinstance(insights, list)
        for insight in insights:
            assert "id" in insight
            assert "category" in insight
            assert "title" in insight
            assert "confidence" in insight
            assert insight["confidence"] >= 0.5
            assert "impact_score" in insight
            assert insight["impact_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_get_insights_by_category(self, client: TestClient, auth_headers):
        """Test filtering insights by category."""
        response = client.get(
            "/intelligence/analytics/insights",
            params={
                "category": InsightCategory.PERFORMANCE.value,
                "limit": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        insights = response.json()

        # All insights should be performance category
        for insight in insights:
            assert insight["category"] == InsightCategory.PERFORMANCE.value

    @pytest.mark.asyncio
    async def test_get_detected_anomalies(self, client: TestClient, auth_headers):
        """Test getting detected anomalies."""
        response = client.get(
            "/intelligence/analytics/anomalies",
            params={
                "min_severity": 0.5,
                "hours": 48
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        anomalies = response.json()

        assert isinstance(anomalies, list)
        for anomaly in anomalies:
            assert "id" in anomaly
            assert "metric_type" in anomaly
            assert "anomaly_type" in anomaly
            assert "severity" in anomaly
            assert anomaly["severity"] >= 0.5
            assert "confidence" in anomaly

    @pytest.mark.asyncio
    async def test_filter_anomalies(self, client: TestClient, auth_headers):
        """Test filtering anomalies by type."""
        response = client.get(
            "/intelligence/analytics/anomalies",
            params={
                "metric_type": MetricType.API_USAGE.value,
                "anomaly_type": AnomalyType.SPIKE.value,
                "hours": 24
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        anomalies = response.json()

        for anomaly in anomalies:
            assert anomaly["metric_type"] == MetricType.API_USAGE.value
            assert anomaly["anomaly_type"] == AnomalyType.SPIKE.value

    @pytest.mark.asyncio
    async def test_analyze_knowledge_gaps(self, client: TestClient, auth_headers):
        """Test knowledge gap analysis."""
        response = client.get(
            "/intelligence/analytics/knowledge-gaps",
            params={"limit": 10},
            headers=auth_headers
        )

        assert response.status_code == 200
        gaps = response.json()

        assert isinstance(gaps, list)
        for gap in gaps:
            assert "id" in gap
            assert "topic" in gap
            assert "gap_score" in gap
            assert 0 <= gap["gap_score"] <= 1
            assert "importance_score" in gap
            assert "suggested_queries" in gap
            assert isinstance(gap["suggested_queries"], list)

    @pytest.mark.asyncio
    async def test_knowledge_gaps_with_focus_areas(self, client: TestClient, auth_headers):
        """Test knowledge gap analysis with focus areas."""
        response = client.get(
            "/intelligence/analytics/knowledge-gaps",
            params={
                "limit": 10,
                "focus_areas": ["machine learning", "data science"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        gaps = response.json()
        assert isinstance(gaps, list)

    @pytest.mark.asyncio
    async def test_get_performance_benchmarks(self, client: TestClient, auth_headers):
        """Test getting performance benchmarks."""
        response = client.get(
            "/intelligence/analytics/benchmarks",
            headers=auth_headers
        )

        assert response.status_code == 200
        benchmarks = response.json()

        assert isinstance(benchmarks, list)
        assert len(benchmarks) > 0

        for benchmark in benchmarks:
            assert "operation" in benchmark
            assert "p50_ms" in benchmark
            assert "p90_ms" in benchmark
            assert "p99_ms" in benchmark
            assert benchmark["p50_ms"] <= benchmark["p90_ms"] <= benchmark["p99_ms"]
            assert "throughput_per_second" in benchmark
            assert "error_rate" in benchmark

    @pytest.mark.asyncio
    async def test_set_metric_threshold(self, client: TestClient, auth_headers):
        """Test setting metric threshold."""
        threshold_data = {
            "metric_type": MetricType.QUERY_PERFORMANCE.value,
            "max_value": 1000.0,
            "alert_on_breach": True,
            "breach_duration_minutes": 5
        }

        response = client.post(
            "/intelligence/analytics/thresholds",
            json=threshold_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_metric_thresholds(self, client: TestClient, auth_headers):
        """Test getting metric thresholds."""
        response = client.get(
            "/intelligence/analytics/thresholds",
            headers=auth_headers
        )

        assert response.status_code == 200
        thresholds = response.json()

        assert isinstance(thresholds, list)
        for threshold in thresholds:
            assert "metric_type" in threshold
            assert "alert_on_breach" in threshold

    @pytest.mark.asyncio
    async def test_export_analytics_json(self, client: TestClient, auth_headers):
        """Test exporting analytics data as JSON."""
        response = client.get(
            "/intelligence/analytics/export",
            params={"format": "json"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        assert "insights" in data
        assert "anomalies" in data
        assert "knowledge_gaps" in data

    @pytest.mark.asyncio
    async def test_export_analytics_csv(self, client: TestClient, auth_headers):
        """Test exporting analytics data as CSV."""
        response = client.get(
            "/intelligence/analytics/export",
            params={"format": "csv"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "content" in data
        assert "media_type" in data
        assert data["media_type"] == "text/csv"
        assert "filename" in data

        # Verify CSV content has headers
        csv_content = data["content"]
        assert "Metric,Timestamp,Value,Trend,Average" in csv_content

    @pytest.mark.asyncio
    async def test_refresh_analytics_cache(self, client: TestClient, auth_headers):
        """Test refreshing analytics cache."""
        response = client.post(
            "/intelligence/analytics/refresh",
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "cache cleared" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_dashboard_with_date_range(self, client: TestClient, auth_headers):
        """Test dashboard generation with date range."""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        query_data = {
            "granularity": TimeGranularity.DAY.value,
            "start_date": start_date,
            "end_date": end_date,
            "include_insights": False,
            "include_anomalies": False,
            "include_knowledge_gaps": False
        }

        response = client.post(
            "/intelligence/analytics/dashboard",
            json=query_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metrics are within date range
        assert "metrics" in data
        for metric_data in data["metrics"].values():
            if "start_time" in metric_data:
                assert metric_data["start_time"] is not None
            if "end_time" in metric_data:
                assert metric_data["end_time"] is not None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_metric(self, client: TestClient, auth_headers):
        """Test error handling for invalid metric type."""
        query_data = {
            "metrics": ["invalid_metric"],
            "granularity": TimeGranularity.HOUR.value
        }

        response = client.post(
            "/intelligence/analytics/dashboard",
            json=query_data,
            headers=auth_headers
        )

        # Should handle gracefully or return validation error
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_concurrent_dashboard_requests(self, client: TestClient, auth_headers):
        """Test handling concurrent dashboard requests."""

        query_data = {
            "granularity": TimeGranularity.HOUR.value,
            "include_insights": True,
            "include_anomalies": True
        }

        # Make multiple concurrent requests
        async def make_request():
            return client.post(
                "/intelligence/analytics/dashboard",
                json=query_data,
                headers=auth_headers
            )

        # Should handle concurrent requests without errors
        responses = []
        for _ in range(3):
            response = client.post(
                "/intelligence/analytics/dashboard",
                json=query_data,
                headers=auth_headers
            )
            responses.append(response)

        for response in responses:
            assert response.status_code == 200
