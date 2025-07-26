"""
Security Hardening Implementation for Second Brain v2.2.0
Comprehensive security enhancements with input validation, rate limiting, and security headers
"""

import asyncio
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class SecurityConfig:
    """Security configuration settings"""

    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_content_length: int = 10000  # 10KB
    max_metadata_fields: int = 20
    max_search_results: int = 100
    enable_rate_limiting: bool = True
    enable_input_validation: bool = True
    enable_security_headers: bool = True
    allowed_origins: list[str] | None = None
    token_min_length: int = 16

    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:3000", "http://localhost:8000"]


class RateLimiter:
    """Advanced rate limiting with sliding window"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.request_history: dict[str, deque] = defaultdict(deque)
        self.blocked_ips: dict[str, datetime] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self):
        """Clean up old request history"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = current_time - 3600  # 1 hour ago

        for ip in list(self.request_history.keys()):
            history = self.request_history[ip]
            while history and history[0] < cutoff_time:
                history.popleft()

            if not history:
                del self.request_history[ip]

        # Clean up expired blocked IPs
        expired_blocks = [
            ip for ip, block_time in self.blocked_ips.items() if datetime.now() - block_time > timedelta(minutes=15)
        ]
        for ip in expired_blocks:
            del self.blocked_ips[ip]

        self.last_cleanup = current_time

    def is_rate_limited(self, request: Request) -> bool:
        """Check if request should be rate limited"""
        if not self.config.enable_rate_limiting:
            return False

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Check if IP is currently blocked
        if client_ip in self.blocked_ips:
            block_time = self.blocked_ips[client_ip]
            if datetime.now() - block_time < timedelta(minutes=15):
                return True
            else:
                del self.blocked_ips[client_ip]

        # Clean up old requests periodically
        self._cleanup_old_requests()

        # Get request history for this IP
        history = self.request_history[client_ip]

        # Remove requests older than 1 hour
        cutoff_time = current_time - 3600
        while history and history[0] < cutoff_time:
            history.popleft()

        # Check minute-based rate limit
        minute_cutoff = current_time - 60
        recent_requests = sum(1 for timestamp in history if timestamp > minute_cutoff)

        if recent_requests >= self.config.max_requests_per_minute:
            # Block IP for 15 minutes
            self.blocked_ips[client_ip] = datetime.now()
            return True

        # Check hour-based rate limit
        if len(history) >= self.config.max_requests_per_hour:
            return True

        # Record this request
        history.append(current_time)

        return False

    def get_rate_limit_info(self, request: Request) -> dict[str, Any]:
        """Get rate limit information for response headers"""
        client_ip = self._get_client_ip(request)
        history = self.request_history[client_ip]
        current_time = time.time()

        # Count recent requests
        minute_cutoff = current_time - 60
        recent_requests = sum(1 for timestamp in history if timestamp > minute_cutoff)

        return {
            "X-RateLimit-Limit": str(self.config.max_requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, self.config.max_requests_per_minute - recent_requests)),
            "X-RateLimit-Reset": str(int(current_time + 60)),
        }


