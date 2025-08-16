"""
LM Studio Integration for Local LLM Processing
Provides text generation and embeddings without API costs
"""

import asyncio
import aiohttp
import numpy as np
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LMStudioService:
    """Interface to LM Studio's OpenAI-compatible API"""
    
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.api_base = f"{base_url}/v1"
        self.headers = {"Content-Type": "application/json"}
        
    async def check_health(self) -> bool:
        """Check if LM Studio is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/models") as resp:
                    return resp.status == 200
        except:
            return False
    
    async def get_models(self) -> List[str]:
        """Get available models in LM Studio"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/models") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
        return []
    
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> np.ndarray:
        """Generate embedding using LM Studio"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "input": text,
                    "model": model or "nomic-embed-text"  # Or any embedding model you have
                }
                
                async with session.post(
                    f"{self.api_base}/embeddings",
                    json=payload,
                    headers=self.headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embedding = data["data"][0]["embedding"]
                        return np.array(embedding, dtype=np.float32)
                    else:
                        error = await resp.text()
                        logger.error(f"Embedding failed: {error}")
                        raise Exception(f"Embedding generation failed: {error}")
                        
        except Exception as e:
            logger.error(f"LM Studio embedding error: {e}")
            raise
    
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """Generate text using LM Studio"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model or "default",  # Will use currently loaded model
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False
                }
                
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=self.headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await resp.text()
                        logger.error(f"Generation failed: {error}")
                        raise Exception(f"Text generation failed: {error}")
                        
        except Exception as e:
            logger.error(f"LM Studio generation error: {e}")
            raise
    
    async def summarize_document(self, content: str, max_length: int = 500) -> str:
        """Summarize a document using LM Studio"""
        prompt = f"""Please provide a concise summary of the following document in {max_length} words or less:

{content[:4000]}  # Truncate to fit context

Summary:"""
        
        return await self.generate_text(prompt, max_tokens=max_length)
    
    async def extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        prompt = f"""Extract the 10 most important keywords from this text. Return only the keywords as a comma-separated list:

{content[:2000]}

Keywords:"""
        
        response = await self.generate_text(prompt, max_tokens=100, temperature=0.3)
        keywords = [k.strip() for k in response.split(",")]
        return keywords[:10]  # Ensure max 10 keywords
    
    async def answer_question(self, context: str, question: str) -> str:
        """Answer a question based on context"""
        prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say "I don't have enough information to answer that."

Context:
{context[:3000]}

Question: {question}

Answer:"""
        
        return await self.generate_text(prompt, max_tokens=300, temperature=0.5)


# Example usage
async def test_lm_studio():
    """Test LM Studio integration"""
    service = LMStudioService()
    
    # Check if running
    if not await service.check_health():
        print("❌ LM Studio is not running. Please start it first.")
        return
    
    print("✅ LM Studio is running")
    
    # Get available models
    models = await service.get_models()
    print(f"Available models: {models}")
    
    # Test text generation
    response = await service.generate_text(
        "What are the benefits of using local LLMs?",
        max_tokens=200
    )
    print(f"\nGenerated text:\n{response}")
    
    # Test embedding (if you have an embedding model)
    try:
        embedding = await service.generate_embedding("Test embedding generation")
        print(f"\nEmbedding shape: {embedding.shape}")
    except:
        print("Embedding model not available")


if __name__ == "__main__":
    asyncio.run(test_lm_studio())