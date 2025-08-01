import asyncio
import os
from typing import Optional

from app.utils.logging_config import get_logger

"""
OpenAI client utility for embeddings.
"""


from openai import AsyncOpenAI

from app.config import Config

logger = get_logger(__name__)


class OpenAIClient:
    """Singleton OpenAI client for embeddings and NLP features."""

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

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str | None:
        """Generate text using OpenAI API."""
        if not self._client:
            logger.error("OpenAI client not initialized - missing API key")
            return None

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            return None

    async def analyze_content(self, content: str, analysis_type: str = "summary") -> dict | None:
        """Analyze content using OpenAI API for various NLP tasks."""
        if not self._client:
            logger.error("OpenAI client not initialized - missing API key")
            return None

        analysis_prompts = {
            "summary": "Summarize the following content in 2-3 sentences:",
            "keywords": "Extract the top 10 keywords from this content:",
            "entities": "Extract named entities (people, places, organizations, dates) from this content:",
            "sentiment": "Analyze the sentiment of this content (positive, negative, neutral) and explain why:",
            "topics": "Identify the main topics discussed in this content:",
            "structure": "Analyze the structure of this content and identify key sections:",
        }

        prompt = analysis_prompts.get(analysis_type, analysis_prompts["summary"])

        try:
            response = await self._client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content analyst. Provide clear, structured analysis.",
                    },
                    {"role": "user", "content": f"{prompt}\n\n{content}"},
                ],
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more consistent analysis
            )

            result = response.choices[0].message.content

            # Structure the response
            return {
                "analysis_type": analysis_type,
                "result": result,
                "model_used": response.model,
                "tokens_used": response.usage.total_tokens if hasattr(response, "usage") else None,
            }

        except Exception as e:
            logger.error(f"Failed to analyze content: {e}")
            return None

    async def enhance_topics(self, topics: list[dict]) -> list[dict] | None:
        """Enhance extracted topics with better names and descriptions."""
        if not self._client:
            logger.error("OpenAI client not initialized - missing API key")
            return None

        try:
            topics_text = "\n".join(
                [
                    f"- {t.get('name', 'Unknown')}: {', '.join(t.get('keywords', [])[:5])}"
                    for t in topics
                ]
            )

            response = await self._client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing and naming topics. Provide clear, descriptive names and brief explanations.",
                    },
                    {
                        "role": "user",
                        "content": f"Improve the names and add brief descriptions for these topics:\n{topics_text}\n\nReturn as JSON array with 'name', 'description', and 'keywords' for each topic.",
                    },
                ],
                max_tokens=800,
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Merge enhanced data back into topics
            enhanced_topics = topics.copy()
            if "topics" in result:
                for i, enhanced in enumerate(result["topics"]):
                    if i < len(enhanced_topics):
                        enhanced_topics[i].update(enhanced)

            return enhanced_topics

        except Exception as e:
            logger.error(f"Failed to enhance topics: {e}")
            return topics  # Return original topics on failure

    async def classify_content(self, content: str, categories: list[str]) -> dict | None:
        """Classify content into provided categories."""
        if not self._client:
            logger.error("OpenAI client not initialized - missing API key")
            return None

        try:
            categories_text = ", ".join(categories)

            response = await self._client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content classifier. Classify content accurately and provide confidence scores.",
                    },
                    {
                        "role": "user",
                        "content": f"Classify this content into one or more of these categories: {categories_text}\n\nContent: {content[:2000]}\n\nReturn as JSON with 'primary_category', 'all_categories' (with confidence scores), and 'reasoning'.",
                    },
                ],
                max_tokens=300,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Failed to classify content: {e}")
            return None


# Global client instance
_openai_client = OpenAIClient()


def get_openai_client() -> OpenAIClient:
    """Get the global OpenAI client instance."""
    return _openai_client


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
