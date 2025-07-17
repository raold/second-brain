import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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
            'database': os.getenv('POSTGRES_DB', 'second_brain'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'pool_size': int(os.getenv('POSTGRES_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('POSTGRES_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('POSTGRES_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('POSTGRES_POOL_RECYCLE', '3600')),
        }

    def _get_qdrant_config(self) -> Dict[str, Any]:
        """Get Qdrant configuration with smart defaults."""
        # Smart hostname detection
        if self.is_docker:
            default_host = 'qdrant'
        else:
            default_host = 'localhost'
            
        return {
            'host': os.getenv('QDRANT_HOST', default_host),
            'port': int(os.getenv('QDRANT_PORT', '6333')),
            'collection': os.getenv('QDRANT_COLLECTION', 'memories'),
            'timeout': int(os.getenv('QDRANT_TIMEOUT', '30')),
        }

    def _get_cache_config(self) -> Dict[str, Any]:
        """Get caching configuration."""
        return {
            'default_ttl': int(os.getenv('CACHE_DEFAULT_TTL', '300')),  # 5 minutes
            'max_size': int(os.getenv('CACHE_MAX_SIZE', '1000')),
            'enable_metrics': os.getenv('CACHE_ENABLE_METRICS', 'true').lower() == 'true',
        }

    def _get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        return {
            'retry_attempts': int(os.getenv('OPENAI_RETRY_ATTEMPTS', '3')),
            'retry_multiplier': int(os.getenv('OPENAI_RETRY_MULTIPLIER', '1')),
            'retry_min_wait': int(os.getenv('OPENAI_RETRY_MIN_WAIT', '2')),
            'retry_max_wait': int(os.getenv('OPENAI_RETRY_MAX_WAIT', '10')),
        }

    def _get_model_versions(self) -> Dict[str, str]:
        """Get model version configuration."""
        return {
            'llm': os.getenv('MODEL_VERSION_LLM', 'gpt-4o'),
            'embedding': os.getenv('MODEL_VERSION_EMBEDDING', 'text-embedding-3-small')
        }

    def _get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return {
            'markdown_dir': os.getenv('MARKDOWN_DIR', 'data/memories'),
            'backup_enabled': os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
            'backup_interval': int(os.getenv('BACKUP_INTERVAL', '3600')),  # 1 hour
        }

    def get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        pg = self.postgres
        return f"postgresql+asyncpg://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"

    def setup_logging(self):
        """Set up logging configuration with Windows compatibility."""
        import logging
        import sys
        
        # Configure logging based on environment
        log_level = getattr(logging, self.log_level.upper())
        
        # Create formatter
        if self.is_windows or self.is_ci:
            # Plain text format for Windows/CI
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            # More detailed format for Unix systems
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    def summary(self):
        """Return configuration summary."""
        return {
            'environment': {
                'is_docker': self.is_docker,
                'is_ci': self.is_ci,
                'is_windows': self.is_windows,
                'debug': self.debug,
                'log_level': self.log_level,
            },
            'api': {
                'host': self.host,
                'port': self.port,
                'tokens_count': len(self.api_tokens),
            },
            'databases': {
                'postgres': {
                    'host': self.postgres['host'],
                    'port': self.postgres['port'],
                    'database': self.postgres['database'],
                },
                'qdrant': {
                    'host': self.qdrant['host'],
                    'port': self.qdrant['port'],
                    'collection': self.qdrant['collection'],
                },
            },
            'models': self.model_versions,
            'storage': self.storage,
        }
        
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


# Global configuration instance
config = Config()
