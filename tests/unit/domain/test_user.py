"""
Unit tests for User domain model.
"""

import pytest
import time
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.models.user import User, UserId, UserRole


class TestUserId:
    """Test UserId value object."""
    
    def test_generate_creates_unique_ids(self):
        """Test that generate creates unique IDs."""
        id1 = UserId.generate()
        id2 = UserId.generate()
        assert id1 != id2
        assert isinstance(id1.value, UUID)
    
    def test_user_id_is_immutable(self):
        """Test that UserId is immutable."""
        user_id = UserId.generate()
        with pytest.raises(AttributeError):
            user_id.value = uuid4()


class TestUser:
    """Test User entity."""
    
    @pytest.fixture
    def valid_user_data(self):
        """Provide valid user data."""
        return {
            "id": UserId.generate(),
            "email": "test@example.com",
            "username": "testuser",
        }
    
    def test_create_user_with_valid_data(self, valid_user_data):
        """Test creating user with valid data."""
        user = User(**valid_user_data)
        assert user.id == valid_user_data["id"]
        assert user.email == valid_user_data["email"]
        assert user.username == valid_user_data["username"]
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
    
    def test_user_requires_email(self, valid_user_data):
        """Test that user requires email."""
        valid_user_data["email"] = ""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            User(**valid_user_data)
    
    def test_user_requires_valid_email(self, valid_user_data):
        """Test that user requires valid email format."""
        valid_user_data["email"] = "invalid-email"
        with pytest.raises(ValueError, match="Invalid email format"):
            User(**valid_user_data)
    
    def test_user_requires_username(self, valid_user_data):
        """Test that user requires username."""
        valid_user_data["username"] = ""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            User(**valid_user_data)
    
    def test_username_minimum_length(self, valid_user_data):
        """Test username minimum length."""
        valid_user_data["username"] = "ab"
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            User(**valid_user_data)
    
    def test_update_profile(self, valid_user_data):
        """Test updating user profile."""
        user = User(**valid_user_data)
        old_updated_at = user.updated_at
        
        # Add small delay to ensure timestamp difference
        time.sleep(0.001)
        
        user.update_profile(
            full_name="Test User",
            bio="A test user",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        assert user.full_name == "Test User"
        assert user.bio == "A test user"
        assert user.avatar_url == "https://example.com/avatar.jpg"
        assert user.updated_at > old_updated_at
    
    def test_update_email(self, valid_user_data):
        """Test updating email."""
        user = User(**valid_user_data)
        user.is_verified = True
        
        user.update_email("newemail@example.com")
        assert user.email == "newemail@example.com"
        assert user.is_verified is False  # Requires re-verification
    
    def test_update_email_validation(self, valid_user_data):
        """Test email update validation."""
        user = User(**valid_user_data)
        
        with pytest.raises(ValueError, match="Invalid email format"):
            user.update_email("invalid-email")
    
    def test_user_verification(self, valid_user_data):
        """Test user verification."""
        user = User(**valid_user_data)
        assert user.is_verified is False
        
        user.verify()
        assert user.is_verified is True
    
    def test_user_activation(self, valid_user_data):
        """Test user activation/deactivation."""
        user = User(**valid_user_data)
        assert user.is_active is True
        
        user.deactivate()
        assert user.is_active is False
        
        user.activate()
        assert user.is_active is True
    
    def test_user_role_promotion(self, valid_user_data):
        """Test user role promotion."""
        user = User(**valid_user_data)
        assert user.role == UserRole.USER
        assert user.memory_limit == 10000
        assert user.storage_limit_mb == 5000
        
        # Promote to premium
        user.promote_to_premium()
        assert user.role == UserRole.PREMIUM
        assert user.memory_limit == 50000
        assert user.storage_limit_mb == 50000
        assert user.api_rate_limit == 10000
        
        # Promote to admin
        user.promote_to_admin()
        assert user.role == UserRole.ADMIN
        assert user.memory_limit == -1  # Unlimited
        assert user.storage_limit_mb == -1
        assert user.api_rate_limit == -1
    
    def test_login_tracking(self, valid_user_data):
        """Test login tracking."""
        user = User(**valid_user_data)
        assert user.last_login_at is None
        
        user.record_login()
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)
    
    def test_preferences(self, valid_user_data):
        """Test user preferences."""
        user = User(**valid_user_data)
        
        # Set preference
        user.update_preference("theme", "dark")
        assert user.get_preference("theme") == "dark"
        
        # Get with default
        assert user.get_preference("language", "en") == "en"
        
        # Update existing
        user.update_preference("theme", "light")
        assert user.get_preference("theme") == "light"
    
    def test_memory_quota_check(self, valid_user_data):
        """Test memory quota checking."""
        user = User(**valid_user_data)
        
        # Regular user
        assert user.can_create_memory(9999) is True
        assert user.can_create_memory(10000) is False
        
        # Admin (unlimited)
        user.promote_to_admin()
        assert user.can_create_memory(999999) is True
    
    def test_storage_quota_check(self, valid_user_data):
        """Test storage quota checking."""
        user = User(**valid_user_data)
        
        # Regular user
        assert user.can_use_storage(4000, 999) is True
        assert user.can_use_storage(4000, 1001) is False
        
        # Admin (unlimited)
        user.promote_to_admin()
        assert user.can_use_storage(999999, 999999) is True
    
    def test_to_dict(self, valid_user_data):
        """Test dictionary conversion."""
        user = User(**valid_user_data)
        user.update_preference("theme", "dark")
        user.record_login()
        
        data = user.to_dict()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["username"] == user.username
        assert data["role"] == UserRole.USER.value
        assert data["preferences"]["theme"] == "dark"
        assert data["last_login_at"] is not None


class TestUserRole:
    """Test UserRole enum."""
    
    def test_user_roles_exist(self):
        """Test that all user roles exist."""
        assert UserRole.USER.value == "user"
        assert UserRole.PREMIUM.value == "premium"
        assert UserRole.ADMIN.value == "admin"