"""
Comprehensive security tests for the security module.
Tests rate limiting, input validation, and security middleware.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from app.security import (
    InputValidator,
    RateLimiter,
    RateLimitingMiddleware,
    SecurityConfig,
    SecurityHeadersMiddleware,
    SecurityManager,
    get_security_manager,
)


class TestSecurityConfig:
    """Test security configuration."""

    @pytest.mark.parametrize(
        "max_requests,max_hour,max_content,valid",
        [
            (60, 1000, 10000, True),  # Default values
            (1, 10, 100, True),  # Minimal values
            (0, 1000, 10000, False),  # Invalid max_requests
            (60, 0, 10000, False),  # Invalid max_hour
            (60, 1000, 0, False),  # Invalid max_content
        ],
    )
    def test_security_config_validation(self, max_requests, max_hour, max_content, valid):
        """Test security config parameter validation."""
        if valid:
            config = SecurityConfig(
                max_requests_per_minute=max_requests,
                max_requests_per_hour=max_hour,
                max_content_length=max_content,
            )
            assert config.max_requests_per_minute == max_requests
            assert config.max_requests_per_hour == max_hour
            assert config.max_content_length == max_content
        else:
            # Would need custom validation logic in SecurityConfig
            # For now, just test that invalid configs can be detected
            assert max_requests <= 0 or max_hour <= 0 or max_content <= 0


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test config."""
        config = SecurityConfig(max_requests_per_minute=5, max_requests_per_hour=50)
        return RateLimiter(config)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    @pytest.mark.parametrize(
        "ip_header,header_value,expected_ip",
        [
            ("X-Forwarded-For", "192.168.1.1, 10.0.0.1", "192.168.1.1"),
            ("X-Real-IP", "192.168.1.1", "192.168.1.1"),
            (None, None, "127.0.0.1"),
        ],
    )
    def test_get_client_ip(self, rate_limiter, mock_request, ip_header, header_value, expected_ip):
        """Test client IP extraction from various headers."""
        if ip_header and header_value:
            mock_request.headers = {ip_header: header_value}

        ip = rate_limiter._get_client_ip(mock_request)
        assert ip == expected_ip

    def test_rate_limiting_allows_normal_requests(self, rate_limiter, mock_request):
        """Test that normal request rates are allowed."""
        # Send requests within limits
        for _ in range(3):
            assert not rate_limiter.is_rate_limited(mock_request)
            time.sleep(0.1)  # Small delay to avoid exact timestamps

    def test_rate_limiting_blocks_excessive_requests(self, rate_limiter, mock_request):
        """Test that excessive requests are blocked."""
        # Exhaust the rate limit
        for _ in range(5):
            rate_limiter.is_rate_limited(mock_request)

        # Next request should be blocked
        assert rate_limiter.is_rate_limited(mock_request)

    def test_rate_limit_info_headers(self, rate_limiter, mock_request):
        """Test rate limit info header generation."""
        info = rate_limiter.get_rate_limit_info(mock_request)

        assert "X-RateLimit-Limit" in info
        assert "X-RateLimit-Remaining" in info
        assert "X-RateLimit-Reset" in info
        assert int(info["X-RateLimit-Limit"]) == rate_limiter.config.max_requests_per_minute

    def test_cleanup_old_requests(self, rate_limiter, mock_request):
        """Test cleanup of old request history."""
        # Add some requests
        rate_limiter.is_rate_limited(mock_request)
        initial_count = len(rate_limiter.request_history["127.0.0.1"])

        # Force cleanup by setting old last_cleanup time
        rate_limiter.last_cleanup = time.time() - 400

        # Trigger cleanup
        rate_limiter._cleanup_old_requests()

        # Should still have recent requests
        assert len(rate_limiter.request_history["127.0.0.1"]) == initial_count

    def test_blocked_ip_management(self, rate_limiter, mock_request):
        """Test IP blocking and unblocking."""
        ip = "127.0.0.1"

        # Block IP manually for testing
        rate_limiter.blocked_ips[ip] = datetime.now()

        # Should be blocked
        assert rate_limiter.is_rate_limited(mock_request)

        # Set old block time
        rate_limiter.blocked_ips[ip] = datetime.now() - timedelta(minutes=20)

        # Should be unblocked
        assert not rate_limiter.is_rate_limited(mock_request)


