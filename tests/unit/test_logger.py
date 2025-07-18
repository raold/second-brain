"""
Tests for the logger utility.
"""

import logging
import pytest

from app.utils.logger import logger


class TestLogger:
    """Test logger configuration and functionality."""

    def test_logger_exists(self):
        """Test that logger is created and configured."""
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "second-brain"

    def test_logger_level(self):
        """Test that logger has correct level."""
        # The root logger should be configured with INFO level
        root_logger = logging.getLogger()
        assert root_logger.level <= logging.INFO

    def test_logger_basic_functionality(self, caplog):
        """Test that logger can log messages."""
        with caplog.at_level(logging.INFO):
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")
        
        # Check that messages were logged
        assert "Test info message" in caplog.text
        assert "Test warning message" in caplog.text  
        assert "Test error message" in caplog.text

    def test_logger_handlers_configured(self):
        """Test that logger has proper handlers."""
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        # Should have at least one StreamHandler
        has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
        assert has_stream_handler
