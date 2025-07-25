"""
Unit tests for User domain model.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.models.user import (
    User,
    UserId,
    UserRole,
    UserPreferences,
    UserFactory,
)


class TestUserId:
    """Tests for UserId value object."""
    
    def test_create_user_id(self):
        """Test creating a UserId."""
        id_value = uuid4()
        user_id = UserId(id_value)
        assert user_id.value == id_value
    
    def test_user_id_equality(self):
        """Test UserId equality."""
        id_value = uuid4()
        user_id1 = UserId(id_value)
        user_id2 = UserId(id_value)
        user_id3 = UserId(uuid4())
        
        assert user_id1 == user_id2
        assert user_id1 != user_id3
    
    def test_user_id_string_representation(self):
        """Test UserId string conversion."""
        id_value = uuid4()
        user_id = UserId(id_value)
        assert str(user_id) == str(id_value)


class TestUserRole:
    """Tests for UserRole enum."""
    
    def test_user_role_values(self):
        """Test all user role values exist."""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"
        assert UserRole.PREMIUM == "premium"
    
    def test_user_role_from_string(self):
        """Test creating UserRole from string."""
        assert UserRole("user") == UserRole.USER
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("premium") == UserRole.PREMIUM
    
    def test_invalid_user_role(self):
        """Test invalid user role raises error."""
        with pytest.raises(ValueError):
            UserRole("invalid_role")


class TestUserPreferences:
    """Tests for UserPreferences value object."""
    
    def test_create_default_preferences(self):
        """Test creating default user preferences."""
        prefs = UserPreferences()
        
        assert prefs.theme == "light"
        assert prefs.language == "en"
        assert prefs.timezone == "UTC"
        assert prefs.email_notifications is True
        assert prefs.daily_summary is False
        assert prefs.memory_retention_days == 365
    
    def test_create_custom_preferences(self):
        """Test creating custom user preferences."""
        prefs = UserPreferences(
            theme="dark",
            language="es",
            timezone="America/New_York",
            email_notifications=False,
            daily_summary=True,
            memory_retention_days=180,
        )
        
        assert prefs.theme == "dark"
        assert prefs.language == "es"
        assert prefs.timezone == "America/New_York"
        assert prefs.email_notifications is False
        assert prefs.daily_summary is True
        assert prefs.memory_retention_days == 180
    
    def test_preferences_to_dict(self):
        """Test converting preferences to dictionary."""
        prefs = UserPreferences(theme="dark", language="fr")
        prefs_dict = prefs.to_dict()
        
        assert prefs_dict["theme"] == "dark"
        assert prefs_dict["language"] == "fr"
        assert "timezone" in prefs_dict
        assert "email_notifications" in prefs_dict
    
    def test_preferences_from_dict(self):
        """Test creating preferences from dictionary."""
        data = {
            "theme": "dark",
            "language": "de",
            "timezone": "Europe/Berlin",
            "email_notifications": False,
        }
        prefs = UserPreferences.from_dict(data)
        
        assert prefs.theme == "dark"
        assert prefs.language == "de"
        assert prefs.timezone == "Europe/Berlin"
        assert prefs.email_notifications is False


class TestUser:
    """Tests for User aggregate."""
    
    def test_create_user(self):
        """Test creating a user."""
        user_id = UserId(uuid4())
        
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
        assert isinstance(user.preferences, UserPreferences)
    
    def test_user_with_optional_fields(self):
        """Test creating user with all optional fields."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            bio="This is my bio",
            role=UserRole.PREMIUM,
            is_verified=True,
            preferences=UserPreferences(theme="dark"),
        )
        
        assert user.full_name == "Test User"
        assert user.avatar_url == "https://example.com/avatar.jpg"
        assert user.bio == "This is my bio"
        assert user.role == UserRole.PREMIUM
        assert user.is_verified is True
        assert user.preferences.theme == "dark"
    
    def test_user_timestamps(self):
        """Test user timestamps."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert user.last_login_at is None
    
    def test_user_quotas(self):
        """Test user quotas."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.memory_limit == 10000
        assert user.storage_limit_mb == 5000
        assert user.api_rate_limit == 1000
    
    def test_user_validation(self):
        """Test user validation rules."""
        # Test invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            User(
                id=UserId(uuid4()),
                email="invalid-email",
                username="testuser",
                password_hash="hashed_password",
            )
        
        # Test empty username
        with pytest.raises(ValueError, match="Username cannot be empty"):
            User(
                id=UserId(uuid4()),
                email="test@example.com",
                username="",
                password_hash="hashed_password",
            )
        
        # Test short username
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            User(
                id=UserId(uuid4()),
                email="test@example.com",
                username="ab",
                password_hash="hashed_password",
            )
        
        # Test invalid username characters
        with pytest.raises(ValueError, match="Username can only contain"):
            User(
                id=UserId(uuid4()),
                email="test@example.com",
                username="test@user",
                password_hash="hashed_password",
            )
    
    def test_update_profile(self):
        """Test updating user profile."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        user.update_profile(
            full_name="Updated Name",
            bio="Updated bio",
            avatar_url="https://example.com/new-avatar.jpg",
        )
        
        assert user.full_name == "Updated Name"
        assert user.bio == "Updated bio"
        assert user.avatar_url == "https://example.com/new-avatar.jpg"
    
    def test_update_preferences(self):
        """Test updating user preferences."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        new_prefs = UserPreferences(
            theme="dark",
            language="es",
            email_notifications=False,
        )
        user.update_preferences(new_prefs)
        
        assert user.preferences.theme == "dark"
        assert user.preferences.language == "es"
        assert user.preferences.email_notifications is False
    
    def test_activate_deactivate_user(self):
        """Test activating and deactivating user."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.is_active is True
        
        user.deactivate()
        assert user.is_active is False
        
        user.activate()
        assert user.is_active is True
    
    def test_verify_user(self):
        """Test verifying user."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.is_verified is False
        
        user.verify()
        assert user.is_verified is True
    
    def test_update_last_login(self):
        """Test updating last login time."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.last_login_at is None
        
        user.update_last_login()
        assert isinstance(user.last_login_at, datetime)
        assert user.last_login_at <= datetime.utcnow()
    
    def test_update_password(self):
        """Test updating password."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="old_hash",
        )
        
        user.update_password("new_hash")
        assert user.password_hash == "new_hash"
    
    def test_update_quotas(self):
        """Test updating user quotas."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        user.update_quotas(
            memory_limit=20000,
            storage_limit_mb=10000,
            api_rate_limit=5000,
        )
        
        assert user.memory_limit == 20000
        assert user.storage_limit_mb == 10000
        assert user.api_rate_limit == 5000
    
    def test_upgrade_to_premium(self):
        """Test upgrading user to premium."""
        user = User(
            id=UserId(uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )
        
        assert user.role == UserRole.USER
        
        user.upgrade_to_premium()
        assert user.role == UserRole.PREMIUM
        assert user.memory_limit == 50000  # Premium limits
        assert user.storage_limit_mb == 20000
        assert user.api_rate_limit == 10000


class TestUserFactory:
    """Tests for UserFactory."""
    
    def test_create_user(self):
        """Test creating a regular user."""
        user = UserFactory.create_user(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password"
        assert user.full_name == "Test User"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
    
    def test_create_admin(self):
        """Test creating an admin user."""
        admin = UserFactory.create_admin(
            email="admin@example.com",
            username="adminuser",
            password_hash="hashed_password",
        )
        
        assert admin.role == UserRole.ADMIN
        assert admin.is_active is True
        assert admin.is_verified is True  # Admins are pre-verified
    
    def test_create_premium_user(self):
        """Test creating a premium user."""
        premium = UserFactory.create_premium_user(
            email="premium@example.com",
            username="premiumuser",
            password_hash="hashed_password",
        )
        
        assert premium.role == UserRole.PREMIUM
        assert premium.memory_limit == 50000
        assert premium.storage_limit_mb == 20000
        assert premium.api_rate_limit == 10000