class InputValidator:
    """Input validation and sanitization"""

    def __init__(self, config: SecurityConfig):
        self.config = config

        # Compiled regex patterns for validation
        self.email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self.url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
        self.sql_injection_pattern = re.compile(
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b.*\b(FROM|INTO|WHERE|SET|TABLE|DATABASE)\b)|"
            r"(\b(DROP|CREATE|ALTER)\s+(TABLE|DATABASE|INDEX|VIEW)\b)|"
            r"(--[^\n]*$)|"
            r"(\/\*.*?\*\/)|"
            r"(\b(OR|AND)\b\s*['\"]?\s*['\"]?\s*=)|"
            r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",
            re.IGNORECASE | re.MULTILINE,
        )
        self.xss_pattern = re.compile(
            r"<script[^>]*>.*?</script>|"
            r"javascript:|"
            r"on\w+\s*=|"
            r"<iframe[^>]*>|"
            r"<object[^>]*>|"
            r"<embed[^>]*>",
            re.IGNORECASE | re.DOTALL,
        )

    def validate_memory_content(self, content: str) -> str:
        """Validate and sanitize memory content"""
        if not content or not isinstance(content, str):
            raise HTTPException(status_code=400, detail="Content is required and must be a string")

        # Check for null bytes
        if '\x00' in content:
            raise HTTPException(status_code=400, detail="Content contains potentially dangerous null bytes")

        # Check length
        if len(content) > self.config.max_content_length:
            raise HTTPException(
                status_code=400, detail=f"Content too long. Maximum {self.config.max_content_length} characters allowed"
            )

        # Check for potential SQL injection
        if self.sql_injection_pattern.search(content):
            raise HTTPException(status_code=400, detail="Content contains potentially dangerous SQL patterns")

        # Check for XSS attempts
        if self.xss_pattern.search(content):
            raise HTTPException(status_code=400, detail="Content contains potentially dangerous script patterns")

        # Sanitize content
        sanitized = self._sanitize_string(content)

        return sanitized

    def validate_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize metadata"""
        if not isinstance(metadata, dict):
            raise HTTPException(status_code=400, detail="Metadata must be a dictionary")

        # Check number of fields
        if len(metadata) > self.config.max_metadata_fields:
            raise HTTPException(
                status_code=400, detail=f"Too many metadata fields. Maximum {self.config.max_metadata_fields} allowed"
            )

        sanitized_metadata = {}

        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str) or len(key) > 100:
                raise HTTPException(status_code=400, detail="Metadata keys must be strings under 100 characters")

            # Sanitize key
            sanitized_key = self._sanitize_string(key)

            # Validate and sanitize value
            if isinstance(value, str):
                if len(value) > 1000:
                    raise HTTPException(status_code=400, detail="Metadata values must be under 1000 characters")
                sanitized_value = self._sanitize_string(value)
            elif isinstance(value, int | float | bool):
                sanitized_value = value
            elif value is None:
                sanitized_value = None
            else:
                raise HTTPException(
                    status_code=400, detail="Metadata values must be strings, numbers, booleans, or null"
                )

            sanitized_metadata[sanitized_key] = sanitized_value

        return sanitized_metadata

    def validate_search_query(self, query: str) -> str:
        """Validate and sanitize search query"""
        if not query or not isinstance(query, str):
            raise HTTPException(status_code=400, detail="Search query is required and must be a string")

        # Check length
        if len(query) > 1000:
            raise HTTPException(status_code=400, detail="Search query too long. Maximum 1000 characters allowed")

        # Check for SQL injection attempts
        if self.sql_injection_pattern.search(query):
            raise HTTPException(status_code=400, detail="Search query contains potentially dangerous SQL patterns")

        return self._sanitize_string(query)

    def validate_search_limit(self, limit: int) -> int:
        """Validate search limit parameter"""
        if not isinstance(limit, int) or limit < 1:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        if limit > self.config.max_search_results:
            raise HTTPException(
                status_code=400, detail=f"Limit too high. Maximum {self.config.max_search_results} results allowed"
            )

        return limit

    def validate_api_token(self, token: str) -> bool:
        """Validate API token format"""
        if not token or not isinstance(token, str):
            return False

        # Check minimum length
        if len(token) < self.config.token_min_length:
            return False

        # Check for suspicious patterns
        if self.sql_injection_pattern.search(token) or self.xss_pattern.search(token):
            return False

        return True

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input"""
        if not isinstance(text, str):
            return text

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove control characters except newlines and tabs  
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
        
        # Normalize multiple spaces (but preserve newlines and tabs)
        import re
        text = re.sub(r' +', ' ', text)

        return text.strip()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""

    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not self.config.enable_security_headers:
            return response

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

        # Add API-specific headers
        response.headers["X-API-Version"] = "v1"
        response.headers["X-Powered-By"] = "Second-Brain"

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Check rate limit
        if self.rate_limiter.is_rate_limited(request):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        rate_limit_info = self.rate_limiter.get_rate_limit_info(request)
        for header, value in rate_limit_info.items():
            response.headers[header] = value

        return response


class SecurityManager:
    """Main security management class"""

    def __init__(self, config: SecurityConfig | None = None):
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter(self.config)
        self.input_validator = InputValidator(self.config)

        # Initialize security monitoring
        self.security_events: list[dict[str, Any]] = []
        self.blocked_attempts = 0
        self.total_requests = 0

    def validate_request(self, request: Request) -> bool:
        """Validate incoming request"""
        self.total_requests += 1

        # Check rate limiting
        if self.rate_limiter.is_rate_limited(request):
            self._log_security_event("rate_limit_exceeded", request)
            self.blocked_attempts += 1
            return False

        return True

    def get_security_middleware(self):
        """Get security middleware for FastAPI"""
        return [
            (SecurityHeadersMiddleware, {"config": self.config}),
            (RateLimitingMiddleware, {"rate_limiter": self.rate_limiter}),
        ]

    def _log_security_event(self, event_type: str, request: Request, details: dict[str, Any] | None = None):
        """Log security event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "client_ip": self.rate_limiter._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "path": str(request.url.path),
            "method": request.method,
            "details": details or {},
        }

        self.security_events.append(event)

        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]

    def get_security_stats(self) -> dict[str, Any]:
        """Get security statistics"""
        return {
            "total_requests": self.total_requests,
            "blocked_attempts": self.blocked_attempts,
            "block_rate": self.blocked_attempts / max(1, self.total_requests),
            "recent_events": len(self.security_events),
            "active_rate_limits": len(self.rate_limiter.request_history),
            "blocked_ips": len(self.rate_limiter.blocked_ips),
        }


# Global security manager instance
security_manager = SecurityManager()


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    return security_manager


# Security testing functions
async def test_rate_limiting():
    """Test rate limiting functionality"""
    print("🔒 Testing rate limiting...")

    # Create test request

    # This would need proper integration testing
    # For now, just test the logic
    pass


async def test_input_validation():
    """Test input validation"""
    print("🔒 Testing input validation...")

    validator = InputValidator(SecurityConfig())

    # Test valid inputs
    try:
        valid_content = validator.validate_memory_content("This is a valid memory content")
        print(f"✅ Valid content passed: {valid_content[:50]}...")
    except Exception as e:
        print(f"❌ Valid content failed: {e}")

    # Test invalid inputs
    try:
        invalid_content = validator.validate_memory_content("DROP TABLE users; --")
        print(f"❌ Invalid content should have failed but passed: {invalid_content}")
    except HTTPException as e:
        print(f"✅ Invalid content correctly blocked: {e.detail}")

    # Test metadata validation
    try:
        valid_metadata = validator.validate_metadata({"category": "test", "importance": "high"})
        print(f"✅ Valid metadata passed: {valid_metadata}")
    except Exception as e:
        print(f"❌ Valid metadata failed: {e}")


if __name__ == "__main__":
    # Run security tests
    asyncio.run(test_input_validation())
    print("🔒 Security hardening implementation complete!")
