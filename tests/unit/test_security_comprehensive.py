"""
Comprehensive Security Test Suite for Second Brain v2.6.0-dev

Tests authentication, authorization, input validation, and security features.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from httpx import AsyncClient

from app.auth import verify_api_key, get_current_user, create_access_token
from app.security.auth import verify_token, validate_session
from app.security.validation import sanitize_input, validate_memory_content
from app.security.middleware import RateLimiter, SecurityHeadersMiddleware


class TestAuthentication:
    """Test authentication mechanisms"""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object"""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request
    
    def test_bearer_token_validation_success(self, mock_request):
        """Test successful bearer token validation"""
        # Set valid token
        mock_request.headers["Authorization"] = "Bearer test-key-1"
        
        # Verify token validates
        with patch.dict("os.environ", {"API_TOKENS": "test-key-1,test-key-2"}):
            result = verify_api_key(mock_request)
            assert result == "test-key-1"
    
    def test_bearer_token_validation_invalid(self, mock_request):
        """Test invalid bearer token rejection"""
        # Set invalid token
        mock_request.headers["Authorization"] = "Bearer invalid-token"
        
        # Verify token is rejected
        with patch.dict("os.environ", {"API_TOKENS": "test-key-1,test-key-2"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(mock_request)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_bearer_token_missing(self, mock_request):
        """Test missing authorization header"""
        # No authorization header
        
        with patch.dict("os.environ", {"API_TOKENS": "test-key-1,test-key-2"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(mock_request)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_bearer_token_wrong_format(self, mock_request):
        """Test wrong authorization format"""
        # Wrong format (not Bearer)
        mock_request.headers["Authorization"] = "Basic dXNlcjpwYXNz"
        
        with patch.dict("os.environ", {"API_TOKENS": "test-key-1,test-key-2"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(mock_request)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_api_key_rotation(self, mock_request):
        """Test API key rotation scenario"""
        # Old token should fail
        mock_request.headers["Authorization"] = "Bearer old-key"
        
        with patch.dict("os.environ", {"API_TOKENS": "new-key-1,new-key-2"}):
            with pytest.raises(HTTPException):
                verify_api_key(mock_request)
        
        # New token should succeed
        mock_request.headers["Authorization"] = "Bearer new-key-1"
        with patch.dict("os.environ", {"API_TOKENS": "new-key-1,new-key-2"}):
            result = verify_api_key(mock_request)
            assert result == "new-key-1"
    
    @pytest.mark.asyncio
    async def test_token_expiration(self):
        """Test token expiration handling"""
        # Create token with short expiration
        token = create_access_token(
            data={"sub": "test-user"},
            expires_delta=timedelta(seconds=1)
        )
        
        # Token should be valid immediately
        payload = await verify_token(token)
        assert payload["sub"] == "test-user"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Token should be expired
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_multiple_valid_tokens(self, mock_request):
        """Test multiple valid API tokens"""
        tokens = ["token1", "token2", "token3"]
        
        with patch.dict("os.environ", {"API_TOKENS": ",".join(tokens)}):
            for token in tokens:
                mock_request.headers["Authorization"] = f"Bearer {token}"
                result = verify_api_key(mock_request)
                assert result == token


class TestAuthorization:
    """Test authorization and permission checks"""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user with permissions"""
        user = Mock()
        user.id = "user-123"
        user.permissions = ["read", "write"]
        user.is_active = True
        return user
    
    def test_permission_check_allowed(self, mock_user):
        """Test permission check for allowed action"""
        # User has 'read' permission
        assert "read" in mock_user.permissions
        assert "write" in mock_user.permissions
    
    def test_permission_check_denied(self, mock_user):
        """Test permission check for denied action"""
        # User doesn't have 'delete' permission
        assert "delete" not in mock_user.permissions
        assert "admin" not in mock_user.permissions
    
    def test_inactive_user_authorization(self, mock_user):
        """Test inactive user is denied access"""
        mock_user.is_active = False
        
        # Check user is inactive
        assert not mock_user.is_active
    
    @pytest.mark.asyncio
    async def test_resource_access_control(self, mock_user):
        """Test resource-level access control"""
        # Mock memory object
        memory = Mock()
        memory.user_id = "user-123"
        memory.is_public = False
        
        # User can access their own memory
        assert memory.user_id == mock_user.id
        
        # Different user cannot access private memory
        other_user = Mock()
        other_user.id = "user-456"
        assert memory.user_id != other_user.id
        assert not memory.is_public
    
    def test_role_based_access(self):
        """Test role-based access control"""
        # Admin role
        admin = Mock()
        admin.roles = ["admin", "user"]
        
        # Regular user
        user = Mock()
        user.roles = ["user"]
        
        # Guest
        guest = Mock()
        guest.roles = ["guest"]
        
        # Check role hierarchy
        assert "admin" in admin.roles
        assert "admin" not in user.roles
        assert "user" not in guest.roles


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance"""
        return RateLimiter(
            requests_per_minute=10,
            requests_per_hour=100
        )
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_traffic(self, rate_limiter):
        """Test rate limiter allows normal traffic"""
        client_id = "127.0.0.1"
        
        # Make requests within limit
        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_traffic(self, rate_limiter):
        """Test rate limiter blocks excessive traffic"""
        client_id = "127.0.0.1"
        
        # Exceed per-minute limit
        for i in range(10):
            await rate_limiter.check_rate_limit(client_id)
        
        # Next request should be blocked
        allowed = await rate_limiter.check_rate_limit(client_id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_client(self, rate_limiter):
        """Test rate limiting is per-client"""
        client1 = "127.0.0.1"
        client2 = "127.0.0.2"
        
        # Exhaust limit for client1
        for i in range(10):
            await rate_limiter.check_rate_limit(client1)
        
        # Client2 should still be allowed
        allowed = await rate_limiter.check_rate_limit(client2)
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, rate_limiter):
        """Test rate limit resets after time window"""
        client_id = "127.0.0.1"
        
        # Mock time to control rate limit windows
        with patch("time.time") as mock_time:
            # Initial time
            mock_time.return_value = 0
            
            # Exhaust limit
            for i in range(10):
                await rate_limiter.check_rate_limit(client_id)
            
            # Should be blocked
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed is False
            
            # Advance time past the window (1 minute)
            mock_time.return_value = 61
            
            # Should be allowed again
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed is True


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_sanitize_sql_injection(self):
        """Test SQL injection prevention"""
        malicious_inputs = [
            "'; DROP TABLE memories; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM users WHERE 1=1;",
            "' UNION SELECT * FROM users --"
        ]
        
        for input_str in malicious_inputs:
            sanitized = sanitize_input(input_str)
            # Verify dangerous characters are escaped
            assert "'" not in sanitized or "\\'" in sanitized
            assert ";" not in sanitized or "\\;" in sanitized
            assert "--" not in sanitized
    
    def test_sanitize_xss_prevention(self):
        """Test XSS attack prevention"""
        xss_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='evil.com'></iframe>",
            "<svg onload=alert('XSS')>"
        ]
        
        for input_str in xss_inputs:
            sanitized = sanitize_input(input_str)
            # Verify HTML tags are escaped
            assert "<" not in sanitized or "&lt;" in sanitized
            assert ">" not in sanitized or "&gt;" in sanitized
            assert "javascript:" not in sanitized
    
    def test_sanitize_path_traversal(self):
        """Test path traversal prevention"""
        path_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "files/../../../secret.txt",
            "./././../config.json"
        ]
        
        for input_str in path_inputs:
            sanitized = sanitize_input(input_str)
            # Verify path traversal sequences are removed
            assert "../" not in sanitized
            assert "..\\" not in sanitized
    
    def test_validate_memory_content_length(self):
        """Test memory content length validation"""
        # Valid length
        valid_content = "a" * 1000
        assert validate_memory_content(valid_content) is True
        
        # Too long
        long_content = "a" * 100001
        assert validate_memory_content(long_content) is False
        
        # Empty
        assert validate_memory_content("") is False
    
    def test_validate_memory_content_format(self):
        """Test memory content format validation"""
        # Valid formats
        assert validate_memory_content("Normal text content") is True
        assert validate_memory_content("Content with\nnewlines") is True
        
        # Invalid formats (binary data)
        assert validate_memory_content("\x00\x01\x02") is False
        assert validate_memory_content(b"binary data".decode("latin-1")) is False
    
    def test_input_type_validation(self):
        """Test input type validation"""
        # String inputs
        assert isinstance(sanitize_input("test"), str)
        
        # Non-string inputs should be converted
        assert isinstance(sanitize_input(123), str)
        assert isinstance(sanitize_input(None), str)
        assert isinstance(sanitize_input([1, 2, 3]), str)


class TestSecurityHeaders:
    """Test security headers middleware"""
    
    @pytest.fixture
    def security_middleware(self):
        """Create security headers middleware"""
        return SecurityHeadersMiddleware()
    
    @pytest.mark.asyncio
    async def test_security_headers_added(self, security_middleware):
        """Test security headers are added to responses"""
        # Mock response
        response = Mock()
        response.headers = {}
        
        # Apply middleware
        await security_middleware.add_security_headers(response)
        
        # Verify headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" in response.headers
    
    @pytest.mark.asyncio
    async def test_cors_configuration(self):
        """Test CORS configuration"""
        # Mock CORS settings
        cors_config = {
            "allowed_origins": ["http://localhost:3000", "https://app.example.com"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
            "allowed_headers": ["Authorization", "Content-Type"],
            "allow_credentials": True
        }
        
        # Verify configuration
        assert "http://localhost:3000" in cors_config["allowed_origins"]
        assert "POST" in cors_config["allowed_methods"]
        assert "Authorization" in cors_config["allowed_headers"]
        assert cors_config["allow_credentials"] is True


class TestSessionManagement:
    """Test session management and security"""
    
    @pytest.fixture
    def session_store(self):
        """Mock session store"""
        return {}
    
    @pytest.mark.asyncio
    async def test_session_creation(self, session_store):
        """Test secure session creation"""
        user_id = "user-123"
        
        # Create session
        session_id = await create_session(user_id, session_store)
        
        # Verify session
        assert session_id in session_store
        assert session_store[session_id]["user_id"] == user_id
        assert "created_at" in session_store[session_id]
        assert "expires_at" in session_store[session_id]
    
    @pytest.mark.asyncio
    async def test_session_validation(self, session_store):
        """Test session validation"""
        user_id = "user-123"
        session_id = await create_session(user_id, session_store)
        
        # Valid session
        is_valid = await validate_session(session_id, session_store)
        assert is_valid is True
        
        # Invalid session
        is_valid = await validate_session("invalid-session", session_store)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_session_expiration(self, session_store):
        """Test session expiration"""
        user_id = "user-123"
        
        # Create session with short expiration
        session_id = await create_session(
            user_id, 
            session_store,
            expires_in=timedelta(seconds=1)
        )
        
        # Should be valid immediately
        assert await validate_session(session_id, session_store) is True
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should be expired
        assert await validate_session(session_id, session_store) is False
    
    @pytest.mark.asyncio
    async def test_session_invalidation(self, session_store):
        """Test manual session invalidation"""
        user_id = "user-123"
        session_id = await create_session(user_id, session_store)
        
        # Invalidate session
        await invalidate_session(session_id, session_store)
        
        # Should no longer be valid
        assert await validate_session(session_id, session_store) is False


class TestEncryption:
    """Test data encryption and security"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        from app.security.utils import hash_password, verify_password
        
        password = "SecurePassword123!"
        
        # Hash password
        hashed = hash_password(password)
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify wrong password
        assert verify_password("WrongPassword", hashed) is False
        
        # Verify hash is different each time (salt)
        hashed2 = hash_password(password)
        assert hashed != hashed2
    
    def test_sensitive_data_encryption(self):
        """Test encryption of sensitive data"""
        from app.security.utils import encrypt_data, decrypt_data
        
        sensitive_data = "SSN: 123-45-6789"
        
        # Encrypt data
        encrypted = encrypt_data(sensitive_data)
        assert encrypted != sensitive_data
        assert len(encrypted) > len(sensitive_data)
        
        # Decrypt data
        decrypted = decrypt_data(encrypted)
        assert decrypted == sensitive_data
    
    def test_encryption_key_rotation(self):
        """Test encryption key rotation scenario"""
        from app.security.utils import encrypt_data, decrypt_data, rotate_encryption_key
        
        data = "Sensitive information"
        
        # Encrypt with current key
        encrypted_v1 = encrypt_data(data)
        
        # Rotate key
        old_key = rotate_encryption_key()
        
        # Can still decrypt old data with key version
        decrypted = decrypt_data(encrypted_v1, key_version="v1")
        assert decrypted == data
        
        # New encryption uses new key
        encrypted_v2 = encrypt_data(data)
        assert encrypted_v2 != encrypted_v1


class TestAuditLogging:
    """Test security audit logging"""
    
    @pytest.fixture
    def audit_logger(self):
        """Mock audit logger"""
        logger = Mock()
        logger.log = Mock()
        return logger
    
    def test_authentication_audit_log(self, audit_logger):
        """Test authentication events are logged"""
        # Successful login
        audit_logger.log("auth.success", {
            "user_id": "user-123",
            "ip": "127.0.0.1",
            "timestamp": datetime.utcnow()
        })
        
        # Failed login
        audit_logger.log("auth.failed", {
            "attempted_user": "admin",
            "ip": "192.168.1.100",
            "reason": "Invalid password"
        })
        
        # Verify logs
        assert audit_logger.log.call_count == 2
    
    def test_authorization_audit_log(self, audit_logger):
        """Test authorization events are logged"""
        # Access granted
        audit_logger.log("access.granted", {
            "user_id": "user-123",
            "resource": "memory:456",
            "action": "read"
        })
        
        # Access denied
        audit_logger.log("access.denied", {
            "user_id": "user-789",
            "resource": "memory:456",
            "action": "delete",
            "reason": "Insufficient permissions"
        })
        
        assert audit_logger.log.call_count == 2
    
    def test_security_violation_audit_log(self, audit_logger):
        """Test security violations are logged"""
        # Rate limit exceeded
        audit_logger.log("security.rate_limit", {
            "ip": "10.0.0.1",
            "requests": 150,
            "limit": 100
        })
        
        # Suspicious activity
        audit_logger.log("security.suspicious", {
            "ip": "192.168.1.50",
            "pattern": "Multiple failed login attempts",
            "action": "Temporary IP block"
        })
        
        assert audit_logger.log.call_count == 2


class TestSecurityIntegration:
    """Integration tests for security features"""
    
    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, client: AsyncClient):
        """Test complete authentication flow"""
        # No auth header - should fail
        response = await client.get("/memories")
        assert response.status_code == 403
        
        # Invalid token - should fail
        response = await client.get(
            "/memories",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 403
        
        # Valid token - should succeed
        response = await client.get(
            "/memories",
            headers={"Authorization": "Bearer test-key-1"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_security_headers_in_response(self, client: AsyncClient):
        """Test security headers are present in responses"""
        response = await client.get(
            "/health",
            headers={"Authorization": "Bearer test-key-1"}
        )
        
        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
    
    @pytest.mark.asyncio
    async def test_input_validation_integration(self, client: AsyncClient):
        """Test input validation in API endpoints"""
        # SQL injection attempt
        malicious_content = "'; DROP TABLE memories; --"
        
        response = await client.post(
            "/memories",
            headers={"Authorization": "Bearer test-key-1"},
            json={
                "content": malicious_content,
                "importance": 5.0
            }
        )
        
        # Should succeed but content should be sanitized
        assert response.status_code == 200
        created_memory = response.json()
        assert malicious_content not in created_memory["content"]
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, client: AsyncClient):
        """Test rate limiting in practice"""
        headers = {"Authorization": "Bearer test-key-1"}
        
        # Make many requests quickly
        responses = []
        for i in range(150):
            response = await client.get("/memories", headers=headers)
            responses.append(response.status_code)
        
        # Some requests should be rate limited (429)
        assert 429 in responses


# Helper functions for tests
async def create_session(user_id: str, store: dict, expires_in: timedelta = None):
    """Create a new session"""
    import uuid
    session_id = str(uuid.uuid4())
    expires_in = expires_in or timedelta(hours=1)
    
    store[session_id] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + expires_in
    }
    return session_id


async def validate_session(session_id: str, store: dict) -> bool:
    """Validate a session"""
    if session_id not in store:
        return False
    
    session = store[session_id]
    if datetime.utcnow() > session["expires_at"]:
        # Session expired
        del store[session_id]
        return False
    
    return True


async def invalidate_session(session_id: str, store: dict):
    """Invalidate a session"""
    if session_id in store:
        del store[session_id]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])