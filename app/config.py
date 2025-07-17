import logging
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Unified configuration system with smart defaults and environment detection."""
    
    def __init__(self):
        # Auto-detect environment
        self.is_docker = self._detect_docker_environment()
        self.is_ci = os.getenv('CI', '').lower() in ('true', '1')
        self.is_windows = os.name == 'nt'
        
        # Core settings
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level = self._get_log_level()
        
        # API Configuration
        self.api_tokens = self._get_api_tokens()
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', '8000'))
        
        # Database Configuration (with smart defaults)
        self.postgres = self._get_postgres_config()
        self.qdrant = self._get_qdrant_config()
        
        # Cache Configuration (simplified)
        self.cache = self._get_cache_config()
        
        # OpenAI Configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.openai = self._get_openai_config()
        
        # Model Version Tracking
        self.model_versions = self._get_model_versions()
        
        # Storage Configuration
        self.storage = self._get_storage_config()

    def _detect_docker_environment(self) -> bool:
        """Auto-detect if running in Docker container."""
        # Check common Docker environment indicators
        docker_indicators = [
            os.path.exists('/.dockerenv'),
            os.getenv('DOCKER_CONTAINER') == 'true',
            'docker' in os.getenv('HOSTNAME', '').lower()
        ]
        return any(docker_indicators)

    def _get_log_level(self) -> str:
        """Get appropriate log level based on environment."""
        if self.is_ci:
            return 'WARNING'  # Reduce noise in CI
        elif self.debug:
            return 'DEBUG'
        else:
            return os.getenv('LOG_LEVEL', 'INFO')

    def _get_api_tokens(self) -> list:
        """Get API tokens with fallback defaults."""
        tokens_str = os.getenv('API_TOKENS', 'dev-token,test-token')
        return [token.strip() for token in tokens_str.split(',') if token.strip()]

    def _get_postgres_config(self) -> Dict[str, Any]:
        """Get PostgreSQL configuration with smart defaults."""
        # Smart hostname detection
        if self.is_docker:
            default_host = 'postgres'
        else:
            default_host = 'localhost'
            
        return {
            'host': os.getenv('POSTGRES_HOST', default_host),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'secondbrain'),
            'username': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'pool_size': int(os.getenv('POSTGRES_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('POSTGRES_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('POSTGRES_POOL_TIMEOUT', '30')),
        }

    def _get_qdrant_config(self) -> Dict[str, Any]:
        """Get Qdrant configuration with smart defaults."""
        if self.is_docker:
            default_host = 'qdrant'
        else:
            default_host = 'localhost'
            
        return {
            'host': os.getenv('QDRANT_HOST', default_host),
            'port': int(os.getenv('QDRANT_PORT', '6333')),
            'timeout': int(os.getenv('QDRANT_TIMEOUT', '30')),
            'collection': os.getenv('QDRANT_COLLECTION', 'second_brain'),
            'vector_size': int(os.getenv('QDRANT_VECTOR_SIZE', '1536')),
            'distance': os.getenv('QDRANT_DISTANCE', 'Cosine'),
        }

    def _get_cache_config(self) -> Dict[str, Any]:
        """Simplified cache configuration."""
        # Single cache size setting that scales others
        base_size = int(os.getenv('CACHE_SIZE', '1000'))
        
        return {
            'enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            'default_ttl': int(os.getenv('CACHE_TTL', '300')),  # 5 minutes default
            'sizes': {
                'embeddings': base_size * 2,     # 2000 default
                'queries': base_size // 2,       # 500 default  
                'memories': base_size * 5,       # 5000 default
                'search': base_size,             # 1000 default
                'analytics': base_size // 10,    # 100 default
            },
            'ttls': {
                'embeddings': 3600,              # 1 hour
                'queries': 300,                  # 5 minutes
                'memories': 1800,                # 30 minutes
                'search': 300,                   # 5 minutes
                'analytics': 900,                # 15 minutes
            }
        }

    def _get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration with smart defaults."""
        return {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
            'retry_attempts': int(os.getenv('OPENAI_RETRY_ATTEMPTS', '3')),
            'retry_multiplier': int(os.getenv('OPENAI_RETRY_MULTIPLIER', '1')),
            'retry_min_wait': int(os.getenv('OPENAI_RETRY_MIN_WAIT', '2')),
            'retry_max_wait': int(os.getenv('OPENAI_RETRY_MAX_WAIT', '10')),
        }

    def _get_model_versions(self) -> Dict[str, str]:
        """Get model version tracking."""
        return {
            "llm": os.getenv("MODEL_VERSION_LLM", "gpt-4o"),
            "embedding": os.getenv("MODEL_VERSION_EMBEDDING", "text-embedding-3-small")
        }

    def _get_storage_config(self) -> Dict[str, Any]:
        """Storage configuration with smart defaults."""
        return {
            'data_dir': Path(os.getenv('DATA_DIR', './app/data')),
            'backup_enabled': os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
            'dual_storage': os.getenv('DUAL_STORAGE', 'true').lower() == 'true',
        }

    def get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        pg = self.postgres
        return f"postgresql+asyncpg://{pg['username']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"

    def get_qdrant_url(self) -> str:
        """Get Qdrant connection URL."""
        qd = self.qdrant
        return f"http://{qd['host']}:{qd['port']}"

    def setup_logging(self) -> None:
        """Setup logging with Windows-compatible settings."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Use simple text format on Windows to avoid emoji encoding issues
        if self.is_windows or self.is_ci:
            log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/app.log') if os.path.exists('logs') else logging.NullHandler()
            ]
        )

    def validate(self) -> None:
        """Validate configuration and warn about issues."""
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY not set - OpenAI features will be disabled")
        
        if not self.api_tokens:
            issues.append("No API tokens configured - authentication will fail")
        
        if self.is_docker and self.postgres['host'] == 'localhost':
            issues.append("Docker environment detected but PostgreSQL host is localhost")
        
        if issues:
            print("⚠️  Configuration Issues:")
            for issue in issues:
                print(f"   - {issue}")

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"""Configuration:
  Environment: {'Docker' if self.is_docker else 'Local'} {'(CI)' if self.is_ci else ''}
  Debug: {self.debug}
  PostgreSQL: {self.postgres['host']}:{self.postgres['port']}
  Qdrant: {self.qdrant['host']}:{self.qdrant['port']}
  Cache: {'Enabled' if self.cache['enabled'] else 'Disabled'}
  Log Level: {self.log_level}"""

    def summary(self) -> dict:
        """Get configuration summary for logging."""
        return {
            "environment": "Docker" if self.is_docker else "Local",
            "debug": self.debug,
            "postgres_host": self.postgres['host'],
            "qdrant_host": self.qdrant['host'],
            "cache_enabled": self.cache['enabled'],
            "log_level": self.log_level,
            "is_windows": self.is_windows,
            "is_ci": self.is_ci
        }

    def override_for_testing(self, **overrides):
        """
        Override configuration values for testing purposes.
        
        Args:
            **overrides: Key-value pairs to override in the configuration
            
        Example:
            config.override_for_testing(
                api_tokens=['test-token'],
                debug=True,
                postgres={'host': 'localhost', 'port': 5432}
            )
        """
        for key, value in overrides.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"Config has no attribute '{key}'")

    def reset_to_defaults(self):
        """Reset configuration to default values (useful for test cleanup)."""
        self.__init__()  # Re-initialize with defaults

# Global configuration instance
config = Config()

# Legacy compatibility - deprecated, use config object instead
OPENAI_API_KEY = config.openai_api_key
API_TOKENS = config.api_tokens
POSTGRES_HOST = config.postgres['host']
POSTGRES_PORT = config.postgres['port']
POSTGRES_DB = config.postgres['database']
POSTGRES_USER = config.postgres['username']
POSTGRES_PASSWORD = config.postgres['password']
QDRANT_HOST = config.qdrant['host']
QDRANT_PORT = config.qdrant['port']
DATA_DIR = str(config.storage['data_dir'])
