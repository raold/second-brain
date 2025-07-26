"""
Tests for the config module.
"""

import os
from unittest.mock import patch

from app.config import Config


class TestConfig:
    """Test configuration management."""

    def test_default_config_values(self):
        """Test that default configuration values are set correctly."""
        # Test database defaults - in test environment these are overridden
        assert Config.DATABASE_URL.startswith("postgresql://")
        if os.getenv("ENVIRONMENT") == "test":
            assert Config.POSTGRES_USER == "secondbrain"
            assert Config.POSTGRES_PASSWORD == "changeme"
        else:
            assert Config.POSTGRES_USER == "brain"
            assert Config.POSTGRES_PASSWORD == "brain_password"
        assert Config.POSTGRES_HOST == "localhost"
        assert Config.POSTGRES_PORT == "5432"
        if os.getenv("ENVIRONMENT") == "test":
            assert Config.POSTGRES_DB == "secondbrain"
        else:
            assert Config.POSTGRES_DB == "brain"

        # Test OpenAI defaults
        assert Config.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
        assert Config.OPENAI_CHAT_MODEL == "gpt-4"

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://test:test@testhost:5432/testdb",
                "POSTGRES_USER": "testuser",
                "OPENAI_EMBEDDING_MODEL": "test-embedding-model",
                "API_TOKENS": "test-token-1,test-token-2",
            },
        ):
            # Import again to pick up the environment variables
            from importlib import reload

            from app import config

            reload(config)

            # Test that environment variables are used
            assert "testhost" in config.Config.DATABASE_URL
            assert config.Config.POSTGRES_USER == "testuser"
            assert config.Config.OPENAI_EMBEDDING_MODEL == "test-embedding-model"
            assert config.Config.API_TOKENS == "test-token-1,test-token-2"

    def test_config_class_attributes_exist(self):
        """Test that all expected configuration attributes exist."""
        expected_attrs = [
            "DATABASE_URL",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "OPENAI_API_KEY",
            "OPENAI_EMBEDDING_MODEL",
            "OPENAI_CHAT_MODEL",
            "API_TOKENS",
        ]

        for attr in expected_attrs:
            assert hasattr(Config, attr), f"Config should have attribute {attr}"

    def test_config_attributes_are_strings(self):
        """Test that all config attributes are strings."""
        string_attrs = [
            "DATABASE_URL",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "OPENAI_API_KEY",
            "OPENAI_EMBEDDING_MODEL",
            "OPENAI_CHAT_MODEL",
            "API_TOKENS",
        ]

        for attr in string_attrs:
            value = getattr(Config, attr)
            assert isinstance(value, str), f"Config.{attr} should be a string, got {type(value)}"
