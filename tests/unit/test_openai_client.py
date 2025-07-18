"""
Tests for the OpenAI client utility.
"""

import os
from unittest.mock import patch

from app.utils.openai_client import OpenAIClient


class TestOpenAIClient:
    """Test OpenAI client functionality."""

    def test_singleton_pattern(self):
        """Test that OpenAIClient implements singleton pattern."""
        client1 = OpenAIClient()
        client2 = OpenAIClient()
        assert client1 is client2, "OpenAIClient should be a singleton"

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key_warning(self, caplog):
        """Test that warning is logged when no API key is set."""
        # Clear any existing instance
        OpenAIClient._instance = None
        OpenAIClient._client = None

        with caplog.at_level("WARNING"):
            client = OpenAIClient()

        assert "OPENAI_API_KEY not set" in caplog.text
        assert client._client is None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("app.utils.openai_client.AsyncOpenAI")
    def test_client_initialization_with_api_key(self, mock_openai):
        """Test that client initializes with valid API key."""
        # Clear any existing instance
        OpenAIClient._instance = None
        OpenAIClient._client = None

        client = OpenAIClient()

        mock_openai.assert_called_once_with(api_key="test-key")

    def test_client_attributes_exist(self):
        """Test that expected attributes exist on client."""
        client = OpenAIClient()
        assert hasattr(client, "_instance")
        assert hasattr(client, "_client")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_client_reinitialization(self):
        """Test that client doesn't reinitialize if already created."""
        # Clear any existing instance
        OpenAIClient._instance = None
        OpenAIClient._client = None

        client1 = OpenAIClient()
        original_client = client1._client

        client2 = OpenAIClient()

        # Should be the same client instance
        assert client2._client is original_client
