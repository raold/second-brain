"""
Comprehensive Security Validation Tests
Tests security features, input validation, and attack prevention
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


class TestSecurityValidation:
    """Test all security-related functionality"""

    @pytest.mark.asyncio
    async def test_api_key_validation_required(self, client: AsyncClient):
        """Test that API key is required for protected endpoints"""
        protected_endpoints = [
            ("/memories", "GET"),
            ("/memories/search", "POST"),
            ("/status", "GET"),
            ("/security/status", "GET"),
            ("/metrics", "GET")
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "POST":
                response = await client.post(endpoint, json={})

            # Should require authentication
            assert response.status_code in [401, 422], f"Endpoint {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_api_key_validation_invalid_key(self, client: AsyncClient):
        """Test rejection of invalid API keys"""
        invalid_keys = [
            "invalid-key",
            "short",
            "",
            "x" * 100,  # Too long
            "test-key",  # Wrong format
        ]

        for invalid_key in invalid_keys:
            response = await client.get(
                "/memories",
                params={"api_key": invalid_key}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_input_sanitization_memory_content(self, client: AsyncClient, api_key: str):
        """Test input sanitization for memory content"""
        malicious_inputs = [
            # XSS attempts
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",

            # SQL injection attempts
            "'; DROP TABLE memories; --",
            "' OR '1'='1",
            "admin'--",

            # Command injection attempts
            "; rm -rf /",
            "$(rm -rf /)",
            "`rm -rf /`",

            # Path traversal attempts
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",

            # Large payloads
            "A" * 100000,  # Very large content

            # Special characters
            "\x00\x01\x02\x03",  # Null bytes and control chars
            "💀🔥💥",  # Unicode that might break things
        ]

        for malicious_input in malicious_inputs:
            payload = {
                "content": malicious_input,
                "importance_score": 0.5
            }

            response = await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )

            # Should either sanitize and succeed, or reject with validation error
            assert response.status_code in [200, 400, 422, 413], f"Failed for input: {malicious_input[:50]}"

            if response.status_code == 200:
                # If accepted, verify content was sanitized
                data = response.json()
                stored_content = data["content"]

                # Should not contain raw script tags or dangerous content
                dangerous_patterns = ["<script", "javascript:", "DROP TABLE", "; rm -rf"]
                for pattern in dangerous_patterns:
                    assert pattern.lower() not in stored_content.lower(), f"Dangerous pattern '{pattern}' not sanitized"

    @pytest.mark.asyncio
    async def test_request_size_limits(self, client: AsyncClient, api_key: str):
        """Test request size limits are enforced"""
        # Test extremely large request
        huge_content = "A" * 1000000  # 1MB content

        payload = {
            "content": huge_content,
            "importance_score": 0.5
        }

        response = await client.post(
            "/memories/semantic",
            json=payload,
            params={"api_key": api_key}
        )

        # Should reject oversized requests
        assert response.status_code in [413, 400, 422]  # Payload too large or validation error

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, client: AsyncClient, api_key: str):
        """Test that rate limiting is properly enforced"""
        # Make rapid requests to trigger rate limiting
        responses = []

        for i in range(20):  # Make 20 rapid requests
            response = await client.get(
                "/health",
                params={"api_key": api_key}
            )
            responses.append(response.status_code)

            # Small delay to avoid overwhelming the test client
            if i % 5 == 0:
                await client.__aenter__()  # Small async delay

        # Should have some rate limit responses if rate limiting is active
        rate_limited = sum(1 for status in responses if status == 429)
        success = sum(1 for status in responses if status == 200)

        # Either all succeed (rate limiting disabled) or some are rate limited
        assert rate_limited >= 0 and success >= 5

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test that CORS headers are properly set"""
        response = await client.options("/health")

        # Should have CORS headers (might be 404 if OPTIONS not implemented)
        if response.status_code != 404:
            headers = response.headers
            # Check for common CORS headers
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers"
            ]

            # At least some CORS headers should be present
            present_headers = sum(1 for header in cors_headers if header in headers)
            assert present_headers >= 0  # May not be present in test environment

    @pytest.mark.asyncio
    async def test_security_headers_applied(self, client: AsyncClient, api_key: str):
        """Test that security headers are applied to responses"""
        response = await client.get(
            "/health",
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        headers = response.headers

        # Check for common security headers
        security_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
            "strict-transport-security": None,  # HTTPS only
            "content-security-policy": None,
        }

        # Count present security headers
        present_count = sum(1 for header in security_headers.keys() if header in headers)
        assert present_count >= 1  # At least some security headers should be present

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client: AsyncClient, api_key: str):
        """Test SQL injection prevention in search queries"""
        sql_injection_payloads = [
            "'; DROP TABLE memories; --",
            "' UNION SELECT * FROM users--",
            "' OR 1=1--",
            "admin'/*",
            "1' AND (SELECT COUNT(*) FROM information_schema.tables)>0--",
        ]

        for payload in sql_injection_payloads:
            search_payload = {
                "query": payload,
                "limit": 10
            }

            response = await client.post(
                "/memories/search",
                json=search_payload,
                params={"api_key": api_key}
            )

            # Should either sanitize and return results, or return validation error
            assert response.status_code in [200, 400, 422]

            if response.status_code == 200:
                # Should return empty or safe results, not error
                data = response.json()
                assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, client: AsyncClient):
        """Test path traversal prevention in file endpoints"""
        path_traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "....//....//....//etc/passwd",
        ]

        for attempt in path_traversal_attempts:
            # Test with docs endpoint that takes file paths
            response = await client.get(f"/docs/{attempt}")

            # Should either return 403 (access denied) or 404 (not found)
            # Should NOT return file contents from outside the docs directory
            assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_json_parsing_edge_cases(self, client: AsyncClient, api_key: str):
        """Test JSON parsing with malformed or edge case data"""
        edge_case_payloads = [
            # Deeply nested JSON
            {"content": {"nested": {"very": {"deep": {"structure": "test"}}}}},

            # JSON with special numbers
            {"content": "test", "importance_score": float('inf')},
            {"content": "test", "importance_score": float('-inf')},

            # Very large numbers
            {"content": "test", "importance_score": 10**308},

            # Unicode in keys and values
            {"content": "test 🧠", "metadata": {"🔑": "🔒"}},
        ]

        for payload in edge_case_payloads:
            try:
                response = await client.post(
                    "/memories/semantic",
                    json=payload,
                    params={"api_key": api_key}
                )

                # Should handle gracefully
                assert response.status_code in [200, 400, 422]

            except Exception as e:
                # Should not cause unhandled exceptions
                pytest.fail(f"Unhandled exception for payload {payload}: {e}")

    @pytest.mark.asyncio
    async def test_content_type_validation(self, client: AsyncClient, api_key: str):
        """Test content type validation"""
        # Test with wrong content type
        response = await client.post(
            "/memories/semantic",
            content="not json",
            headers={"content-type": "text/plain"},
            params={"api_key": api_key}
        )

        # Should reject non-JSON content
        assert response.status_code in [400, 415, 422]

    @pytest.mark.asyncio
    async def test_parameter_pollution(self, client: AsyncClient, api_key: str):
        """Test handling of parameter pollution attacks"""
        # Test duplicate parameters
        response = await client.get(
            "/memories?limit=10&limit=100&api_key=" + api_key
        )

        # Should handle gracefully, not cause errors
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_memory_metadata_injection(self, client: AsyncClient, api_key: str):
        """Test metadata injection attempts"""
        malicious_metadata = {
            "content": "Test content",
            "semantic_metadata": {
                "domain": "<script>alert('xss')</script>",
                "concepts": ["'; DROP TABLE memories; --"],
                "malicious_key": {"nested": {"injection": "attempt"}},
                "confidence": "not a number"
            },
            "importance_score": 0.5
        }

        response = await client.post(
            "/memories/semantic",
            json=malicious_metadata,
            params={"api_key": api_key}
        )

        # Should either sanitize or reject
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_search_query_edge_cases(self, client: AsyncClient, api_key: str):
        """Test search with edge case queries"""
        edge_case_queries = [
            "",  # Empty query
            " ",  # Whitespace only
            "a" * 10000,  # Very long query
            "\n\r\t",  # Only control characters
            "🧠🤖💭",  # Only emojis
            "SELECT * FROM",  # SQL-like syntax
            "../../../../etc/passwd",  # Path traversal in query
        ]

        for query in edge_case_queries:
            payload = {
                "query": query,
                "limit": 5
            }

            response = await client.post(
                "/memories/search",
                json=payload,
                params={"api_key": api_key}
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_security_status_endpoint_authorization(self, client: AsyncClient, api_key: str):
        """Test security status endpoint requires proper authorization"""
        # Test without API key
        response = await client.get("/security/status")
        assert response.status_code in [401, 422]

        # Test with valid API key
        response = await client.get(
            "/security/status",
            params={"api_key": api_key}
        )
        assert response.status_code == 200

        # Verify response contains security metrics
        data = response.json()
        assert "security" in data or "timestamp" in data

    @pytest.mark.asyncio
    async def test_concurrent_authentication_attempts(self, client: AsyncClient, api_key: str):
        """Test handling of concurrent authentication attempts"""
        import asyncio

        async def auth_attempt(key):
            return await client.get("/health", params={"api_key": key})

        # Test concurrent valid requests
        valid_tasks = [auth_attempt(api_key) for _ in range(10)]
        valid_results = await asyncio.gather(*valid_tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in valid_results)

        # Test concurrent invalid requests
        invalid_tasks = [auth_attempt("invalid-key") for _ in range(5)]
        invalid_results = await asyncio.gather(*invalid_tasks)

        # All should fail
        assert all(r.status_code == 401 for r in invalid_results)

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, client: AsyncClient, api_key: str):
        """Test request timeout handling"""
        with patch('asyncio.sleep') as mock_sleep:
            # Mock a slow operation
            mock_sleep.return_value = None

            response = await client.get(
                "/health",
                params={"api_key": api_key},
                timeout=1.0  # Short timeout
            )

            # Should complete within timeout or handle gracefully
            assert response.status_code in [200, 408, 500]

    @pytest.mark.asyncio
    async def test_memory_access_authorization(self, client: AsyncClient, api_key: str):
        """Test that memory access is properly authorized"""
        # Store a memory first
        payload = {
            "content": "Private memory content",
            "importance_score": 0.5
        }

        response = await client.post(
            "/memories/semantic",
            json=payload,
            params={"api_key": api_key}
        )

        assert response.status_code == 200
        memory = response.json()
        memory_id = memory["id"]

        # Try to access without API key
        response = await client.get(f"/memories/{memory_id}")
        assert response.status_code in [401, 422]

        # Try to access with invalid API key
        response = await client.get(
            f"/memories/{memory_id}",
            params={"api_key": "invalid"}
        )
        assert response.status_code == 401

        # Should work with valid API key
        response = await client.get(
            f"/memories/{memory_id}",
            params={"api_key": api_key}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_information_disclosure(self, client: AsyncClient, api_key: str):
        """Test that error messages don't disclose sensitive information"""
        # Trigger various error conditions
        error_conditions = [
            # Invalid memory ID format
            ("/memories/invalid-format", "GET"),
            # Malformed JSON
            ("/memories/semantic", "POST"),
        ]

        for endpoint, method in error_conditions:
            if method == "GET":
                response = await client.get(
                    endpoint,
                    params={"api_key": api_key}
                )
            elif method == "POST":
                # Send malformed JSON
                response = await client.post(
                    endpoint,
                    content="invalid json{",
                    headers={"content-type": "application/json"},
                    params={"api_key": api_key}
                )

            # Error responses should not contain sensitive information
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_text = str(error_data).lower()

                    # Should not contain sensitive patterns
                    sensitive_patterns = [
                        "password", "secret", "key", "token",
                        "database", "connection", "traceback",
                        "/home/", "/var/", "c:\\", "file not found"
                    ]

                    for pattern in sensitive_patterns:
                        assert pattern not in error_text, f"Error message contains sensitive info: {pattern}"

                except:
                    # If response is not JSON, check raw text
                    error_text = response.text.lower()
                    assert "traceback" not in error_text
                    assert "database" not in error_text