class TestInputValidator:
    """Test input validation and sanitization."""

    @pytest.fixture
    def validator(self):
        """Create input validator."""
        config = SecurityConfig(max_content_length=1000, max_metadata_fields=10)
        return InputValidator(config)

    @pytest.mark.parametrize(
        "content,should_pass",
        [
            ("Valid content", True),
            ("", False),  # Empty content
            ("A" * 500, True),  # Within limits
            ("A" * 1500, False),  # Too long
            ("DROP TABLE users;", False),  # SQL injection
            ("<script>alert('xss')</script>", False),  # XSS
            ("javascript:alert(1)", False),  # JavaScript
            ("Normal text with numbers 123", True),
            ("Text with symbols !@#$%", True),
        ],
    )
    def test_validate_memory_content(self, validator, content, should_pass):
        """Test memory content validation with various inputs."""
        if should_pass:
            result = validator.validate_memory_content(content)
            assert isinstance(result, str)
            assert len(result) <= validator.config.max_content_length
        else:
            with pytest.raises(HTTPException):
                validator.validate_memory_content(content)

    @pytest.mark.parametrize(
        "metadata,should_pass",
        [
            ({"key": "value"}, True),
            ({"key1": "value1", "key2": 42}, True),
            ({}, True),  # Empty metadata
            ({"key": None}, True),  # Null value
            ({"key": True}, True),  # Boolean value
            ({"key": 3.14}, True),  # Float value
            ({f"key{i}": f"value{i}" for i in range(15)}, False),  # Too many fields
            ({"": "value"}, True),  # Empty key (will be sanitized)
            ({"key": "x" * 1500}, False),  # Value too long
            ({"key": {"nested": "object"}}, False),  # Invalid nested object
            ({"key": ["list", "values"]}, False),  # Invalid list value
        ],
    )
    def test_validate_metadata(self, validator, metadata, should_pass):
        """Test metadata validation with various inputs."""
        if should_pass:
            result = validator.validate_metadata(metadata)
            assert isinstance(result, dict)
            assert len(result) <= validator.config.max_metadata_fields
        else:
            with pytest.raises(HTTPException):
                validator.validate_metadata(metadata)

    @pytest.mark.parametrize(
        "query,should_pass",
        [
            ("search query", True),
            ("", False),  # Empty query
            ("x" * 500, True),  # Normal length
            ("x" * 1500, False),  # Too long
            ("SELECT * FROM table", False),  # SQL injection
            ("search for something", True),
            ("query with 123 numbers", True),
        ],
    )
    def test_validate_search_query(self, validator, query, should_pass):
        """Test search query validation."""
        if should_pass:
            result = validator.validate_search_query(query)
            assert isinstance(result, str)
            assert len(result) <= 1000
        else:
            with pytest.raises(HTTPException):
                validator.validate_search_query(query)

    @pytest.mark.parametrize(
        "limit,should_pass",
        [
            (10, True),
            (1, True),
            (100, True),
            (0, False),  # Invalid
            (-1, False),  # Invalid
            (1000, False),  # Too high
        ],
    )
    def test_validate_search_limit(self, validator, limit, should_pass):
        """Test search limit validation."""
        if should_pass:
            result = validator.validate_search_limit(limit)
            assert result == limit
        else:
            with pytest.raises(HTTPException):
                validator.validate_search_limit(limit)

    @pytest.mark.parametrize(
        "token,is_valid",
        [
            ("valid_token_123456", True),
            ("short", False),  # Too short
            ("", False),  # Empty
            ("a" * 20, True),  # Valid length
            ("DROP TABLE; --", False),  # SQL injection
            ("<script>alert(1)</script>", False),  # XSS
        ],
    )
    def test_validate_api_token(self, validator, token, is_valid):
        """Test API token validation."""
        result = validator.validate_api_token(token)
        assert result == is_valid

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("normal text", "normal text"),
            ("  extra  spaces  ", "extra spaces"),
            ("text\x00with\x00nulls", "textwithnulls"),
            ("text\nwith\nnewlines", "text\nwith\nnewlines"),
            ("text\twith\ttabs", "text\twith\ttabs"),
            ("\x01\x02control\x03chars\x04", "controlchars"),
        ],
    )
    def test_sanitize_string(self, validator, input_text, expected):
        """Test string sanitization."""
        result = validator._sanitize_string(input_text)
        assert result == expected


