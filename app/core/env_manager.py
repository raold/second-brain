"""
Robust environment variable management for Second Brain.
Provides centralized configuration with validation and type safety.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import warnings

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class EnvManager:
    """
    Centralized environment variable management with validation.
    
    Features:
    - Type-safe environment variable access
    - Default values with override capability
    - Validation and error reporting
    - Support for .env files (without python-dotenv dependency)
    - Secret masking in logs
    """
    
    # Sensitive keys that should be masked in logs
    SENSITIVE_KEYS = {
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'JWT_SECRET_KEY',
        'DATABASE_URL',
        'POSTGRES_PASSWORD',
        'REDIS_PASSWORD',
        'API_TOKENS',
        'SENTRY_DSN',
        'AWS_SECRET_KEY',
        'AWS_ACCESS_KEY_ID',
    }
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize environment manager.
        
        Args:
            env_file: Optional path to .env file
        """
        self._cache: Dict[str, Any] = {}
        self._loaded = False
        
        # Load .env file if it exists
        if env_file is None:
            env_file = Path.cwd() / '.env'
        
        if env_file.exists():
            self._load_env_file(env_file)
            logger.info(f"Loaded environment from {env_file}")
        
        # Determine environment
        self.environment = self._get_environment()
        logger.info(f"Running in {self.environment.value} mode")
        
        # Validate required variables
        self._validate_required()
    
    def _load_env_file(self, env_file: Path) -> None:
        """Load environment variables from a .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
                            
        except Exception as e:
            logger.warning(f"Could not load .env file: {e}")
    
    def _get_environment(self) -> Environment:
        """Determine current environment."""
        env_str = os.getenv('ENVIRONMENT', 'development').lower()
        
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(f"Unknown environment '{env_str}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def _validate_required(self) -> None:
        """Validate required environment variables based on environment."""
        required = []
        
        # Always require database in production
        if self.environment == Environment.PRODUCTION:
            required.extend(['DATABASE_URL', 'JWT_SECRET_KEY'])
            
            # Check for default/weak values in production
            if self.get('JWT_SECRET_KEY', '').endswith('change-in-production'):
                raise ValueError("JWT_SECRET_KEY must be changed for production")
        
        # Check OpenAI key if not using mocks
        if not self.get_bool('USE_MOCK_OPENAI'):
            if not self.get('OPENAI_API_KEY'):
                logger.warning("OPENAI_API_KEY not set, AI features will be limited")
        
        # Validate required variables
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable with optional default.
        
        Args:
            key: Environment variable name
            default: Default value if not set
            
        Returns:
            Environment variable value or default
        """
        value = os.getenv(key, default)
        
        # Cache for performance
        self._cache[key] = value
        
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default boolean value
            
        Returns:
            Boolean value
        """
        value = self.get(key, str(default))
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default integer value
            
        Returns:
            Integer value
        """
        value = self.get(key, str(default))
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}: {value}, using default {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default float value
            
        Returns:
            Float value
        """
        value = self.get(key, str(default))
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid float value for {key}: {value}, using default {default}")
            return default
    
    def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """
        Get list environment variable (comma-separated or JSON array).
        
        Args:
            key: Environment variable name
            default: Default list value
            
        Returns:
            List of strings
        """
        value = self.get(key)
        if not value:
            return default or []
        
        # Try JSON array first
        if value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Fall back to comma-separated
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get dictionary environment variable (JSON format).
        
        Args:
            key: Environment variable name
            default: Default dictionary value
            
        Returns:
            Dictionary
        """
        value = self.get(key)
        if not value:
            return default or {}
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON value for {key}, using default")
            return default or {}
    
    def get_database_url(self) -> str:
        """
        Get database URL, constructing from parts if necessary.
        
        Returns:
            PostgreSQL connection string
        """
        # First check for complete DATABASE_URL
        db_url = self.get('DATABASE_URL')
        if db_url:
            return db_url
        
        # Construct from parts
        user = self.get('POSTGRES_USER', 'postgres')
        password = self.get('POSTGRES_PASSWORD', 'postgres')
        host = self.get('POSTGRES_HOST', 'localhost')
        port = self.get('POSTGRES_PORT', '5432')
        database = self.get('POSTGRES_DB', 'secondbrain')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION
    
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment == Environment.TEST
    
    def mask_sensitive(self, value: str, key: str) -> str:
        """
        Mask sensitive values for logging.
        
        Args:
            value: Value to potentially mask
            key: Environment variable key
            
        Returns:
            Masked value if sensitive, original otherwise
        """
        if key.upper() in self.SENSITIVE_KEYS and value:
            # Show first 4 and last 4 characters
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return "***"
        return value
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for logging (with sensitive values masked).
        
        Returns:
            Dictionary of configuration values
        """
        summary = {
            'environment': self.environment.value,
            'database_configured': bool(self.get('DATABASE_URL') or self.get('POSTGRES_DB')),
            'openai_configured': bool(self.get('OPENAI_API_KEY')),
            'redis_configured': bool(self.get('REDIS_URL')),
            'debug_mode': self.get_bool('DEBUG'),
            'host': self.get('HOST', '127.0.0.1'),
            'port': self.get_int('PORT', 8000),
            'log_level': self.get('LOG_LEVEL', 'INFO'),
            'features': {
                'mock_database': self.get_bool('USE_MOCK_DATABASE'),
                'mock_openai': self.get_bool('USE_MOCK_OPENAI'),
                'sessions': self.get_bool('FEATURE_SESSIONS_ENABLED', True),
                'attachments': self.get_bool('FEATURE_ATTACHMENTS_ENABLED', True),
            }
        }
        
        return summary
    
    def validate_production_ready(self) -> List[str]:
        """
        Validate if configuration is production-ready.
        
        Returns:
            List of issues (empty if production-ready)
        """
        issues = []
        
        # Check for weak/default values
        if 'changeme' in self.get('DATABASE_URL', ''):
            issues.append("DATABASE_URL contains default password")
        
        if self.get('JWT_SECRET_KEY', '').endswith('change-in-production'):
            issues.append("JWT_SECRET_KEY is using default value")
        
        if self.get_bool('DEBUG'):
            issues.append("DEBUG mode is enabled")
        
        if self.get('HOST') == '0.0.0.0':
            issues.append("HOST is set to 0.0.0.0 (security risk)")
        
        if not self.get('OPENAI_API_KEY') and not self.get_bool('USE_MOCK_OPENAI'):
            issues.append("No OpenAI API key configured")
        
        if self.get_bool('USE_MOCK_DATABASE'):
            issues.append("Mock database is enabled")
        
        return issues


# Global instance
_env_manager: Optional[EnvManager] = None


def get_env_manager() -> EnvManager:
    """
    Get global environment manager instance.
    
    Returns:
        EnvManager instance
    """
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvManager()
    return _env_manager


# Convenience functions
def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable."""
    return get_env_manager().get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    return get_env_manager().get_bool(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    return get_env_manager().get_int(key, default)


def is_production() -> bool:
    """Check if running in production."""
    return get_env_manager().is_production()


def is_development() -> bool:
    """Check if running in development."""
    return get_env_manager().is_development()