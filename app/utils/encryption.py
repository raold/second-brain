"""
Secure encryption utilities for Google Drive integration.
Based on Gemini 2.5 Pro recommendations for enterprise token storage.
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TokenEncryption:
    """Secure token encryption/decryption for Google OAuth tokens"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize token encryption
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, loads from environment.
        """
        self._encryption_key = encryption_key or os.getenv("GDRIVE_ENCRYPTION_KEY")
        
        if not self._encryption_key:
            raise ValueError(
                "GDRIVE_ENCRYPTION_KEY environment variable is required for token encryption"
            )
        
        try:
            self._fernet = Fernet(self._encryption_key.encode())
            logger.info("Token encryption initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize token encryption: {e}")
            raise ValueError(f"Invalid encryption key format: {e}")
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token string
        
        Args:
            token: Plain text token to encrypt
            
        Returns:
            Base64-encoded encrypted token
            
        Raises:
            ValueError: If token is empty or encryption fails
        """
        if not token or not token.strip():
            raise ValueError("Token cannot be empty")
        
        try:
            encrypted_bytes = self._fernet.encrypt(token.encode('utf-8'))
            encrypted_token = encrypted_bytes.decode('utf-8')
            
            logger.debug("Token encrypted successfully", extra={
                "operation": "encrypt_token",
                "token_length": len(token),
                "encrypted_length": len(encrypted_token)
            })
            
            return encrypted_token
            
        except Exception as e:
            logger.error(f"Token encryption failed: {e}", extra={
                "operation": "encrypt_token",
                "error_type": type(e).__name__
            })
            raise ValueError(f"Token encryption failed: {e}")
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an encrypted token
        
        Args:
            encrypted_token: Base64-encoded encrypted token
            
        Returns:
            Plain text token
            
        Raises:
            ValueError: If token is invalid or decryption fails
        """
        if not encrypted_token or not encrypted_token.strip():
            raise ValueError("Encrypted token cannot be empty")
        
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_token.encode('utf-8'))
            token = decrypted_bytes.decode('utf-8')
            
            logger.debug("Token decrypted successfully", extra={
                "operation": "decrypt_token",
                "encrypted_length": len(encrypted_token),
                "token_length": len(token)
            })
            
            return token
            
        except InvalidToken:
            logger.error("Invalid encrypted token provided", extra={
                "operation": "decrypt_token",
                "error_type": "InvalidToken"
            })
            raise ValueError("Invalid encrypted token - token may be corrupted or key may be wrong")
        
        except Exception as e:
            logger.error(f"Token decryption failed: {e}", extra={
                "operation": "decrypt_token",
                "error_type": type(e).__name__
            })
            raise ValueError(f"Token decryption failed: {e}")
    
    def is_token_encrypted(self, token: str) -> bool:
        """
        Check if a token appears to be encrypted
        
        Args:
            token: Token string to check
            
        Returns:
            True if token appears encrypted, False otherwise
        """
        if not token:
            return False
        
        try:
            # Try to decrypt - if it works, it's encrypted
            self.decrypt_token(token)
            return True
        except ValueError:
            # If decryption fails, it's likely not encrypted
            return False
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a new Fernet encryption key
        
        Returns:
            Base64-encoded encryption key suitable for environment variable
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')


def get_token_encryption() -> TokenEncryption:
    """
    Get configured token encryption instance
    
    Returns:
        Configured TokenEncryption instance
        
    Raises:
        ValueError: If encryption key is not configured
    """
    return TokenEncryption()


# For development/testing - generate a key if none exists
def ensure_encryption_key_exists():
    """
    Ensure encryption key exists for development
    This should NOT be used in production
    """
    if not os.getenv("GDRIVE_ENCRYPTION_KEY"):
        logger.warning(
            "No GDRIVE_ENCRYPTION_KEY found - generating temporary key for development. "
            "This should NOT happen in production!"
        )
        key = TokenEncryption.generate_encryption_key()
        os.environ["GDRIVE_ENCRYPTION_KEY"] = key
        logger.info(f"Generated temporary encryption key: {key}")
        return key
    return None


if __name__ == "__main__":
    # CLI utility for key generation
    print("Generating new Fernet encryption key for Google Drive tokens:")
    key = TokenEncryption.generate_encryption_key()
    print(f"GDRIVE_ENCRYPTION_KEY={key}")
    print("\nAdd this to your .env file for secure token storage.")