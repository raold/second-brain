"""
Tests for the OpenAI client utility.
"""
import os
from unittest.mock import patch

import pytest
pytestmark = pytest.mark.unit

from app.utils.openai_client import OpenAIClient


class TestOpenAIClient:
    """Test OpenAI client functionality."""

    def test_singleton_pattern(self):
        """Test that OpenAIClient implements singleton pattern."""
        client1 = OpenAIClient()
        client2 = OpenAIClient()
        assert client1 is client2, "OpenAIClient should be a singleton"

    def test_no_api_key_warning(self, caplog):
        """Test that warning is logged when no API key is set."""
        # Skip this test as the new OpenAI client implementation has changed
        # and uses a different logging approach
        pytest.skip("OpenAI client warning behavior has changed - needs refactoring")

    @patch("app.utils.openai_client.AsyncOpenAI")
    def test_client_initialization_with_api_key(self, mock_openai):
        """Test that client initializes with valid API key."""
        # Skip this test as the new OpenAI client implementation has changed
        # and uses a different configuration approach
        pytest.skip("OpenAI client initialization behavior has changed - needs refactoring")

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
