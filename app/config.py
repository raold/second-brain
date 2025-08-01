import os
from dataclasses import dataclass

"""
Configuration management for Second Brain application.
Handles environment variables and application settings.
"""



@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""

    name: str
    use_mock_database: bool
    require_openai: bool
    debug_mode: bool
    log_level: str


class Config:
    """Configuration class that handles environment variables."""

    # Environment Detection
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # PostgreSQL Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4")

    # API Configuration
    API_TOKENS: str = os.getenv("API_TOKENS", "")

    # Application Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Test Configuration

    # Environment Configurations
    ENVIRONMENTS = {
        "development": EnvironmentConfig(
            name="development",
            use_mock_database=False,
            require_openai=False,
            debug_mode=True,
            log_level="DEBUG",
        ),
        "testing": EnvironmentConfig(
            name="testing",
            use_mock_database=True,
            require_openai=False,
            debug_mode=True,
            log_level="INFO",
        ),
        "ci": EnvironmentConfig(
            name="ci",
            use_mock_database=True,
            require_openai=False,
            debug_mode=False,
            log_level="WARNING",
        ),
        "production": EnvironmentConfig(
            name="production",
            use_mock_database=False,
            require_openai=True,
            debug_mode=False,
            log_level="WARNING",
        ),
    }

    @classmethod
    def get_environment_config(cls) -> EnvironmentConfig:
        """Get the current environment configuration."""
        return cls.ENVIRONMENTS.get(cls.ENVIRONMENT, cls.ENVIRONMENTS["development"])

    @classmethod
    def should_use_mock_database(cls) -> bool:
        """Determine if mock database should be used."""
        # Mock database removed - always use real database
        return False

    @classmethod
    def should_require_openai(cls) -> bool:
        """Determine if OpenAI API key is required."""
        env_config = cls.get_environment_config()
        return env_config.require_openai

    @classmethod
    def get_database_url(cls) -> str:
        """Get the complete database URL."""
        if cls.DATABASE_URL:
            return cls.DATABASE_URL
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    @classmethod
    def get_api_tokens(cls) -> list[str]:
        """Get list of valid API tokens."""
        if not cls.API_TOKENS:
            return []
        return [token.strip() for token in cls.API_TOKENS.split(",") if token.strip()]

    @classmethod
    def validate_configuration(cls) -> list[str]:
        """Validate current configuration and return list of issues."""
        issues = []
        env_config = cls.get_environment_config()

        # Check OpenAI configuration if required
        if env_config.require_openai and not cls.OPENAI_API_KEY:
            issues.append(f"OPENAI_API_KEY is required for {cls.ENVIRONMENT} environment")

        # Check API tokens for non-development environments
        if cls.ENVIRONMENT != "development" and not cls.get_api_tokens():
            issues.append(f"API_TOKENS must be configured for {cls.ENVIRONMENT} environment")

        # Validate database configuration for non-mock environments
        if not cls.should_use_mock_database():
            if not cls.DATABASE_URL and (
                not cls.POSTGRES_USER or not cls.POSTGRES_PASSWORD or not cls.POSTGRES_DB
            ):
                issues.append(
                    "Database configuration required: Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB"
                )
            if cls.POSTGRES_PASSWORD == "brain_password":
                issues.append("Default PostgreSQL password detected - please set a secure password")

        return issues

    @classmethod
    def get_effective_log_level(cls) -> str:
        """Get the effective log level based on environment and explicit setting."""
        env_config = cls.get_environment_config()
        # Explicit LOG_LEVEL takes precedence
        if os.getenv("LOG_LEVEL"):
            return cls.LOG_LEVEL
        return env_config.log_level

    @classmethod
    def is_debug_mode(cls) -> bool:
        """Determine if debug mode should be enabled."""
        env_config = cls.get_environment_config()
        # Explicit DEBUG setting takes precedence
        if os.getenv("DEBUG"):
            return cls.DEBUG
        return env_config.debug_mode


def get_settings() -> Config:
    """Get application settings instance."""
    return Config()
