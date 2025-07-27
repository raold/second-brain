"""
Integration tests for Google Drive OAuth authentication.
Tests the complete OAuth flow and token management.
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.gdrive.auth_service import GoogleAuthService
from app.services.gdrive.exceptions import GoogleAuthError, GoogleTokenError
from app.utils.encryption import TokenEncryption
from app.models.gdrive import UserGoogleCredentials


class TestGoogleDriveAuthIntegration:
    """Integration tests for Google Drive authentication"""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        monkeypatch.setenv("GDRIVE_ENCRYPTION_KEY", TokenEncryption.generate_encryption_key())
    
    @pytest.fixture
    def auth_service(self, mock_env):
        """Create auth service with mocked environment"""
        return GoogleAuthService()
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials object"""
        creds = Mock()
        creds.refresh_token = "mock_refresh_token"
        creds.token = "mock_access_token"
        creds.valid = True
        creds.refresh = Mock()
        return creds
    
    @pytest.mark.integration
    def test_auth_service_initialization(self, auth_service):
        """Test auth service initializes with proper configuration"""
        assert auth_service.client_id == "test_client_id"
        assert auth_service.client_secret == "test_client_secret"
        assert auth_service.redirect_uri == "http://localhost:8000/auth/google/callback"
        assert auth_service.SCOPES == [
            'https://www.googleapis.com/auth/drive.readonly',
            'openid',
            'email',
            'profile'
        ]
    
    @pytest.mark.integration
    def test_generate_oauth_url(self, auth_service):
        """Test OAuth URL generation"""
        user_id = "test_user_123"
        
        result = auth_service.generate_oauth_url(user_id)
        
        assert "auth_url" in result
        assert "state" in result
        assert result["auth_url"].startswith("https://accounts.google.com/o/oauth2/auth")
        assert "client_id=test_client_id" in result["auth_url"]
        assert "scope=" in result["auth_url"]
        assert "access_type=offline" in result["auth_url"]
        assert result["state"].startswith(f"{user_id}:")
    
    @pytest.mark.integration
    def test_generate_oauth_url_with_custom_state(self, auth_service):
        """Test OAuth URL generation with custom state"""
        user_id = "test_user_123"
        custom_state = "custom_state_value"
        
        result = auth_service.generate_oauth_url(user_id, custom_state)
        
        assert result["state"] == f"{user_id}:{custom_state}"
        assert f"state={user_id}%3A{custom_state}" in result["auth_url"]
    
    @pytest.mark.integration
    def test_state_verification(self, auth_service):
        """Test state parameter verification"""
        user_id = "test_user_123"
        
        # Valid state
        valid_state = f"{user_id}:some_random_state"
        assert auth_service._verify_state(valid_state, user_id) is True
        
        # Invalid states
        assert auth_service._verify_state("invalid_state", user_id) is False
        assert auth_service._verify_state(f"wrong_user:state", user_id) is False
        assert auth_service._verify_state("no_colon_state", user_id) is False
        assert auth_service._verify_state("", user_id) is False
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_state(self, auth_service):
        """Test OAuth callback with invalid state"""
        code = "test_auth_code"
        invalid_state = "invalid_state"
        user_id = "test_user_123"
        
        with pytest.raises(GoogleAuthError, match="Invalid state parameter"):
            await auth_service.handle_oauth_callback(code, invalid_state, user_id)
    
    @pytest.mark.integration 
    @pytest.mark.asyncio
    @patch('app.services.gdrive.auth_service.Flow')
    @patch('app.services.gdrive.auth_service.build')
    async def test_oauth_callback_success(self, mock_build, mock_flow_class, auth_service):
        """Test successful OAuth callback"""
        # Setup mocks
        mock_flow = Mock()
        mock_flow_class.from_client_config.return_value = mock_flow
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        mock_flow.credentials = mock_credentials
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.userinfo().get().execute.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "verified_email": True
        }
        
        # Test callback
        user_id = "test_user_123"
        state = f"{user_id}:test_state"
        code = "test_auth_code"
        
        with patch.object(auth_service, '_store_credentials', new_callable=AsyncMock) as mock_store:
            result = await auth_service.handle_oauth_callback(code, state, user_id)
            
            assert result["user_id"] == user_id
            assert result["user_info"]["email"] == "test@example.com"
            assert result["drive_access"] is True
            assert result["credentials_stored"] is True
            
            # Verify store_credentials was called
            mock_store.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('app.services.gdrive.auth_service.build')
    async def test_get_user_info(self, mock_build, auth_service):
        """Test getting user info from Google"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.userinfo().get().execute.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "verified_email": True
        }
        
        mock_credentials = Mock()
        
        result = await auth_service._get_user_info(mock_credentials)
        
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["verified_email"] is True
        
        mock_build.assert_called_once_with('oauth2', 'v2', credentials=mock_credentials)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_token_encryption_integration(self, auth_service):
        """Test token encryption/decryption integration"""
        test_token = "test_refresh_token_12345"
        
        # Encrypt token
        encrypted = auth_service.encryption.encrypt_token(test_token)
        assert encrypted != test_token
        assert len(encrypted) > len(test_token)
        
        # Decrypt token
        decrypted = auth_service.encryption.decrypt_token(encrypted)
        assert decrypted == test_token
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('app.services.gdrive.auth_service.build')
    async def test_check_drive_connectivity_success(self, mock_build, auth_service):
        """Test successful Drive connectivity check"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.about().get().execute.return_value = {
            "user": {"emailAddress": "test@example.com"},
            "storageQuota": {
                "limit": "1000000000000",
                "usage": "500000000000"
            }
        }
        
        user_id = "test_user_123"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = Mock()
            
            result = await auth_service.check_drive_connectivity(user_id)
            
            assert result["connected"] is True
            assert result["user_email"] == "test@example.com"
            assert "storage_quota" in result
            assert "last_checked" in result
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_check_drive_connectivity_no_credentials(self, auth_service):
        """Test Drive connectivity check with no credentials"""
        user_id = "test_user_123"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = None
            
            result = await auth_service.check_drive_connectivity(user_id)
            
            assert result["connected"] is False
            assert result["error"] == "No credentials found"
    
    @pytest.mark.integration
    def test_missing_environment_variables(self, monkeypatch):
        """Test auth service fails with missing environment variables"""
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        
        with pytest.raises(GoogleAuthError, match="Google OAuth credentials not configured"):
            GoogleAuthService()
    
    @pytest.mark.integration
    @patch('app.services.gdrive.auth_service.requests')
    @pytest.mark.asyncio
    async def test_revoke_user_access(self, mock_requests, auth_service):
        """Test revoking user access"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        user_id = "test_user_123"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_credentials = Mock()
            mock_credentials.refresh_token = "test_refresh_token"
            mock_get_creds.return_value = mock_credentials
            
            with patch('app.services.gdrive.auth_service.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                result = await auth_service.revoke_user_access(user_id)
                
                assert result is True
                mock_requests.post.assert_called_once()
                mock_session.execute.assert_called_once()
                mock_session.commit.assert_called_once()


@pytest.mark.integration
class TestTokenEncryptionIntegration:
    """Integration tests for token encryption utilities"""
    
    @pytest.fixture
    def encryption_key(self):
        """Generate encryption key for testing"""
        return TokenEncryption.generate_encryption_key()
    
    @pytest.fixture
    def token_encryption(self, encryption_key, monkeypatch):
        """Create token encryption instance"""
        monkeypatch.setenv("GDRIVE_ENCRYPTION_KEY", encryption_key)
        return TokenEncryption()
    
    @pytest.mark.integration
    def test_encrypt_decrypt_cycle(self, token_encryption):
        """Test complete encrypt/decrypt cycle"""
        original_token = "ya29.test_access_token_with_long_string_12345"
        
        # Encrypt
        encrypted = token_encryption.encrypt_token(original_token)
        assert encrypted != original_token
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = token_encryption.decrypt_token(encrypted)
        assert decrypted == original_token
    
    @pytest.mark.integration
    def test_encrypt_empty_token(self, token_encryption):
        """Test encrypting empty token raises error"""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            token_encryption.encrypt_token("")
        
        with pytest.raises(ValueError, match="Token cannot be empty"):
            token_encryption.encrypt_token("   ")
    
    @pytest.mark.integration
    def test_decrypt_invalid_token(self, token_encryption):
        """Test decrypting invalid token raises error"""
        with pytest.raises(ValueError, match="Invalid encrypted token"):
            token_encryption.decrypt_token("invalid_encrypted_token")
        
        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            token_encryption.decrypt_token("")
    
    @pytest.mark.integration
    def test_is_token_encrypted(self, token_encryption):
        """Test token encryption detection"""
        plain_token = "plain_text_token"
        encrypted_token = token_encryption.encrypt_token(plain_token)
        
        assert token_encryption.is_token_encrypted(encrypted_token) is True
        assert token_encryption.is_token_encrypted(plain_token) is False
        assert token_encryption.is_token_encrypted("") is False
    
    @pytest.mark.integration
    def test_different_keys_fail_decryption(self, monkeypatch):
        """Test that different encryption keys fail decryption"""
        key1 = TokenEncryption.generate_encryption_key()
        key2 = TokenEncryption.generate_encryption_key()
        
        # Encrypt with first key
        monkeypatch.setenv("GDRIVE_ENCRYPTION_KEY", key1)
        encryption1 = TokenEncryption()
        encrypted = encryption1.encrypt_token("test_token")
        
        # Try to decrypt with second key
        monkeypatch.setenv("GDRIVE_ENCRYPTION_KEY", key2)
        encryption2 = TokenEncryption()
        
        with pytest.raises(ValueError, match="Invalid encrypted token"):
            encryption2.decrypt_token(encrypted)
    
    @pytest.mark.integration
    def test_key_generation(self):
        """Test encryption key generation"""
        key1 = TokenEncryption.generate_encryption_key()
        key2 = TokenEncryption.generate_encryption_key()
        
        assert len(key1) > 0
        assert len(key2) > 0
        assert key1 != key2  # Keys should be unique
        
        # Keys should be valid base64
        import base64
        try:
            base64.b64decode(key1)
            base64.b64decode(key2)
        except Exception:
            pytest.fail("Generated keys should be valid base64")


@pytest.mark.integration
class TestGoogleDriveAPIRoutes:
    """Integration tests for Google Drive API routes"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing"""
        from fastapi.testclient import TestClient
        from app.app import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for API calls"""
        return {"api_key": "test-token-for-development"}
    
    @pytest.mark.integration
    def test_gdrive_routes_registered(self, test_client):
        """Test that Google Drive routes are properly registered"""
        # Test that the routes exist (should return method not allowed or auth error, not 404)
        
        # Test connect endpoint
        response = test_client.post("/api/v1/gdrive/connect")
        assert response.status_code != 404  # Route exists
        
        # Test status endpoint
        response = test_client.get("/api/v1/gdrive/status")
        assert response.status_code != 404  # Route exists
        
        # Test disconnect endpoint
        response = test_client.delete("/api/v1/gdrive/disconnect")
        assert response.status_code != 404  # Route exists
    
    @pytest.mark.integration 
    @patch('app.services.gdrive.auth_service.GoogleAuthService')
    def test_connect_endpoint_success(self, mock_auth_service_class, test_client, auth_headers):
        """Test successful OAuth initiation"""
        mock_auth_service = Mock()
        mock_auth_service_class.return_value = mock_auth_service
        mock_auth_service.generate_oauth_url.return_value = {
            "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=test",
            "state": "test_user:random_state"
        }
        
        response = test_client.post(
            "/api/v1/gdrive/connect",
            json={"redirect_after_auth": "/dashboard"},
            params=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "expires_in" in data
    
    @pytest.mark.integration
    @patch('app.services.gdrive.auth_service.GoogleAuthService')
    def test_status_endpoint_disconnected(self, mock_auth_service_class, test_client, auth_headers):
        """Test status endpoint when disconnected"""
        mock_auth_service = Mock()
        mock_auth_service_class.return_value = mock_auth_service
        mock_auth_service.check_drive_connectivity = AsyncMock(return_value={
            "connected": False,
            "error": "No credentials found"
        })
        
        response = test_client.get("/api/v1/gdrive/status", params=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert "error" in data
    
    @pytest.mark.integration
    def test_oauth_callback_missing_params(self, test_client):
        """Test OAuth callback with missing parameters"""
        response = test_client.get("/api/v1/gdrive/callback")
        
        # Should redirect to dashboard with error
        assert response.status_code == 302
        assert "error" in response.headers["location"]
    
    @pytest.mark.integration
    def test_oauth_callback_with_error(self, test_client):
        """Test OAuth callback with error parameter"""
        response = test_client.get(
            "/api/v1/gdrive/callback",
            params={
                "error": "access_denied",
                "state": "test_user:state"
            }
        )
        
        # Should redirect to dashboard with error
        assert response.status_code == 302
        location = response.headers["location"]
        assert "error=oauth_denied" in location
        assert "details=access_denied" in location