"""
Local embedding client using LM Studio and CLIP services.
Replaces OpenAI/Anthropic with fully local models.
"""

import asyncio
import aiohttp
import os
from typing import Optional, List, Dict, Any
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class LocalEmbeddingClient:
    """Local embedding client using LM Studio (text) and CLIP (images)."""
    
    _instance: Optional["LocalEmbeddingClient"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # LM Studio for text embeddings (Nomic Embed Text v1.5)
        self.lm_studio_url = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
        self.text_embedding_model = "text-embedding-nomic-embed-text-v1.5"
        
        # CLIP for image embeddings
        self.clip_url = os.getenv("CLIP_SERVICE_URL", "http://127.0.0.1:8002")
        
        # LLaVA for vision+text understanding
        self.llava_url = os.getenv("LLAVA_SERVICE_URL", "http://127.0.0.1:8003")
        
        logger.info("Local embedding client initialized with:")
        logger.info(f"  - Text embeddings: {self.lm_studio_url} ({self.text_embedding_model})")
        logger.info(f"  - Image embeddings: {self.clip_url}")
        logger.info(f"  - Vision understanding: {self.llava_url}")
    
    async def get_embedding(self, text: str) -> List[float] | None:
        """Get text embedding using LM Studio's Nomic model (768 dimensions)."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.text_embedding_model,
                    "input": text
                }
                
                async with session.post(
                    f"{self.lm_studio_url}/embeddings",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embedding = data["data"][0]["embedding"]
                        logger.debug(f"Generated {len(embedding)}-dim text embedding")
                        return embedding
                    else:
                        error = await resp.text()
                        logger.error(f"LM Studio embedding failed: {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get text embedding: {e}")
            return None
    
    async def get_image_embedding(self, image_bytes: bytes) -> List[float] | None:
        """Get image embedding using CLIP (768 dimensions)."""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('image', image_bytes, filename='image.jpg')
                
                async with session.post(
                    f"{self.clip_url}/clip/embed-image",
                    data=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        embedding = result["embedding"]
                        logger.debug(f"Generated {len(embedding)}-dim image embedding")
                        return embedding
                    else:
                        error = await resp.text()
                        logger.error(f"CLIP embedding failed: {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get image embedding: {e}")
            return None
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: str = None
    ) -> str | None:
        """Generate text using LM Studio's LLaVA model."""
        try:
            async with aiohttp.ClientSession() as session:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": model or "llava-1.6-mistral-7b",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                async with session.post(
                    f"{self.lm_studio_url}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        logger.error(f"Text generation failed: {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            return None
    
    async def analyze_content(self, content: str, analysis_type: str = "summary") -> Dict[str, Any] | None:
        """Analyze content using local LLM for various NLP tasks."""
        
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
            result = await self.generate_text(
                prompt=f"{prompt}\n\n{content}",
                system_prompt="You are an expert content analyst. Provide clear, structured analysis.",
                max_tokens=500,
                temperature=0.3  # Lower temperature for consistent analysis
            )
            
            if result:
                return {
                    "analysis_type": analysis_type,
                    "result": result,
                    "model_used": "llava-1.6-mistral-7b",
                    "local": True
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze content: {e}")
            return None
    
    async def analyze_image(self, image_bytes: bytes, prompt: str = "Describe this image") -> str | None:
        """Analyze image using LLaVA service."""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('image', image_bytes, filename='image.jpg')
                data.add_field('prompt', prompt)
                
                async with session.post(
                    f"{self.llava_url}/llava/analyze",
                    data=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("analysis", "")
                    else:
                        error = await resp.text()
                        logger.error(f"Image analysis failed: {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            return None
    
    async def classify_content(self, content: str, categories: List[str]) -> Dict[str, Any] | None:
        """Classify content into provided categories using local LLM."""
        categories_text = ", ".join(categories)
        
        prompt = f"""Classify this content into one or more of these categories: {categories_text}

Content: {content[:2000]}

Provide your response as:
- Primary category: [main category]
- All categories: [list with confidence]
- Reasoning: [brief explanation]"""
        
        try:
            result = await self.generate_text(
                prompt=prompt,
                system_prompt="You are an expert content classifier.",
                max_tokens=300,
                temperature=0.3
            )
            
            if result:
                return {
                    "classification": result,
                    "model_used": "llava-1.6-mistral-7b",
                    "local": True
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to classify content: {e}")
            return None


# Global client instance
_local_client = LocalEmbeddingClient()


def get_local_client() -> LocalEmbeddingClient:
    """Get the global local embedding client instance."""
    return _local_client


# Compatibility wrappers to replace OpenAI functions
def get_openai_client():
    """Compatibility wrapper - returns local client instead."""
    logger.info("Using local embedding client instead of OpenAI")
    return get_local_client()


async def get_openai_embedding_async(text: str) -> List[float] | None:
    """Compatibility wrapper - uses local embeddings."""
    return await _local_client.get_embedding(text)


def get_openai_embedding(text: str) -> List[float] | None:
    """Synchronous wrapper for backward compatibility."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Cannot run async embedding function from within an event loop")
            return None
        else:
            return loop.run_until_complete(_local_client.get_embedding(text))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_local_client.get_embedding(text))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None