"""
Test security audit and hardening functionality
"""

from datetime import timedelta
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

from fastapi import Response

from app.core.exceptions import UnauthorizedException
from app.core.security_audit import (
    DataEncryption,
    PasswordPolicy,
    SecureTokenManager,
    SecurityAuditor,
    SecurityAuditResult,
    SecurityEventMonitor,
    SecurityHeadersManager,
    get_password_hasher,
    get_password_policy,
)


class TestPasswordPolicy:
    """Test password policy enforcement"""

    def test_password_policy_creation(self):
        """Test creating password policy"""
        policy = PasswordPolicy(min_length=10, require_special=True)

        assert policy.min_length == 10
        assert policy.require_special is True

    def test_strong_password_validation(self):
        """Test validation of strong passwords"""
        policy = get_password_policy()

        # Test strong password (avoiding sequential characters)
        valid, errors = policy.validate("Str0ng!P@ssW0rk2024")
        assert valid is True
        assert len(errors) == 0

    def test_weak_password_validation(self):
        """Test validation of weak passwords"""
        policy = get_password_policy()

        # Too short
        valid, errors = policy.validate("Short1!")
        assert valid is False
        assert any("at least 12 characters" in e for e in errors)

        # No uppercase
        valid, errors = policy.validate("weak!password123")
        assert valid is False
        assert any("uppercase" in e for e in errors)

        # No special characters
        valid, errors = policy.validate("WeakPassword123")
        assert valid is False
        assert any("special character" in e for e in errors)

    def test_sequential_characters_detection(self):
        """Test detection of sequential characters"""
        policy = PasswordPolicy()

        # Sequential letters
        valid, errors = policy.validate("Abc123!@#def")
        assert valid is False
        assert any("sequential" in e for e in errors)

        # Sequential numbers
        valid, errors = policy.validate("Pass123!@#word")
        assert valid is False
        assert any("sequential" in e for e in errors)

    def test_repeated_characters_detection(self):
        """Test detection of repeated characters"""
        policy = PasswordPolicy()

        valid, errors = policy.validate("Paaassword123!")
        assert valid is False
        assert any("repeated" in e for e in errors)


class TestSecureTokenManager:
    """Test secure token management"""

    def test_token_creation(self):
        """Test creating access tokens"""
        manager = SecureTokenManager(secret_key="test-secret-key")

        data = {"sub": "user123", "role": "user"}
        token = manager.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_token_verification(self):
        """Test verifying tokens"""
        manager = SecureTokenManager(secret_key="test-secret-key")

        # Create token
        data = {"sub": "user123", "role": "user"}
        token = manager.create_access_token(data)

        # Verify token
        payload = manager.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "user"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_expired_token_verification(self):
        """Test verifying expired tokens"""
        manager = SecureTokenManager(secret_key="test-secret-key")

        # Create token that's already expired
        data = {"sub": "user123"}
        token = manager.create_access_token(data, expires_delta=timedelta(seconds=-10))

        # Wait a bit to ensure it's expired
        import time
        time.sleep(0.1)

        # Verify should fail
        with pytest.raises(UnauthorizedException) as exc_info:
            manager.verify_token(token)

        # The JWT library throws a generic error that gets wrapped as "Invalid token"
        assert str(exc_info.value.message) == "Invalid token"

    def test_invalid_token_verification(self):
        """Test verifying invalid tokens"""
        manager = SecureTokenManager(secret_key="test-secret-key")

        # Invalid token
        with pytest.raises(UnauthorizedException):
            manager.verify_token("invalid.token.here")

    def test_refresh_token_creation(self):
        """Test creating refresh tokens"""
        manager = SecureTokenManager(secret_key="test-secret-key")

        refresh_token = manager.create_refresh_token("user123")
        assert refresh_token is not None
        assert len(refresh_token) > 20


