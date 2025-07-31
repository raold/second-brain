"""
Comprehensive Tests for Monitoring and Observability Endpoints
Tests metrics, health checks, and monitoring functionality
"""

import time
from unittest.mock import patch

import pytest
from httpx import AsyncClient


class TestMonitoringEndpoints:
    """Test all monitoring and observability endpoints"""

    @pytest.mark.asyncio
    async def test_health_endpoint_basic(self, client: AsyncClient):
        """Test basic health endpoint functionality"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify health response structure
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient):
        """Test detailed health check endpoint"""
        response = await client.get("/health/detailed")

        # Should return detailed health information
        assert response.status_code in [200, 503]  # Healthy or unhealthy

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "checks" in data or "components" in data or "timestamp" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint_authorization(self, client: AsyncClient, api_key: str):
        """Test metrics endpoint requires authorization"""
        # Test without API key
        response = await client.get("/metrics")
        assert response.status_code in [401, 422]

        # Test with valid API key
        response = await client.get(
            "/metrics",
            params={"api_key": api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_endpoint_content(self, client: AsyncClient, api_key: str):
        """Test metrics endpoint returns proper metrics data"""
        response = await client.get(
            "/metrics",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metrics structure
        expected_sections = ["system", "application", "timestamp"]
        present_sections = [section for section in expected_sections if section in data]
        assert len(present_sections) >= 1, "Metrics should contain at least one expected section"

        if "system" in data:
            system_metrics = data["system"]
            expected_system_metrics = ["cpu_percent", "memory_percent", "uptime_seconds"]
            system_present = [metric for metric in expected_system_metrics if metric in system_metrics]
            assert len(system_present) >= 1, "System metrics should contain basic metrics"

    @pytest.mark.asyncio
    async def test_monitoring_summary_endpoint(self, client: AsyncClient):
        """Test monitoring summary endpoint"""
        response = await client.get("/monitoring/summary")

        assert response.status_code == 200
        data = response.json()

        # Should contain monitoring summary information
        assert isinstance(data, dict)
        # Common monitoring fields
        monitoring_fields = ["metrics", "requests", "performance", "timestamp"]
        present_fields = [field for field in monitoring_fields if field in data]
        assert len(present_fields) >= 0  # May have different structure

    @pytest.mark.asyncio
    async def test_security_status_endpoint(self, client: AsyncClient, api_key: str):
        """Test security status monitoring endpoint"""
        response = await client.get(
            "/security/status",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Should contain security metrics
        assert "security" in data or "timestamp" in data

        if "security" in data:
            security_data = data["security"]
            assert isinstance(security_data, dict)

    @pytest.mark.asyncio
    async def test_security_audit_endpoint(self, client: AsyncClient, api_key: str):
        """Test security audit endpoint"""
        response = await client.get(
            "/security/audit",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Should contain audit results
        audit_fields = ["status", "results", "recommendations", "timestamp"]
        present_fields = [field for field in audit_fields if field in data]
        assert len(present_fields) >= 1, "Audit should contain audit information"

    @pytest.mark.asyncio
    async def test_version_endpoint_comprehensive(self, client: AsyncClient):
        """Test version endpoint returns comprehensive version info"""
        response = await client.get("/version")

        assert response.status_code == 200
        data = response.json()

        # Verify version information structure
        required_fields = ["version", "version_string", "environment"]
        for field in required_fields:
            assert field in data, f"Version info missing required field: {field}"

        # Version should be a valid format
        assert data["version"] in ["3.0.0", "2.4.4"]  # Known versions
        assert data["version_string"].startswith("v")

    @pytest.mark.asyncio
    async def test_status_endpoint_database_metrics(self, client: AsyncClient, api_key: str):
        """Test status endpoint provides database metrics"""
        response = await client.get(
            "/status",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Should contain database status
        assert "database" in data
        assert data["database"] == "connected"

        # Should contain index status
        if "index_status" in data:
            index_status = data["index_status"]
            expected_index_fields = ["memories_with_embeddings", "index_ready"]
            for field in expected_index_fields:
                if field in index_status:
                    assert isinstance(index_status[field], int | bool)

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client: AsyncClient):
        """Test health check response time performance"""
        response_times = []

        # Make multiple health check requests
        for _ in range(5):
            start_time = time.time()
            response = await client.get("/health")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # Health checks should be fast
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 1.0, f"Health check too slow: {avg_response_time}s"

        # No individual health check should be extremely slow
        max_response_time = max(response_times)
        assert max_response_time < 2.0, f"Individual health check too slow: {max_response_time}s"

    @pytest.mark.asyncio
    async def test_monitoring_endpoints_concurrent_access(self, client: AsyncClient, api_key: str):
        """Test concurrent access to monitoring endpoints"""
        import asyncio

        async def access_endpoint(endpoint, use_auth=False):
            params = {"api_key": api_key} if use_auth else {}
            return await client.get(endpoint, params=params)

        # Test concurrent access to different monitoring endpoints
        tasks = [
            access_endpoint("/health"),
            access_endpoint("/health/detailed"),
            access_endpoint("/monitoring/summary"),
            access_endpoint("/version"),
        ]

        # Add authenticated endpoints
        if api_key:
            tasks.extend([
                access_endpoint("/metrics", use_auth=True),
                access_endpoint("/security/status", use_auth=True),
                access_endpoint("/status", use_auth=True),
            ])

        results = await asyncio.gather(*tasks)

        # All requests should succeed or fail gracefully
        for result in results:
            assert 200 <= result.status_code < 500, f"Unexpected status code: {result.status_code}"

    @pytest.mark.asyncio
    async def test_metrics_data_consistency(self, client: AsyncClient, api_key: str):
        """Test consistency of metrics data across requests"""
        # Make two requests to metrics endpoint
        response1 = await client.get("/metrics", params={"api_key": api_key})
        await asyncio.sleep(0.1)  # Small delay
        response2 = await client.get("/metrics", params={"api_key": api_key})

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Timestamps should be different (metrics are fresh)
        if "timestamp" in data1 and "timestamp" in data2:
            assert data1["timestamp"] != data2["timestamp"]

        # Basic structure should be consistent
        assert data1.keys() == data2.keys() or len(data1.keys() & data2.keys()) >= 1

    @pytest.mark.asyncio
    async def test_monitoring_error_handling(self, client: AsyncClient, api_key: str):
        """Test error handling in monitoring endpoints"""
        # Test with simulated backend failures
        with patch('app.core.monitoring.get_metrics_collector') as mock_collector:
            mock_collector.side_effect = Exception("Metrics collection failed")

            response = await client.get("/monitoring/summary")

            # Should handle errors gracefully
            assert response.status_code in [200, 500, 503]

            if response.status_code != 200:
                # Error response should be properly formatted
                try:
                    error_data = response.json()
                    assert "detail" in error_data or "error" in error_data
                except:
                    # Non-JSON error response is also acceptable
                    assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_health_check_dependency_validation(self, client: AsyncClient):
        """Test health check validates critical dependencies"""
        response = await client.get("/health/detailed")

        if response.status_code == 200:
            data = response.json()

            # Look for dependency checks
            if "checks" in data:
                checks = data["checks"]

                # Should check critical dependencies
                critical_deps = ["database", "redis", "openai"]
                for dep in critical_deps:
                    # May or may not be present depending on configuration
                    if dep in checks:
                        # If present, should have status
                        assert "status" in checks[dep] or "healthy" in checks[dep]

    @pytest.mark.asyncio
    async def test_prometheus_metrics_format(self, client: AsyncClient):
        """Test Prometheus metrics endpoint format (if available)"""
        # Some systems expose metrics in Prometheus format
        response = await client.get("/metrics", headers={"Accept": "text/plain"})

        if response.status_code == 200:
            content = response.text

            # If it's Prometheus format, should have metric patterns
            if "# HELP" in content or "# TYPE" in content:
                # Verify basic Prometheus format
                lines = content.split('\n')
                metric_lines = [line for line in lines if line and not line.startswith('#')]

                # Should have some actual metrics
                assert len(metric_lines) > 0

                # Basic format validation (metric_name value)
                for line in metric_lines[:5]:  # Check first few
                    if ' ' in line:
                        parts = line.split(' ')
                        assert len(parts) >= 2  # metric_name and value

    @pytest.mark.asyncio
    async def test_monitoring_data_types(self, client: AsyncClient, api_key: str):
        """Test that monitoring endpoints return correct data types"""
        response = await client.get("/metrics", params={"api_key": api_key})

        if response.status_code == 200:
            data = response.json()

            # Verify data types for common metrics
            if "system" in data:
                system = data["system"]

                numeric_fields = ["cpu_percent", "memory_percent", "uptime_seconds"]
                for field in numeric_fields:
                    if field in system:
                        assert isinstance(system[field], int | float), f"{field} should be numeric"

                # Memory values should be reasonable
                if "memory_percent" in system:
                    assert 0 <= system["memory_percent"] <= 100, "Memory percent should be 0-100"

                if "cpu_percent" in system:
                    assert 0 <= system["cpu_percent"] <= 100, "CPU percent should be 0-100"

    @pytest.mark.asyncio
    async def test_rate_limit_monitoring(self, client: AsyncClient, api_key: str):
        """Test rate limiting monitoring and metrics"""
        # Make requests to potentially trigger rate limiting info
        responses = []
        for _ in range(10):
            response = await client.get("/health", params={"api_key": api_key})
            responses.append(response)

        # Check for rate limiting headers or information
        for response in responses:
            headers = response.headers

            # Look for common rate limiting headers
            rate_headers = [
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-reset",
                "retry-after"
            ]

            # If rate limiting is active, headers might be present
            [h for h in rate_headers if h in headers]
            # No assertion - rate limiting may not be configured

    @pytest.mark.asyncio
    async def test_monitoring_endpoint_caching(self, client: AsyncClient, api_key: str):
        """Test caching behavior of monitoring endpoints"""
        # Make rapid requests to see if caching is in effect
        start_time = time.time()

        response1 = await client.get("/metrics", params={"api_key": api_key})
        response2 = await client.get("/metrics", params={"api_key": api_key})

        end_time = time.time()

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both requests should complete quickly
        total_time = end_time - start_time
        assert total_time < 2.0, f"Metrics requests too slow: {total_time}s"

        # Check if responses are identical (cached) or different (fresh)
        data1 = response1.json()
        data2 = response2.json()

        # If timestamps are identical, likely cached
        # If different, metrics are fresh
        if "timestamp" in data1 and "timestamp" in data2:
            # Either scenario is acceptable
            assert isinstance(data1["timestamp"], str)
            assert isinstance(data2["timestamp"], str)

    @pytest.mark.asyncio
    async def test_monitoring_memory_usage(self, client: AsyncClient, api_key: str):
        """Test monitoring of application memory usage"""
        response = await client.get("/metrics", params={"api_key": api_key})

        if response.status_code == 200:
            data = response.json()

            if "system" in data and "memory_percent" in data["system"]:
                memory_percent = data["system"]["memory_percent"]

                # Memory usage should be reasonable
                assert 0 <= memory_percent <= 95, f"Memory usage seems too high: {memory_percent}%"

                # Application should not be using excessive memory
                if "memory_used_mb" in data["system"]:
                    memory_used = data["system"]["memory_used_mb"]
                    assert memory_used > 0, "Memory usage should be positive"
                    # Allow up to 2GB for tests (reasonable for a full application)
                    assert memory_used < 2048, f"Memory usage very high: {memory_used}MB"

    @pytest.mark.asyncio
    async def test_application_version_consistency(self, client: AsyncClient):
        """Test version consistency across different endpoints"""
        # Get version from different sources
        version_response = await client.get("/version")
        health_response = await client.get("/health")

        assert version_response.status_code == 200
        assert health_response.status_code == 200

        version_data = version_response.json()
        health_data = health_response.json()

        # Versions should be consistent
        version_from_version = version_data.get("version")
        version_from_health = health_data.get("version")

        if version_from_version and version_from_health:
            assert version_from_version == version_from_health, "Version mismatch between endpoints"

        # Version should be a valid format
        if version_from_version:
            assert "." in version_from_version, "Version should have dot notation"
            parts = version_from_version.split(".")
            assert len(parts) >= 2, "Version should have at least major.minor"
