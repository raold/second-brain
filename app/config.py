"""
Configuration management for Second Brain application.
Uses the centralized environment manager for consistent configuration.
"""

from app.core.env_manager import get_env_manager, Environment

# Get environment manager instance
env = get_env_manager()


class Config:
    """
    Application configuration using environment manager.
    All environment variables are accessed through the centralized manager.
    """
    
    # Environment
    ENVIRONMENT: Environment = env.environment
    IS_PRODUCTION: bool = env.is_production()
    IS_DEVELOPMENT: bool = env.is_development()
    IS_TEST: bool = env.is_test()
    
    # Database Configuration
    DATABASE_URL: str = env.get_database_url()
    
    # PostgreSQL Configuration (individual components)
    POSTGRES_USER: str = env.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = env.get("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = env.get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = env.get("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = env.get("POSTGRES_DB", "secondbrain")
    
    # Redis Configuration
    REDIS_URL: str = env.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = env.get_int("REDIS_MAX_CONNECTIONS", 50)
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = env.get("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = env.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_CHAT_MODEL: str = env.get("OPENAI_CHAT_MODEL", "gpt-4")
    
    # Anthropic Configuration (Optional)
    ANTHROPIC_API_KEY: str = env.get("ANTHROPIC_API_KEY", "")
    
    # Container Security (Single User)
    CONTAINER_API_KEY: str = env.get("CONTAINER_API_KEY", "")
    # JWT removed - not needed for single user containers
    
    # API Configuration
    API_TOKENS: list = env.get_list("API_TOKENS", [])
    
    # Application Configuration
    HOST: str = env.get("HOST", "127.0.0.1")
    PORT: int = env.get_int("PORT", 8000)
    DEBUG: bool = env.get_bool("DEBUG", False)
    LOG_LEVEL: str = env.get("LOG_LEVEL", "INFO")
    
    # CORS Configuration
    CORS_ORIGINS: list = env.get_list("CORS_ORIGINS", ["http://localhost:3000", "http://localhost:8000"])
    
    # Feature Flags
    USE_MOCK_DATABASE: bool = env.get_bool("USE_MOCK_DATABASE", False)
    USE_MOCK_OPENAI: bool = env.get_bool("USE_MOCK_OPENAI", False)
    FEATURE_SESSIONS_ENABLED: bool = env.get_bool("FEATURE_SESSIONS_ENABLED", True)
    FEATURE_ATTACHMENTS_ENABLED: bool = env.get_bool("FEATURE_ATTACHMENTS_ENABLED", True)
    ENABLE_TELEMETRY: bool = env.get_bool("ENABLE_TELEMETRY", False)
    ENABLE_ANALYTICS: bool = env.get_bool("ENABLE_ANALYTICS", False)
    
    # AI Model Configuration
    VECTOR_DIMENSION: int = env.get_int("VECTOR_DIMENSION", 1536)
    BATCH_SIZE: int = env.get_int("BATCH_SIZE", 100)
    SIMILARITY_THRESHOLD: float = env.get_float("SIMILARITY_THRESHOLD", 0.7)
    
    # Monitoring Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT: str = env.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    OTEL_SERVICE_NAME: str = env.get("OTEL_SERVICE_NAME", "second-brain")
    SENTRY_DSN: str = env.get("SENTRY_DSN", "")
    
    # Development Configuration
    ENABLE_HOT_RELOAD: bool = env.get_bool("ENABLE_HOT_RELOAD", IS_DEVELOPMENT)
    ENABLE_DEBUG_TOOLBAR: bool = env.get_bool("ENABLE_DEBUG_TOOLBAR", False)
    
    @classmethod
    def validate(cls) -> list:
        """
        Validate configuration for production readiness.
        
        Returns:
            List of validation issues (empty if valid)
        """
        return env.validate_production_ready()
    
    @classmethod
    def get_summary(cls) -> dict:
        """
        Get configuration summary for logging.
        
        Returns:
            Dictionary of configuration values (sensitive values masked)
        """
        return env.get_config_summary()
    
    @classmethod
    def is_ai_enabled(cls) -> bool:
        """Check if AI features are enabled."""
        return bool(cls.OPENAI_API_KEY) or cls.USE_MOCK_OPENAI
    
    @classmethod
    def is_database_configured(cls) -> bool:
        """Check if database is configured."""
        return bool(cls.DATABASE_URL) or cls.USE_MOCK_DATABASE


# Convenience function for backward compatibility
def get_config() -> Config:
    """Get configuration instance."""
    return Config