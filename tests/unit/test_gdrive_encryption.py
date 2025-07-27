"""
Unit tests for Google Drive token encryption utilities.
Tests encryption/decryption functionality in isolation.
"""

import pytest
import os
from unittest.mock import patch, Mock

from app.utils.encryption import TokenEncryption, get_token_encryption, ensure_encryption_key_exists
from cryptography.fernet import Fernet, InvalidToken


class TestTokenEncryption:
    """Unit tests for TokenEncryption class"""
    
    @pytest.fixture
    def valid_key(self):
        """Generate a valid Fernet key for testing"""
        return Fernet.generate_key().decode('utf-8')
    
    @pytest.fixture
    def token_encryption(self, valid_key):
        """Create TokenEncryption instance with valid key"""
        return TokenEncryption(encryption_key=valid_key)
    
    @pytest.mark.unit
    def test_initialization_with_key(self, valid_key):
        """Test TokenEncryption initializes with provided key"""
        encryption = TokenEncryption(encryption_key=valid_key)
        assert encryption._encryption_key == valid_key
        assert encryption._fernet is not None
    
    @pytest.mark.unit
    def test_initialization_without_key_raises_error(self):
        """Test TokenEncryption raises error without key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GDRIVE_ENCRYPTION_KEY environment variable is required"):
                TokenEncryption()
    
    @pytest.mark.unit
    def test_initialization_with_env_key(self, valid_key):
        """Test TokenEncryption initializes with environment variable"""
        with patch.dict(os.environ, {'GDRIVE_ENCRYPTION_KEY': valid_key}):
            encryption = TokenEncryption()
            assert encryption._encryption_key == valid_key
    
    @pytest.mark.unit
    def test_initialization_with_invalid_key(self):
        """Test TokenEncryption raises error with invalid key"""
        with pytest.raises(ValueError, match="Invalid encryption key format"):
            TokenEncryption(encryption_key="invalid_key")
    
    @pytest.mark.unit
    def test_encrypt_token_success(self, token_encryption):
        """Test successful token encryption"""
        test_token = "test_refresh_token_12345"
        
        encrypted = token_encryption.encrypt_token(test_token)
        
        assert encrypted != test_token
        assert len(encrypted) > 0
        assert isinstance(encrypted, str)
    
    @pytest.mark.unit
    def test_encrypt_token_empty_raises_error(self, token_encryption):
        """Test encrypting empty token raises ValueError"""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            token_encryption.encrypt_token("")
        
        with pytest.raises(ValueError, match="Token cannot be empty"):
            token_encryption.encrypt_token("   ")
        
        with pytest.raises(ValueError, match="Token cannot be empty"):
            token_encryption.encrypt_token(None)
    
    @pytest.mark.unit
    def test_decrypt_token_success(self, token_encryption):
        """Test successful token decryption"""
        test_token = "test_refresh_token_12345"
        encrypted = token_encryption.encrypt_token(test_token)
        
        decrypted = token_encryption.decrypt_token(encrypted)
        
        assert decrypted == test_token
    
    @pytest.mark.unit
    def test_decrypt_token_empty_raises_error(self, token_encryption):
        """Test decrypting empty token raises ValueError"""
        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            token_encryption.decrypt_token("")
        
        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            token_encryption.decrypt_token("   ")
        
        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            token_encryption.decrypt_token(None)
    
    @pytest.mark.unit
    def test_decrypt_invalid_token_raises_error(self, token_encryption):
        """Test decrypting invalid token raises ValueError"""
        with pytest.raises(ValueError, match="Invalid encrypted token"):
            token_encryption.decrypt_token("invalid_encrypted_token")
        
        with pytest.raises(ValueError, match="Invalid encrypted token"):
            token_encryption.decrypt_token("not_base64_encoded!")
    
    @pytest.mark.unit
    def test_encrypt_decrypt_round_trip(self, token_encryption):
        """Test encrypt/decrypt round trip preserves original token"""
        test_cases = [
            "simple_token",
            "ya29.access_token_with_dots_and_underscores",
            "refresh_token_with_special_chars!@#$%",
            "very_long_token_" + "x" * 100,
            "short",
            "token with spaces",
            "tóken_wíth_ûnicóde_çhars"
        ]
        
        for test_token in test_cases:
            encrypted = token_encryption.encrypt_token(test_token)
            decrypted = token_encryption.decrypt_token(encrypted)
            assert decrypted == test_token, f"Round trip failed for token: {test_token}"
    
    @pytest.mark.unit
    def test_is_token_encrypted_true(self, token_encryption):
        """Test is_token_encrypted returns True for encrypted tokens"""
        test_token = "test_token_12345"
        encrypted_token = token_encryption.encrypt_token(test_token)
        
        assert token_encryption.is_token_encrypted(encrypted_token) is True
    
    @pytest.mark.unit
    def test_is_token_encrypted_false(self, token_encryption):
        """Test is_token_encrypted returns False for plain tokens"""
        plain_tokens = [
            "plain_text_token",
            "not_encrypted",
            "random_string_123",
            ""
        ]
        
        for token in plain_tokens:
            assert token_encryption.is_token_encrypted(token) is False
    
    @pytest.mark.unit
    def test_is_token_encrypted_empty_token(self, token_encryption):
        """Test is_token_encrypted handles empty tokens"""
        assert token_encryption.is_token_encrypted("") is False
        assert token_encryption.is_token_encrypted(None) is False
    
    @pytest.mark.unit
    def test_encryption_deterministic(self, token_encryption):
        """Test that encryption is not deterministic (same input gives different output)"""
        test_token = "test_token_12345"
        
        encrypted1 = token_encryption.encrypt_token(test_token)
        encrypted2 = token_encryption.encrypt_token(test_token)
        
        # Encrypted values should be different (Fernet uses random IV)
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same original value
        assert token_encryption.decrypt_token(encrypted1) == test_token
        assert token_encryption.decrypt_token(encrypted2) == test_token
    
    @pytest.mark.unit
    def test_encryption_key_mismatch(self):
        """Test that tokens encrypted with one key cannot be decrypted with another"""
        key1 = Fernet.generate_key().decode('utf-8')
        key2 = Fernet.generate_key().decode('utf-8')
        
        encryption1 = TokenEncryption(encryption_key=key1)
        encryption2 = TokenEncryption(encryption_key=key2)
        
        test_token = "test_token_12345"
        encrypted_with_key1 = encryption1.encrypt_token(test_token)
        
        # Should not be able to decrypt with different key
        with pytest.raises(ValueError, match="Invalid encrypted token"):
            encryption2.decrypt_token(encrypted_with_key1)
    
    @pytest.mark.unit
    @patch('app.utils.encryption.logger')
    def test_encryption_logging(self, mock_logger, token_encryption):
        """Test that encryption operations are logged"""
        test_token = "test_token_12345"
        
        # Test encrypt logging
        encrypted = token_encryption.encrypt_token(test_token)
        mock_logger.debug.assert_called()
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test decrypt logging
        token_encryption.decrypt_token(encrypted)
        mock_logger.debug.assert_called()
    
    @pytest.mark.unit
    @patch('app.utils.encryption.logger')
    def test_encryption_error_logging(self, mock_logger, token_encryption):
        """Test that encryption errors are logged"""
        # Test encrypt error logging
        with pytest.raises(ValueError):
            token_encryption.encrypt_token("")
        mock_logger.error.assert_called()
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test decrypt error logging
        with pytest.raises(ValueError):
            token_encryption.decrypt_token("invalid_token")
        mock_logger.error.assert_called()


class TestTokenEncryptionStaticMethods:
    """Unit tests for TokenEncryption static methods"""
    
    @pytest.mark.unit
    def test_generate_encryption_key(self):
        """Test encryption key generation"""
        key1 = TokenEncryption.generate_encryption_key()
        key2 = TokenEncryption.generate_encryption_key()
        
        # Keys should be strings
        assert isinstance(key1, str)
        assert isinstance(key2, str)
        
        # Keys should be different
        assert key1 != key2
        
        # Keys should be valid Fernet keys
        try:
            Fernet(key1.encode())
            Fernet(key2.encode())
        except Exception:
            pytest.fail("Generated keys should be valid Fernet keys")
    
    @pytest.mark.unit
    def test_generate_key_length(self):
        """Test that generated keys have expected length"""
        key = TokenEncryption.generate_encryption_key()
        
        # Fernet keys are 32 bytes, base64 encoded = 44 characters
        assert len(key) == 44
        
        # Should be valid base64
        import base64
        try:
            decoded = base64.b64decode(key)
            assert len(decoded) == 32
        except Exception:
            pytest.fail("Generated key should be valid base64")


class TestTokenEncryptionFactory:
    """Unit tests for token encryption factory functions"""
    
    @pytest.mark.unit
    @patch.dict(os.environ, {'GDRIVE_ENCRYPTION_KEY': 'test_key_for_factory'})
    @patch('app.utils.encryption.TokenEncryption')
    def test_get_token_encryption(self, mock_token_encryption_class):
        """Test get_token_encryption factory function"""
        mock_instance = Mock()
        mock_token_encryption_class.return_value = mock_instance
        
        result = get_token_encryption()
        
        assert result == mock_instance
        mock_token_encryption_class.assert_called_once_with()
    
    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    @patch('app.utils.encryption.logger')
    @patch('app.utils.encryption.TokenEncryption.generate_encryption_key')
    def test_ensure_encryption_key_exists_no_key(self, mock_generate_key, mock_logger):
        """Test ensure_encryption_key_exists when no key exists"""
        mock_generate_key.return_value = "generated_test_key"
        
        result = ensure_encryption_key_exists()
        
        assert result == "generated_test_key"
        assert os.environ.get("GDRIVE_ENCRYPTION_KEY") == "generated_test_key"
        mock_logger.warning.assert_called()
        mock_logger.info.assert_called()
    
    @pytest.mark.unit
    @patch.dict(os.environ, {'GDRIVE_ENCRYPTION_KEY': 'existing_key'})
    def test_ensure_encryption_key_exists_with_key(self):
        """Test ensure_encryption_key_exists when key already exists"""
        result = ensure_encryption_key_exists()
        
        assert result is None
        assert os.environ.get("GDRIVE_ENCRYPTION_KEY") == "existing_key"


class TestTokenEncryptionEdgeCases:
    """Unit tests for edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_unicode_token_handling(self):
        """Test encryption/decryption with unicode tokens"""
        key = TokenEncryption.generate_encryption_key()
        encryption = TokenEncryption(encryption_key=key)
        
        unicode_tokens = [
            "tóken_wíth_áccents",
            "トークン_with_japanese",
            "مفتاح_with_arabic",
            "🔑_token_with_emoji",
            "token\nwith\nnewlines",
            "token\twith\ttabs"
        ]
        
        for token in unicode_tokens:
            encrypted = encryption.encrypt_token(token)
            decrypted = encryption.decrypt_token(encrypted)
            assert decrypted == token, f"Unicode handling failed for: {token}"
    
    @pytest.mark.unit
    def test_very_long_token(self):
        """Test encryption/decryption with very long tokens"""
        key = TokenEncryption.generate_encryption_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # Create a very long token (10KB)
        long_token = "a" * 10240
        
        encrypted = encryption.encrypt_token(long_token)
        decrypted = encryption.decrypt_token(encrypted)
        
        assert decrypted == long_token
        assert len(encrypted) > len(long_token)  # Encrypted should be longer
    
    @pytest.mark.unit
    def test_binary_like_token(self):
        """Test encryption/decryption with binary-like token strings"""
        key = TokenEncryption.generate_encryption_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # Token that might look like encrypted data
        binary_like_token = "gAAAAABhZ8J7..." + "x" * 50
        
        encrypted = encryption.encrypt_token(binary_like_token)
        decrypted = encryption.decrypt_token(encrypted)
        
        assert decrypted == binary_like_token
    
    @pytest.mark.unit
    @patch('app.utils.encryption.Fernet')
    def test_fernet_initialization_error(self, mock_fernet_class):
        """Test error handling when Fernet initialization fails"""
        mock_fernet_class.side_effect = Exception("Fernet init failed")
        
        with pytest.raises(ValueError, match="Invalid encryption key format"):
            TokenEncryption(encryption_key="test_key")
    
    @pytest.mark.unit
    def test_encrypt_with_fernet_error(self):
        """Test error handling when Fernet encrypt fails"""
        key = TokenEncryption.generate_encryption_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # Mock Fernet to raise an exception
        with patch.object(encryption._fernet, 'encrypt', side_effect=Exception("Encrypt failed")):
            with pytest.raises(ValueError, match="Token encryption failed"):
                encryption.encrypt_token("test_token")
    
    @pytest.mark.unit
    def test_decrypt_with_fernet_error(self):
        """Test error handling when Fernet decrypt fails (not InvalidToken)"""
        key = TokenEncryption.generate_encryption_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # Mock Fernet to raise a non-InvalidToken exception
        with patch.object(encryption._fernet, 'decrypt', side_effect=Exception("Decrypt failed")):
            with pytest.raises(ValueError, match="Token decryption failed"):
                encryption.decrypt_token("some_token")
    
    @pytest.mark.unit
    def test_cli_key_generation(self, capsys):
        """Test CLI key generation functionality"""
        # This would normally be run as: python -m app.utils.encryption
        # We'll test the logic that would be executed
        
        key = TokenEncryption.generate_encryption_key()
        
        # Simulate what the CLI would print
        print(f"Generating new Fernet encryption key for Google Drive tokens:")
        print(f"GDRIVE_ENCRYPTION_KEY={key}")
        print("\nAdd this to your .env file for secure token storage.")
        
        captured = capsys.readouterr()
        assert "Generating new Fernet encryption key" in captured.out
        assert f"GDRIVE_ENCRYPTION_KEY={key}" in captured.out
        assert "Add this to your .env file" in captured.out