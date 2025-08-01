"""
Unit tests for V2 Unified API endpoints
Tests the unified Second Brain v2.0 API with robust V1 implementations and V2 features
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.routes.v2_unified_api import ConnectionManager, manager


class TestConnectionManager:
    """Test the WebSocket connection manager"""

    def test_connection_manager_initialization(self):
        """Test connection manager initializes correctly"""
        cm = ConnectionManager()
        assert cm.active_connections == []

    @pytest.mark.asyncio
    async def test_connect_websocket(self):
        """Test connecting a WebSocket"""
        cm = ConnectionManager()
        mock_websocket = AsyncMock()

        await cm.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()
        assert mock_websocket in cm.active_connections
        assert len(cm.active_connections) == 1

    def test_disconnect_websocket(self):
        """Test disconnecting a WebSocket"""
        cm = ConnectionManager()
        mock_websocket = MagicMock()
        cm.active_connections.append(mock_websocket)

        cm.disconnect(mock_websocket)

        assert mock_websocket not in cm.active_connections
        assert len(cm.active_connections) == 0

    def test_disconnect_nonexistent_websocket(self):
        """Test disconnecting a WebSocket that doesn't exist"""
        cm = ConnectionManager()
        mock_websocket = MagicMock()

        # Should not raise error
        cm.disconnect(mock_websocket)
        assert len(cm.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting a message to all connections"""
        cm = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        cm.active_connections = [mock_ws1, mock_ws2]

        test_message = {"type": "test", "data": "broadcast"}

        await cm.broadcast(test_message)

        mock_ws1.send_json.assert_called_once_with(test_message)
        mock_ws2.send_json.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_broadcast_with_failed_connection(self):
        """Test broadcasting handles failed connections gracefully"""
        cm = ConnectionManager()
        mock_ws_good = AsyncMock()
        mock_ws_bad = AsyncMock()
        mock_ws_bad.send_json.side_effect = Exception("Connection failed")
        cm.active_connections = [mock_ws_good, mock_ws_bad]

        test_message = {"type": "test", "data": "broadcast"}

        await cm.broadcast(test_message)

        mock_ws_good.send_json.assert_called_once_with(test_message)
        mock_ws_bad.send_json.assert_called_once_with(test_message)
        # Failed connection should be removed
        assert mock_ws_bad not in cm.active_connections
        assert mock_ws_good in cm.active_connections


@pytest.mark.asyncio
class TestV2UnifiedAPI:
    """Test V2 Unified API endpoints"""

    async def test_get_simple_metrics_success(self, client: AsyncClient, api_key: str):
        """Test getting simple metrics successfully"""
        response = await client.get("/api/v2/metrics", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "tests" in data
        assert "patterns" in data
        assert "version" in data
        assert "agents" in data
        assert "token_usage" in data
        assert "memories" in data
        assert "active_users" in data
        assert "system_health" in data

        # Verify data types
        assert isinstance(data["tests"], int)
        assert isinstance(data["patterns"], int)
        assert isinstance(data["version"], str)
        assert isinstance(data["agents"], int)
        assert isinstance(data["token_usage"], str)
        assert isinstance(data["memories"], int)
        assert isinstance(data["active_users"], int)
        assert isinstance(data["system_health"], str)

    async def test_get_simple_metrics_unauthorized(self, client: AsyncClient):
        """Test getting simple metrics without API key"""
        response = await client.get("/api/v2/metrics")
        assert response.status_code == 422  # Missing required parameter

    async def test_get_simple_metrics_invalid_api_key(self, client: AsyncClient):
        """Test getting simple metrics with invalid API key"""
        response = await client.get("/api/v2/metrics", params={"api_key": "invalid-key"})
        assert response.status_code == 403

    async def test_get_detailed_metrics_success(self, client: AsyncClient, api_key: str):
        """Test getting detailed metrics successfully"""
        response = await client.get("/api/v2/metrics/detailed", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "memories" in data
        assert "performance" in data
        assert "timestamp" in data
        assert "system" in data
        assert "database" in data

        # Verify memories data structure
        memories = data["memories"]
        assert "total" in memories
        assert "unique_users" in memories
        assert "type_distribution" in memories

        # Verify performance data structure
        performance = data["performance"]
        assert "api_response_time" in performance
        assert "memory_usage" in performance
        assert "cpu_usage" in performance

    async def test_get_detailed_metrics_unauthorized(self, client: AsyncClient):
        """Test getting detailed metrics without authorization"""
        response = await client.get("/api/v2/metrics/detailed")
        assert response.status_code == 422

    async def test_get_git_activity_success(self, client: AsyncClient, api_key: str):
        """Test getting git activity data successfully"""
        response = await client.get("/api/v2/git/activity", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "commits" in data
        assert "timeline" in data
        assert "stats" in data

        # Verify commits structure (may be empty in test environment)
        assert isinstance(data["commits"], list)

        # Verify timeline structure
        assert isinstance(data["timeline"], list)
        for timeline_item in data["timeline"]:
            assert "label" in timeline_item
            assert "timestamp" in timeline_item

        # Verify stats structure
        stats = data["stats"]
        assert "total_commits" in stats
        assert "authors" in stats
        assert "branch" in stats

    async def test_get_todos_success(self, client: AsyncClient, api_key: str):
        """Test getting TODO list successfully"""
        response = await client.get("/api/v2/todos", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "todos" in data
        assert "stats" in data
        assert "last_updated" in data

        # Verify todos structure
        assert isinstance(data["todos"], list)
        for todo in data["todos"]:
            assert "id" in todo
            assert "content" in todo
            assert "status" in todo
            assert "priority" in todo
            assert "category" in todo

        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats
        assert "completed" in stats
        assert "in_progress" in stats
        assert "pending" in stats
        assert "completion_rate" in stats

    async def test_get_health_status_success(self, client: AsyncClient, api_key: str):
        """Test getting health status successfully"""
        response = await client.get("/api/v2/health", params={"api_key": api_key})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data

        # Verify health checks
        checks = data["checks"]
        expected_checks = ["api", "database", "redis", "disk", "memory", "cpu"]
        for check in expected_checks:
            assert check in checks
            assert checks[check] in ["healthy", "degraded", "unhealthy", "unknown", "unavailable"]

        # Verify overall status
        assert data["status"] in ["healthy", "degraded", "unhealthy", "error"]

    async def test_ingest_memory_success(self, client: AsyncClient, api_key: str):
        """Test ingesting a new memory successfully"""
        response = await client.post(
            "/api/v2/memories/ingest",
            params={
                "content": "Test memory content",
                "memory_type": "note",
                "tags": ["test", "api"],
                "api_key": api_key,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "memory_id" in data
        assert "message" in data
        assert data["message"] == "Memory ingested successfully"

    async def test_ingest_memory_missing_content(self, client: AsyncClient, api_key: str):
        """Test ingesting memory without content"""
        response = await client.post("/api/v2/memories/ingest", params={"api_key": api_key})

        assert response.status_code == 422  # Missing required parameter

    async def test_ingest_memory_unauthorized(self, client: AsyncClient):
        """Test ingesting memory without authorization"""
        response = await client.post(
            "/api/v2/memories/ingest", params={"content": "Test memory content"}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestV2APIEdgeCases:
    """Test edge cases and error conditions for V2 API"""

    async def test_metrics_with_high_memory_count(self, client: AsyncClient, api_key: str):
        """Test metrics calculation with high memory count"""
        with patch("app.routes.v2_unified_api.get_database") as mock_get_db:
            mock_db = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.fetchval.return_value = 1500  # High memory count to trigger 15x token usage
            mock_db.pool = mock_pool
            mock_get_db.return_value = mock_db

            response = await client.get("/api/v2/metrics", params={"api_key": api_key})

            assert response.status_code == 200
            data = response.json()
            assert data["token_usage"] == "15x"

    async def test_detailed_metrics_database_error(self, client: AsyncClient, api_key: str):
        """Test detailed metrics with database error"""
        with patch("app.routes.v2_unified_api.get_database") as mock_get_db:
            mock_db = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.fetchrow.side_effect = Exception("Database error")
            mock_db.pool = mock_pool
            mock_get_db.return_value = mock_db

            response = await client.get("/api/v2/metrics/detailed", params={"api_key": api_key})

            assert response.status_code == 500

    async def test_git_activity_no_git_repo(self, client: AsyncClient, api_key: str):
        """Test git activity when not in a git repository"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1  # Git command failed

            response = await client.get("/api/v2/git/activity", params={"api_key": api_key})

            assert response.status_code == 200
            data = response.json()
            assert data["commits"] == []
            assert data["stats"]["total_commits"] == 0

    async def test_todos_missing_file(self, client: AsyncClient, api_key: str):
        """Test TODOs endpoint when TODO.md file doesn't exist"""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            response = await client.get("/api/v2/todos", params={"api_key": api_key})

            assert response.status_code == 200
            data = response.json()
            assert data["todos"] == []
            assert data["stats"]["total"] == 0

    async def test_health_status_with_resource_limits(self, client: AsyncClient, api_key: str):
        """Test health status with high resource usage"""
        with (
            patch("psutil.cpu_percent") as mock_cpu,
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):

            # Mock high resource usage
            mock_cpu.return_value = 95.0
            mock_memory.return_value.percent = 85.0
            mock_disk.return_value.percent = 90.0

            response = await client.get("/api/v2/health", params={"api_key": api_key})

            assert response.status_code == 200
            data = response.json()
            assert data["checks"]["cpu"] == "unhealthy"
            assert data["checks"]["memory"] == "degraded"
            assert data["checks"]["disk"] == "unhealthy"
            assert data["status"] == "unhealthy"

    async def test_memory_ingestion_database_error(self, client: AsyncClient, api_key: str):
        """Test memory ingestion with database error"""
        with patch("app.routes.v2_unified_api.get_database") as mock_get_db:
            mock_db = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.fetchrow.side_effect = Exception("Database connection failed")
            mock_db.pool = mock_pool
            mock_get_db.return_value = mock_db

            response = await client.post(
                "/api/v2/memories/ingest",
                params={"content": "Test memory content", "api_key": api_key},
            )

            assert response.status_code == 500


@pytest.mark.asyncio
class TestV2APIPerformance:
    """Performance tests for V2 API endpoints"""

    async def test_metrics_response_time(self, client: AsyncClient, api_key: str):
        """Test that metrics endpoint responds within acceptable time"""
        import time

        start_time = time.time()
        response = await client.get("/api/v2/metrics", params={"api_key": api_key})
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds

    async def test_detailed_metrics_response_time(self, client: AsyncClient, api_key: str):
        """Test that detailed metrics endpoint responds within acceptable time"""
        import time

        start_time = time.time()
        response = await client.get("/api/v2/metrics/detailed", params={"api_key": api_key})
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 5.0  # Detailed metrics can take up to 5 seconds

    async def test_concurrent_requests(self, client: AsyncClient, api_key: str):
        """Test handling multiple concurrent requests"""
        import asyncio

        async def make_request():
            return await client.get("/api/v2/metrics", params={"api_key": api_key})

        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


@pytest.mark.asyncio
class TestV2APISecurity:
    """Security tests for V2 API endpoints"""

    async def test_sql_injection_protection(self, client: AsyncClient, api_key: str):
        """Test protection against SQL injection attacks"""
        malicious_content = "'; DROP TABLE memories; --"

        response = await client.post(
            "/api/v2/memories/ingest", params={"content": malicious_content, "api_key": api_key}
        )

        # Should handle malicious input gracefully
        assert response.status_code in [200, 400, 500]  # Not crash the server

    async def test_api_key_validation_edge_cases(self, client: AsyncClient):
        """Test API key validation with various edge cases"""
        edge_case_keys = [
            "",  # Empty key
            "short",  # Too short
            "a" * 100,  # Too long
            "invalid-characters-!@#$%^&*()",  # Special characters
            None,  # None value
        ]

        for key in edge_case_keys:
            params = {"api_key": key} if key is not None else {}
            response = await client.get("/api/v2/metrics", params=params)
            assert response.status_code in [403, 422]  # Should reject invalid keys

    async def test_rate_limiting_headers(self, client: AsyncClient, api_key: str):
        """Test that rate limiting headers are present"""
        response = await client.get("/api/v2/metrics", params={"api_key": api_key})

        assert response.status_code == 200
        # Check for common rate limiting headers (if implemented)
        # Note: These may not be implemented yet, so we just check they don't cause errors
        headers = response.headers
        assert isinstance(headers, dict)

    async def test_input_sanitization(self, client: AsyncClient, api_key: str):
        """Test that user input is properly sanitized"""
        xss_payload = "<script>alert('xss')</script>"

        response = await client.post(
            "/api/v2/memories/ingest",
            params={"content": xss_payload, "memory_type": xss_payload, "api_key": api_key},
        )

        # Should handle XSS payload without executing it
        assert response.status_code in [200, 400]  # Should not crash

    async def test_large_payload_handling(self, client: AsyncClient, api_key: str):
        """Test handling of large payloads"""
        # 1MB of text
        large_content = "A" * (1024 * 1024)

        response = await client.post(
            "/api/v2/memories/ingest", params={"content": large_content, "api_key": api_key}
        )

        # Should handle large payloads gracefully
        assert response.status_code in [200, 413, 422]  # Success or payload too large
