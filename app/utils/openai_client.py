"""
OpenAI client utility for embeddings.
"""

import asyncio
import os
from typing import Optional

from openai import AsyncOpenAI

from app.config import Config
from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class OpenAIClient:
    """Singleton OpenAI client for embeddings."""

    _instance: Optional["OpenAIClient"] = None
    _client: AsyncOpenAI | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            api_key = Config.OPENAI_API_KEY
            if not api_key:
                env_config = Config.get_environment_config()
                if env_config.require_openai:
                    logger.error("OPENAI_API_KEY is required for this environment but not set")
                    raise ValueError("OPENAI_API_KEY is required but not configured")
                else:
                    logger.warning("OPENAI_API_KEY not set, OpenAI client will not be available")
                    return

            self._client = AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text using OpenAI API."""
        if not self._client:
            logger.error("OpenAI client not initialized - missing API key")
            return None

        try:
            response = await self._client.embeddings.create(
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None


# Global client instance
_openai_client = OpenAIClient()


def get_openai_embedding(text: str) -> list[float] | None:
    """
    Synchronous wrapper for getting embeddings.
    This is a temporary solution for backward compatibility.
    """
    try:
        # Run the async function in a new event loop if needed
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we need to use a different approach
            # For now, return None and log a warning
            logger.warning("Cannot run async embedding function from within an event loop")
            return None
        else:
            return loop.run_until_complete(_openai_client.get_embedding(text))
    except RuntimeError:
        # No event loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_openai_client.get_embedding(text))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None


async def get_openai_embedding_async(text: str) -> list[float] | None:
    """Async version of get_openai_embedding."""
    return await _openai_client.get_embedding(text)