class TestDataEncryption:
    """Test data encryption utilities"""

    def test_data_encryption_decryption(self):
        """Test encrypting and decrypting data"""
        encryptor = DataEncryption()

        # Test string encryption
        original = "Sensitive data here"
        encrypted = encryptor.encrypt_data(original)
        decrypted = encryptor.decrypt_data(encrypted)

        assert encrypted != original
        assert decrypted == original

    def test_dict_encryption_decryption(self):
        """Test encrypting and decrypting dictionaries"""
        encryptor = DataEncryption()

        # Test dict encryption
        original = {"user": "test", "password": "secret", "data": [1, 2, 3]}
        encrypted = encryptor.encrypt_dict(original)
        decrypted = encryptor.decrypt_dict(encrypted)

        assert isinstance(encrypted, str)
        assert decrypted == original

    def test_hash_data_and_verify(self):
        """Test hashing and verifying data"""
        encryptor = DataEncryption()

        # Hash data
        data = "password123"
        hashed = encryptor.hash_data(data)

        # Verify correct data
        assert encryptor.verify_hash(data, hashed) is True

        # Verify incorrect data
        assert encryptor.verify_hash("wrongpassword", hashed) is False

    def test_encryption_with_master_key(self):
        """Test encryption with specific master key"""
        from cryptography.fernet import Fernet
        master_key = Fernet.generate_key().decode()

        encryptor1 = DataEncryption(master_key=master_key)
        encryptor2 = DataEncryption(master_key=master_key)

        # Encrypt with first instance
        data = "Test data"
        encrypted = encryptor1.encrypt_data(data)

        # Decrypt with second instance (same key)
        decrypted = encryptor2.decrypt_data(encrypted)
        assert decrypted == data


class TestSecurityHeaders:
    """Test security headers management"""

    def test_apply_security_headers(self):
        """Test applying security headers to response"""
        response = Response()
        SecurityHeadersManager.apply_security_headers(response)

        # Check essential headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Permissions-Policy" in response.headers


class TestSecurityAuditor:
    """Test security auditing functionality"""

    @pytest.mark.asyncio
    async def test_run_full_audit(self):
        """Test running full security audit"""
        auditor = SecurityAuditor()
        results = await auditor.run_full_audit()

        assert len(results) > 0
        assert all(isinstance(r, SecurityAuditResult) for r in results)

    @pytest.mark.asyncio
    async def test_audit_authentication(self):
        """Test authentication audit checks"""
        auditor = SecurityAuditor()
        results = await auditor._audit_authentication()

        assert len(results) > 0

        # Check for specific audits
        check_names = [r.check_name for r in results]
        assert "Strong Password Policy" in check_names
        assert "Multi-Factor Authentication" in check_names
        assert "Account Lockout Policy" in check_names

    @pytest.mark.asyncio
    async def test_generate_audit_report(self):
        """Test generating audit report"""
        auditor = SecurityAuditor()
        results = await auditor.run_full_audit()

        report = auditor.generate_audit_report(results)

        assert "audit_date" in report
        assert "total_checks" in report
        assert "passed_checks" in report
        assert "security_score" in report
        assert "results_by_severity" in report
        assert "recommendations" in report

        # Check severity categories
        assert all(sev in report["results_by_severity"] for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"])


class TestSecurityEventMonitor:
    """Test security event monitoring"""

    def test_detect_suspicious_activity(self):
        """Test detecting suspicious activity"""
        monitor = SecurityEventMonitor()

        # Mock request
        request = Mock()

        # Test SQL injection detection
        activities = monitor.detect_suspicious_activity(request, "SELECT * FROM users WHERE id=1")
        assert len(activities) > 0
        assert any("SQL injection" in a for a in activities)

        # Test path traversal detection
        activities = monitor.detect_suspicious_activity(request, "../../etc/passwd")
        assert len(activities) > 0
        assert any("path traversal" in a for a in activities)

        # Test command injection detection
        activities = monitor.detect_suspicious_activity(request, "ls -la; cat /etc/passwd")
        assert len(activities) > 0
        assert any("command injection" in a for a in activities)

    @pytest.mark.asyncio
    async def test_log_security_event(self):
        """Test logging security events"""
        monitor = SecurityEventMonitor()

        # Log a security event
        await monitor.log_security_event(
            event_type="AUTHENTICATION_FAILED",
            severity="MEDIUM",
            source_ip="192.168.1.100",
            user_id="user123",
            details={"attempts": 3}
        )

        # No exception should be raised


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_password_hash_and_verify(self):
        """Test hashing and verifying passwords"""
        hasher = get_password_hasher()

        password = "SecureP@ssw0rd123"

        # Hash password
        hashed = hasher.hash(password)
        assert hashed != password

        # Verify correct password
        assert hasher.verify(hashed, password) is True

        # Verify incorrect password
        try:
            hasher.verify(hashed, "wrongpassword")
            raise AssertionError("Should have raised exception")
        except Exception:
            pass  # Expected

    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes"""
        hasher = get_password_hasher()

        password = "TestPassword123!"
        hash1 = hasher.hash(password)
        hash2 = hasher.hash(password)

        # Same password should produce different hashes (due to salt)
        assert hash1 != hash2

        # But both should verify correctly
        assert hasher.verify(hash1, password) is True
        assert hasher.verify(hash2, password) is True
