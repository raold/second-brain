"""
Unit tests for Google Drive authentication service.
Tests OAuth service logic in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from app.services.gdrive.auth_service import GoogleAuthService
from app.services.gdrive.exceptions import GoogleAuthError, GoogleTokenError


class TestGoogleAuthServiceUnit:
    """Unit tests for GoogleAuthService class"""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables for testing"""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id_12345")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret_67890")
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        monkeypatch.setenv("GDRIVE_ENCRYPTION_KEY", "test_encryption_key_base64_encoded")
    
    @pytest.fixture
    def mock_encryption(self):
        """Mock token encryption"""
        encryption = Mock()
        encryption.encrypt_token.return_value = "encrypted_token_data"
        encryption.decrypt_token.return_value = "decrypted_refresh_token"
        return encryption
    
    @pytest.fixture
    def auth_service(self, mock_env, mock_encryption):
        """Create auth service with mocked dependencies"""
        with patch('app.services.gdrive.auth_service.get_token_encryption', return_value=mock_encryption):
            return GoogleAuthService()
    
    @pytest.mark.unit
    def test_initialization_success(self, auth_service):
        """Test successful service initialization"""
        assert auth_service.client_id == "test_client_id_12345"
        assert auth_service.client_secret == "test_client_secret_67890"
        assert auth_service.redirect_uri == "http://localhost:8000/auth/google/callback"
        assert auth_service.SCOPES == [
            'https://www.googleapis.com/auth/drive.readonly',
            'openid',
            'email',
            'profile'
        ]
    
    @pytest.mark.unit
    def test_initialization_missing_client_id(self, monkeypatch, mock_encryption):
        """Test initialization fails without client ID"""
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_secret")
        
        with patch('app.services.gdrive.auth_service.get_token_encryption', return_value=mock_encryption):
            with pytest.raises(GoogleAuthError, match="Google OAuth credentials not configured"):
                GoogleAuthService()
    
    @pytest.mark.unit
    def test_initialization_missing_client_secret(self, monkeypatch, mock_encryption):
        """Test initialization fails without client secret"""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_id")
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        
        with patch('app.services.gdrive.auth_service.get_token_encryption', return_value=mock_encryption):
            with pytest.raises(GoogleAuthError, match="Google OAuth credentials not configured"):
                GoogleAuthService()
    
    @pytest.mark.unit
    def test_generate_oauth_url_basic(self, auth_service):
        """Test basic OAuth URL generation"""
        user_id = "test_user_123"
        
        with patch('app.services.gdrive.auth_service.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.from_client_config.return_value = mock_flow
            mock_flow.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?client_id=test",
                "mock_state"
            )
            
            result = auth_service.generate_oauth_url(user_id)
            
            assert "auth_url" in result
            assert "state" in result
            assert result["auth_url"] == "https://accounts.google.com/o/oauth2/auth?client_id=test"
            assert result["state"].startswith(f"{user_id}:")
    
    @pytest.mark.unit
    def test_generate_oauth_url_with_custom_state(self, auth_service):
        """Test OAuth URL generation with custom state"""
        user_id = "test_user_123"
        custom_state = "custom_state_value"
        
        with patch('app.services.gdrive.auth_service.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.from_client_config.return_value = mock_flow
            mock_flow.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?client_id=test",
                "mock_state"
            )
            
            result = auth_service.generate_oauth_url(user_id, custom_state)
            
            assert result["state"] == f"{user_id}:{custom_state}"
            
            # Verify Flow was called with correct state
            call_args = mock_flow.authorization_url.call_args
            assert call_args[1]["state"] == f"{user_id}:{custom_state}"
    
    @pytest.mark.unit
    def test_generate_oauth_url_flow_error(self, auth_service):
        """Test OAuth URL generation with Flow error"""
        user_id = "test_user_123"
        
        with patch('app.services.gdrive.auth_service.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.side_effect = Exception("Flow creation failed")
            
            with pytest.raises(GoogleAuthError, match="Failed to generate OAuth URL"):
                auth_service.generate_oauth_url(user_id)
    
    @pytest.mark.unit
    def test_verify_state_valid(self, auth_service):
        """Test state verification with valid state"""
        user_id = "test_user_123"
        state = f"{user_id}:random_state_value"
        
        assert auth_service._verify_state(state, user_id) is True
    
    @pytest.mark.unit
    def test_verify_state_invalid(self, auth_service):
        """Test state verification with invalid states"""
        user_id = "test_user_123"
        
        # Test various invalid states
        invalid_states = [
            "no_colon_state",
            "wrong_user:state",
            "test_user_123",  # No colon
            "",
            ":",
            ":state_only",
            "user_only:",
        ]
        
        for invalid_state in invalid_states:
            assert auth_service._verify_state(invalid_state, user_id) is False
    
    @pytest.mark.unit
    def test_verify_state_exception_handling(self, auth_service):
        """Test state verification handles exceptions"""
        user_id = "test_user_123"
        
        # None should not cause exception
        assert auth_service._verify_state(None, user_id) is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, auth_service):
        """Test successful user info retrieval"""
        mock_credentials = Mock()
        
        with patch('app.services.gdrive.auth_service.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            mock_service.userinfo().get().execute.return_value = {
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/pic.jpg",
                "verified_email": True
            }
            
            result = await auth_service._get_user_info(mock_credentials)
            
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["picture"] == "https://example.com/pic.jpg"
            assert result["verified_email"] is True
            
            mock_build.assert_called_once_with('oauth2', 'v2', credentials=mock_credentials)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_info_api_error(self, auth_service):
        """Test user info retrieval with API error"""
        mock_credentials = Mock()
        
        with patch('app.services.gdrive.auth_service.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            mock_service.userinfo().get().execute.side_effect = Exception("API error")
            
            with pytest.raises(GoogleAuthError, match="Failed to get user info"):
                await auth_service._get_user_info(mock_credentials)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_oauth_callback_invalid_state(self, auth_service):
        """Test OAuth callback with invalid state"""
        code = "test_auth_code"
        invalid_state = "invalid_state"
        user_id = "test_user_123"
        
        with pytest.raises(GoogleAuthError, match="Invalid state parameter"):
            await auth_service.handle_oauth_callback(code, invalid_state, user_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_oauth_callback_success(self, auth_service):
        """Test successful OAuth callback handling"""
        code = "test_auth_code"
        user_id = "test_user_123"
        state = f"{user_id}:test_state"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        
        user_info = {
            "email": "test@example.com",
            "name": "Test User",
            "verified_email": True
        }
        
        with patch('app.services.gdrive.auth_service.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.from_client_config.return_value = mock_flow
            mock_flow.credentials = mock_credentials
            
            with patch.object(auth_service, '_get_user_info', new_callable=AsyncMock) as mock_get_user_info:
                mock_get_user_info.return_value = user_info
                
                with patch.object(auth_service, '_store_credentials', new_callable=AsyncMock) as mock_store:
                    result = await auth_service.handle_oauth_callback(code, state, user_id)
                    
                    assert result["user_id"] == user_id
                    assert result["user_info"] == user_info
                    assert result["drive_access"] is True
                    assert result["credentials_stored"] is True
                    
                    mock_flow.fetch_token.assert_called_once_with(code=code)
                    mock_get_user_info.assert_called_once_with(mock_credentials)
                    mock_store.assert_called_once_with(user_id, mock_credentials, user_info)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_oauth_callback_flow_error(self, auth_service):
        """Test OAuth callback with Flow error"""
        code = "test_auth_code"
        user_id = "test_user_123"
        state = f"{user_id}:test_state"
        
        with patch('app.services.gdrive.auth_service.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.side_effect = Exception("Flow error")
            
            with pytest.raises(GoogleAuthError, match="OAuth callback failed"):
                await auth_service.handle_oauth_callback(code, state, user_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_credentials_success(self, auth_service):
        """Test successful credential storage"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.token = "test_access_token"
        
        user_info = {"email": "test@example.com", "name": "Test User"}
        
        mock_session = AsyncMock()
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            await auth_service._store_credentials(user_id, mock_credentials, user_info)
            
            # Verify database operations
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify encryption was called
            auth_service.encryption.encrypt_token.assert_called_once_with("test_refresh_token")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_credentials_no_refresh_token(self, auth_service):
        """Test credential storage without refresh token"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = None
        
        user_info = {"email": "test@example.com"}
        
        with pytest.raises(GoogleTokenError, match="No refresh token received"):
            await auth_service._store_credentials(user_id, mock_credentials, user_info)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_credentials_database_error(self, auth_service):
        """Test credential storage with database error"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.token = "test_access_token"
        
        user_info = {"email": "test@example.com"}
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            with pytest.raises(GoogleTokenError, match="Failed to store credentials"):
                await auth_service._store_credentials(user_id, mock_credentials, user_info)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_credentials_success(self, auth_service):
        """Test successful user credentials retrieval"""
        user_id = "test_user_123"
        
        # Mock database result
        mock_cred_record = Mock()
        mock_cred_record.encrypted_refresh_token = "encrypted_token_data"
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_cred_record
        mock_session.execute.return_value = mock_result
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('app.services.gdrive.auth_service.Credentials') as mock_credentials_class:
                mock_credentials = Mock()
                mock_credentials.valid = True
                mock_credentials_class.return_value = mock_credentials
                
                result = await auth_service.get_user_credentials(user_id)
                
                assert result == mock_credentials
                
                # Verify decryption was called
                auth_service.encryption.decrypt_token.assert_called_once_with("encrypted_token_data")
                
                # Verify credentials were created with correct parameters
                mock_credentials_class.assert_called_once_with(
                    token=None,
                    refresh_token="decrypted_refresh_token",
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=auth_service.client_id,
                    client_secret=auth_service.client_secret,
                    scopes=auth_service.SCOPES
                )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_credentials_not_found(self, auth_service):
        """Test user credentials retrieval when not found"""
        user_id = "test_user_123"
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await auth_service.get_user_credentials(user_id)
            
            assert result is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_credentials_refresh_needed(self, auth_service):
        """Test user credentials retrieval with token refresh"""
        user_id = "test_user_123"
        
        # Mock database result
        mock_cred_record = Mock()
        mock_cred_record.encrypted_refresh_token = "encrypted_token_data"
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_cred_record
        mock_session.execute.return_value = mock_result
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            with patch('app.services.gdrive.auth_service.Credentials') as mock_credentials_class:
                mock_credentials = Mock()
                mock_credentials.valid = False  # Needs refresh
                mock_credentials_class.return_value = mock_credentials
                
                with patch('app.services.gdrive.auth_service.Request') as mock_request_class:
                    mock_request = Mock()
                    mock_request_class.return_value = mock_request
                    
                    result = await auth_service.get_user_credentials(user_id)
                    
                    assert result == mock_credentials
                    
                    # Verify refresh was called
                    mock_credentials.refresh.assert_called_once_with(mock_request)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_credentials_database_error(self, auth_service):
        """Test user credentials retrieval with database error"""
        user_id = "test_user_123"
        
        with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")
            
            with pytest.raises(GoogleTokenError, match="Failed to get user credentials"):
                await auth_service.get_user_credentials(user_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_user_access_success(self, auth_service):
        """Test successful user access revocation"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = mock_credentials
            
            with patch('app.services.gdrive.auth_service.requests') as mock_requests:
                mock_requests.post.return_value = mock_response
                
                with patch('app.services.gdrive.auth_service.get_db_session') as mock_get_session:
                    mock_session = AsyncMock()
                    mock_get_session.return_value.__aenter__.return_value = mock_session
                    
                    result = await auth_service.revoke_user_access(user_id)
                    
                    assert result is True
                    
                    # Verify revoke API call
                    mock_requests.post.assert_called_once()
                    call_args = mock_requests.post.call_args[0]
                    assert "revoke" in call_args[0]
                    assert "test_refresh_token" in call_args[0]
                    
                    # Verify database update
                    mock_session.execute.assert_called_once()
                    mock_session.commit.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_user_access_no_credentials(self, auth_service):
        """Test user access revocation with no credentials"""
        user_id = "test_user_123"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = None
            
            result = await auth_service.revoke_user_access(user_id)
            
            assert result is True  # Should succeed if no credentials to revoke
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_revoke_user_access_api_error(self, auth_service):
        """Test user access revocation with API error"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = mock_credentials
            
            with patch('app.services.gdrive.auth_service.requests') as mock_requests:
                mock_requests.post.side_effect = Exception("Network error")
                
                result = await auth_service.revoke_user_access(user_id)
                
                assert result is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_drive_connectivity_success(self, auth_service):
        """Test successful Drive connectivity check"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = mock_credentials
            
            with patch('app.services.gdrive.auth_service.build') as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service
                mock_service.about().get().execute.return_value = {
                    "user": {"emailAddress": "test@example.com"},
                    "storageQuota": {
                        "limit": "1000000000000",
                        "usage": "500000000000"
                    }
                }
                
                result = await auth_service.check_drive_connectivity(user_id)
                
                assert result["connected"] is True
                assert result["user_email"] == "test@example.com"
                assert "storage_quota" in result
                assert "last_checked" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_drive_connectivity_no_credentials(self, auth_service):
        """Test Drive connectivity check with no credentials"""
        user_id = "test_user_123"
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = None
            
            result = await auth_service.check_drive_connectivity(user_id)
            
            assert result["connected"] is False
            assert result["error"] == "No credentials found"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_drive_connectivity_api_error(self, auth_service):
        """Test Drive connectivity check with API error"""
        user_id = "test_user_123"
        
        mock_credentials = Mock()
        
        with patch.object(auth_service, 'get_user_credentials', new_callable=AsyncMock) as mock_get_creds:
            mock_get_creds.return_value = mock_credentials
            
            with patch('app.services.gdrive.auth_service.build') as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service
                mock_service.about().get().execute.side_effect = Exception("API error")
                
                result = await auth_service.check_drive_connectivity(user_id)
                
                assert result["connected"] is False
                assert "error" in result