#!/usr/bin/env python3
"""
Standalone test for security infrastructure core functionality.
"""

import asyncio
import hashlib
import hmac
import time
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class SecurityConfig:
    """Security configuration for testing"""
    api_key_length: int = 32
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    password_min_length: int = 8
    session_timeout: int = 3600
    max_login_attempts: int = 5
    lockout_duration: int = 900

class MockRateLimiter:
    """Mock rate limiter for testing"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed under rate limit"""
        now = time.time()
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[identifier] = []
        
        # Check if under limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        now = time.time()
        if identifier in self.requests:
            current_requests = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
            return max(0, self.max_requests - len(current_requests))
        return self.max_requests

class MockAuthenticator:
    """Mock authenticator for testing"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.users: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[float]] = {}
    
    def hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """Hash password with salt"""
        if not salt:
            salt = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        return password_hash, salt
    
    def validate_password_strength(self, password: str) -> tuple[bool, List[str]]:
        """Validate password strength"""
        errors = []
        
        if len(password) < self.config.password_min_length:
            errors.append(f"Password must be at least {self.config.password_min_length} characters")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[0-9]', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def register_user(self, username: str, password: str, email: str) -> tuple[bool, str]:
        """Register a new user"""
        if username in self.users:
            return False, "Username already exists"
        
        is_valid, errors = self.validate_password_strength(password)
        if not is_valid:
            return False, "; ".join(errors)
        
        password_hash, salt = self.hash_password(password)
        
        self.users[username] = {
            "password_hash": password_hash,
            "salt": salt,
            "email": email,
            "created_at": datetime.now(),
            "is_active": True,
            "failed_attempts": 0,
            "locked_until": None
        }
        
        return True, "User registered successfully"
    
    def authenticate_user(self, username: str, password: str) -> tuple[bool, str, Optional[str]]:
        """Authenticate user credentials"""
        if username not in self.users:
            return False, "Invalid credentials", None
        
        user = self.users[username]
        
        # Check if account is locked
        if user.get("locked_until") and datetime.now() < user["locked_until"]:
            return False, "Account is locked", None
        
        # Verify password
        password_hash, _ = self.hash_password(password, user["salt"])
        
        if password_hash == user["password_hash"]:
            # Reset failed attempts on successful login
            user["failed_attempts"] = 0
            user["locked_until"] = None
            
            # Create session
            session_id = hashlib.sha256(f"{username}{time.time()}".encode()).hexdigest()
            self.sessions[session_id] = {
                "username": username,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=self.config.session_timeout)
            }
            
            return True, "Authentication successful", session_id
        else:
            # Track failed attempt
            user["failed_attempts"] += 1
            
            if user["failed_attempts"] >= self.config.max_login_attempts:
                user["locked_until"] = datetime.now() + timedelta(seconds=self.config.lockout_duration)
                return False, "Account locked due to too many failed attempts", None
            
            return False, "Invalid credentials", None
    
    def validate_session(self, session_id: str) -> tuple[bool, Optional[str]]:
        """Validate session"""
        if session_id not in self.sessions:
            return False, None
        
        session = self.sessions[session_id]
        
        if datetime.now() > session["expires_at"]:
            del self.sessions[session_id]
            return False, None
        
        return True, session["username"]

class MockInputValidator:
    """Mock input validator for testing"""
    
    @staticmethod
    def sanitize_input(data: str) -> str:
        """Sanitize input data"""
        # Remove potential XSS patterns
        data = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
        data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
        data = re.sub(r'on\w+\s*=', '', data, flags=re.IGNORECASE)
        
        return data.strip()
    
    @staticmethod
    def validate_sql_injection(query: str) -> tuple[bool, List[str]]:
        """Check for SQL injection patterns"""
        dangerous_patterns = [
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+\w+\s+set",
            r"exec\s*\(",
            r"sp_\w+",
            r"xp_\w+"
        ]
        
        threats = []
        query_lower = query.lower()
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower):
                threats.append(f"Potential SQL injection: {pattern}")
        
        return len(threats) == 0, threats
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        if len(api_key) != 32:
            return False
        
        if not re.match(r'^[a-zA-Z0-9]+$', api_key):
            return False
        
        return True

async def test_security_infrastructure():
    """Test security infrastructure functionality"""
    print("🔒 Testing Security Infrastructure")
    print("=" * 50)
    
    config = SecurityConfig()
    
    # Test 1: Rate Limiting
    print("\n1. Testing Rate Limiting...")
    rate_limiter = MockRateLimiter(max_requests=5, window_seconds=60)
    
    # Make requests within limit
    for i in range(5):
        assert rate_limiter.is_allowed("user1"), f"Request {i+1} should be allowed"
    
    # Exceed limit
    assert not rate_limiter.is_allowed("user1"), "Request should be rate limited"
    
    # Different user should still work
    assert rate_limiter.is_allowed("user2"), "Different user should be allowed"
    
    print("✅ Rate limiting working correctly")
    
    # Test 2: Password Validation
    print("\n2. Testing Password Validation...")
    authenticator = MockAuthenticator(config)
    
    weak_passwords = [
        "123456",
        "password",
        "abcdefgh",
        "PASSWORD123",
        "Password"
    ]
    
    strong_passwords = [
        "StrongP@ssw0rd!",
        "MySecur3#Passw0rd",
        "Comp!ex$P@ss123"
    ]
    
    for pwd in weak_passwords:
        is_valid, _ = authenticator.validate_password_strength(pwd)
        assert not is_valid, f"Weak password '{pwd}' should be rejected"
    
    for pwd in strong_passwords:
        is_valid, _ = authenticator.validate_password_strength(pwd)
        assert is_valid, f"Strong password should be accepted"
    
    print("✅ Password validation working correctly")
    
    # Test 3: User Registration
    print("\n3. Testing User Registration...")
    
    success, msg = authenticator.register_user("testuser", "StrongP@ssw0rd!", "test@example.com")
    assert success, f"Registration should succeed: {msg}"
    
    success, msg = authenticator.register_user("testuser", "AnotherP@ss123", "test2@example.com")
    assert not success, "Duplicate username should be rejected"
    
    success, msg = authenticator.register_user("testuser2", "weak", "test3@example.com")
    assert not success, "Weak password should be rejected"
    
    print("✅ User registration working correctly")
    
    # Test 4: Authentication
    print("\n4. Testing Authentication...")
    
    # Valid credentials
    success, msg, valid_session = authenticator.authenticate_user("testuser", "StrongP@ssw0rd!")
    assert success, "Valid credentials should authenticate"
    assert valid_session is not None, "Session should be created"
    
    # Invalid credentials
    success, msg, invalid_session = authenticator.authenticate_user("testuser", "wrongpassword")
    assert not success, "Invalid credentials should be rejected"
    assert invalid_session is None, "No session should be created"
    
    print("✅ Authentication working correctly")
    
    # Test 5: Session Management
    print("\n5. Testing Session Management...")
    
    # Valid session
    is_valid, username = authenticator.validate_session(valid_session)
    assert is_valid, "Valid session should be accepted"
    assert username == "testuser", "Correct username should be returned"
    
    # Invalid session
    is_valid, username = authenticator.validate_session("invalid_session")
    assert not is_valid, "Invalid session should be rejected"
    assert username is None, "No username should be returned"
    
    print("✅ Session management working correctly")
    
    # Test 6: Account Lockout
    print("\n6. Testing Account Lockout...")
    
    # Register a test user for lockout testing
    authenticator.register_user("locktest", "TestP@ssw0rd!", "lock@example.com")
    
    # Make multiple failed attempts
    for i in range(config.max_login_attempts):
        success, msg, _ = authenticator.authenticate_user("locktest", "wrongpassword")
        assert not success, f"Failed attempt {i+1} should be rejected"
    
    # Account should now be locked
    success, msg, _ = authenticator.authenticate_user("locktest", "TestP@ssw0rd!")
    assert not success, "Account should be locked"
    assert "locked" in msg.lower(), "Should indicate account is locked"
    
    print("✅ Account lockout working correctly")
    
    # Test 7: Input Validation
    print("\n7. Testing Input Validation...")
    validator = MockInputValidator()
    
    # XSS prevention
    malicious_input = "<script>alert('xss')</script>Hello"
    cleaned = validator.sanitize_input(malicious_input)
    assert "<script>" not in cleaned, "Script tags should be removed"
    assert "Hello" in cleaned, "Safe content should remain"
    
    # SQL injection detection
    safe_query = "SELECT * FROM users WHERE name = 'john'"
    is_safe, _ = validator.validate_sql_injection(safe_query)
    assert is_safe, "Safe query should pass validation"
    
    malicious_query = "SELECT * FROM users WHERE 1=1; DROP TABLE users;"
    is_safe, threats = validator.validate_sql_injection(malicious_query)
    assert not is_safe, "Malicious query should be detected"
    assert len(threats) > 0, "Threats should be identified"
    
    print("✅ Input validation working correctly")
    
    # Test 8: API Key Validation
    print("\n8. Testing API Key Validation...")
    
    valid_key = "abcd1234efgh5678ijkl9012mnop3456"
    assert validator.validate_api_key(valid_key), "Valid API key should pass"
    
    invalid_keys = [
        "short",
        "toolongtobeavalidapikeythatexceeds32chars",
        "invalid-chars-!@#$%^&*()",
        ""
    ]
    
    for key in invalid_keys:
        assert not validator.validate_api_key(key), f"Invalid key '{key}' should be rejected"
    
    print("✅ API key validation working correctly")
    
    print("\n" + "=" * 50)
    print("🎉 ALL SECURITY INFRASTRUCTURE TESTS PASSED!")
    print("=" * 50)
    
    return {
        "tests_run": 8,
        "tests_passed": 8,
        "users_registered": len(authenticator.users),
        "sessions_created": len(authenticator.sessions),
        "rate_limits_tested": True,
        "security_validations": ["XSS", "SQL Injection", "Password Strength", "API Key Format"]
    }

if __name__ == "__main__":
    try:
        result = asyncio.run(test_security_infrastructure())
        print(f"\nTest Summary:")
        print(f"- Tests Run: {result['tests_run']}")
        print(f"- Tests Passed: {result['tests_passed']}")
        print(f"- Users Registered: {result['users_registered']}")
        print(f"- Sessions Created: {result['sessions_created']}")
        print(f"- Security Validations: {', '.join(result['security_validations'])}")
        print(f"- Rate Limiting: {'✅' if result['rate_limits_tested'] else '❌'}")
    except Exception as e:
        print(f"❌ Security test failed with error: {e}")
        import traceback
        traceback.print_exc()