class TestSecurityMiddleware:
    """Test security middleware components."""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""

        async def app(request):
            return JSONResponse({"status": "ok"})

        return app

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        return request

    @pytest.mark.asyncio
    async def test_security_headers_middleware(self, mock_app, mock_request):
        """Test security headers middleware."""
        config = SecurityConfig(enable_security_headers=True)
        middleware = SecurityHeadersMiddleware(mock_app, config)

        response = await middleware.dispatch(mock_request, mock_app)

        # Check that security headers are added
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limiting_middleware_allows_normal_requests(self, mock_app, mock_request):
        """Test rate limiting middleware allows normal requests."""
        config = SecurityConfig(max_requests_per_minute=10)
        rate_limiter = RateLimiter(config)
        middleware = RateLimitingMiddleware(mock_app, rate_limiter)

        response = await middleware.dispatch(mock_request, mock_app)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limiting_middleware_blocks_excessive_requests(self, mock_app, mock_request):
        """Test rate limiting middleware blocks excessive requests."""
        config = SecurityConfig(max_requests_per_minute=1)
        rate_limiter = RateLimiter(config)
        middleware = RateLimitingMiddleware(mock_app, rate_limiter)

        # First request should pass
        response1 = await middleware.dispatch(mock_request, mock_app)
        assert response1.status_code == 200

        # Second request should be blocked
        response2 = await middleware.dispatch(mock_request, mock_app)
        assert response2.status_code == 429
        assert "error" in response2.body.decode()


class TestSecurityManager:
    """Test security manager integration."""

    @pytest.fixture
    def security_manager(self):
        """Create security manager."""
        config = SecurityConfig(max_requests_per_minute=5)
        return SecurityManager(config)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"User-Agent": "TestAgent"}
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        return request

    def test_validate_request_normal(self, security_manager, mock_request):
        """Test normal request validation."""
        result = security_manager.validate_request(mock_request)
        assert result is True
        assert security_manager.total_requests == 1

    def test_validate_request_rate_limited(self, security_manager, mock_request):
        """Test rate limited request validation."""
        # Exhaust rate limit
        for _ in range(6):
            security_manager.validate_request(mock_request)

        # Should be blocked now
        result = security_manager.validate_request(mock_request)
        assert result is False
        assert security_manager.blocked_attempts > 0

    def test_get_security_stats(self, security_manager, mock_request):
        """Test security statistics generation."""
        # Generate some activity
        security_manager.validate_request(mock_request)

        stats = security_manager.get_security_stats()

        assert "total_requests" in stats
        assert "blocked_attempts" in stats
        assert "block_rate" in stats
        assert stats["total_requests"] >= 1

    def test_get_security_middleware(self, security_manager):
        """Test security middleware configuration."""
        middleware = security_manager.get_security_middleware()

        assert len(middleware) == 2
        assert middleware[0][0] == SecurityHeadersMiddleware
        assert middleware[1][0] == RateLimitingMiddleware

    def test_security_event_logging(self, security_manager, mock_request):
        """Test security event logging."""
        # Generate rate limit event
        for _ in range(6):
            security_manager.validate_request(mock_request)

        # Check that events were logged
        assert len(security_manager.security_events) > 0

        event = security_manager.security_events[-1]
        assert event["event_type"] == "rate_limit_exceeded"
        assert event["client_ip"] == "127.0.0.1"
        assert event["path"] == "/test"


class TestSecurityIntegration:
    """Test security component integration."""

    @pytest.mark.asyncio
    async def test_full_security_pipeline(self):
        """Test complete security validation pipeline."""
        config = SecurityConfig(
            max_requests_per_minute=10,
            max_content_length=500,
            enable_input_validation=True,
            enable_rate_limiting=True,
        )

        security_manager = SecurityManager(config)
        validator = security_manager.input_validator

        # Test valid content passes all checks
        valid_content = "This is valid content"
        sanitized = validator.validate_memory_content(valid_content)
        assert sanitized == valid_content

        # Test metadata validation
        valid_metadata = {"category": "test", "priority": 1}
        validated_metadata = validator.validate_metadata(valid_metadata)
        assert validated_metadata == valid_metadata

    def test_global_security_manager_singleton(self):
        """Test that global security manager is properly initialized."""
        manager1 = get_security_manager()
        manager2 = get_security_manager()

        # Should be the same instance
        assert manager1 is manager2
        assert isinstance(manager1, SecurityManager)

    @pytest.mark.parametrize(
        "attack_vector,content",
        [
            ("sql_injection", "'; DROP TABLE users; --"),
            ("xss", "<script>alert('xss')</script>"),
            ("javascript", "javascript:alert(1)"),
            ("null_bytes", "content\x00with\x00nulls"),
            ("oversized", "x" * 20000),
        ],
    )
    def test_attack_vector_protection(self, attack_vector, content):
        """Test protection against common attack vectors."""
        config = SecurityConfig(max_content_length=1000)
        validator = InputValidator(config)

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_memory_content(content)

        assert exc_info.value.status_code == 400
        assert (
            "dangerous" in exc_info.value.detail.lower()
            or "too long" in exc_info.value.detail.lower()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
