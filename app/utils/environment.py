"""
Environment configuration validation and testing utilities.
"""

import os
from typing import Any

from app.config import Config


def validate_test_environment() -> dict[str, Any]:
    """Validate and setup test environment configuration."""
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
        os.environ["API_TOKENS"] = "test-token-32-chars-long-for-auth-1234567890abcdef,test-token-32-chars-long-for-auth-0987654321fedcba"

    # Use real OpenAI key if available (from GitHub secrets), otherwise use mock
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = "test-key-mock"

    # Validate configuration
    issues = Config.validate_configuration()

    return {
        "environment": Config.ENVIRONMENT,
        "use_mock_database": Config.should_use_mock_database(),
        "require_openai": Config.should_require_openai(),
        "debug_mode": Config.is_debug_mode(),
        "log_level": Config.get_effective_log_level(),
        "validation_issues": issues,
        "api_tokens": Config.get_api_tokens(),
    }


def validate_ci_environment() -> dict[str, Any]:
    """Validate and setup CI environment configuration."""
    # Set CI environment
    os.environ["ENVIRONMENT"] = "ci"
        os.environ["DEBUG"] = "false"
    os.environ["LOG_LEVEL"] = "WARNING"

    # Validate configuration
    issues = Config.validate_configuration()

    return {
        "environment": Config.ENVIRONMENT,
        "use_mock_database": Config.should_use_mock_database(),
        "require_openai": Config.should_require_openai(),
        "debug_mode": Config.is_debug_mode(),
        "log_level": Config.get_effective_log_level(),
        "validation_issues": issues,
    }


def validate_production_environment() -> dict[str, Any]:
    """Validate production environment configuration."""
    # Validate production configuration without changing environment
    current_env = Config.ENVIRONMENT
    if current_env != "production":
        # Temporarily set to production for validation
        os.environ["ENVIRONMENT"] = "production"

    try:
        issues = Config.validate_configuration()

        return {
            "environment": "production",
            "use_mock_database": Config.should_use_mock_database(),
            "require_openai": Config.should_require_openai(),
            "debug_mode": Config.is_debug_mode(),
            "log_level": Config.get_effective_log_level(),
            "validation_issues": issues,
            "api_tokens_configured": len(Config.get_api_tokens()) > 0,
            "openai_key_configured": bool(Config.OPENAI_API_KEY),
            "database_url_configured": bool(Config.DATABASE_URL),
        }
    finally:
        # Restore original environment
        if current_env != "production":
            os.environ["ENVIRONMENT"] = current_env


def get_environment_summary() -> dict[str, Any]:
    """Get a summary of the current environment configuration."""
    env_config = Config.get_environment_config()

    return {
        "current_environment": Config.ENVIRONMENT,
        "environment_config": {
            "name": env_config.name,
            "use_mock_database": env_config.use_mock_database,
            "require_openai": env_config.require_openai,
            "debug_mode": env_config.debug_mode,
            "log_level": env_config.log_level,
        },
        "effective_settings": {
            "use_mock_database": Config.should_use_mock_database(),
            "require_openai": Config.should_require_openai(),
            "debug_mode": Config.is_debug_mode(),
            "log_level": Config.get_effective_log_level(),
        },
        "configuration_status": {
            "openai_configured": bool(Config.OPENAI_API_KEY),
            "api_tokens_count": len(Config.get_api_tokens()),
            "database_url_configured": bool(Config.DATABASE_URL),
            "validation_issues": Config.validate_configuration(),
        },
    }
