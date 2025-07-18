"""
Configuration management for Second Brain application.
Handles environment variables and application settings.
"""

import os
from typing import Optional


class Config:
    """Configuration class that handles environment variables."""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://brain:brain_password@localhost:5432/brain")
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "brain")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "brain_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "brain")
    
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
    USE_MOCK_DATABASE: bool = os.getenv("USE_MOCK_DATABASE", "false").lower() == "true"
    
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
