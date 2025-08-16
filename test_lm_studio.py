#!/usr/bin/env python3
"""
Test LM Studio models - Text generation and embeddings
"""
import asyncio
import aiohttp
import json

async def test_models():
    """Test available LM Studio models"""
    base_url = "http://127.0.0.1:1234/v1"
    
    print("=" * 60)
    print("LM STUDIO MODEL TEST")
    print("=" * 60)
    
    # 1. List models
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/models") as resp:
            data = await resp.json()
            models = data["data"]
            print("\nAvailable models:")
            for model in models:
                print(f"  - {model['id']}")
    
        # 2. Test text generation with GPT-OSS
        print("\n1. Testing GPT-OSS 120B text generation...")
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [
                {"role": "user", "content": "What are the benefits of using local LLMs for document processing?"}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data["choices"][0]["message"]["content"]
                    print(f"Response: {response[:500]}...")
                else:
                    error = await resp.text()
                    print(f"Error: {error}")
        except Exception as e:
            print(f"Failed: {e}")
        
        # 3. Test embeddings with Nomic
        print("\n2. Testing Nomic Embed Text v1.5...")
        payload = {
            "model": "text-embedding-nomic-embed-text-v1.5",
            "input": "Second Brain multimodal document processing system",
        }
        
        try:
            async with session.post(
                f"{base_url}/embeddings",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embedding = data["data"][0]["embedding"]
                    print(f"Embedding generated: {len(embedding)} dimensions")
                    print(f"First 10 values: {embedding[:10]}")
                else:
                    error = await resp.text()
                    print(f"Error: {error}")
        except Exception as e:
            print(f"Failed: {e}")
        
        # 4. Test document summarization
        print("\n3. Testing document summarization...")
        document = """
        The Second Brain system is a comprehensive knowledge management platform that integrates 
        multiple AI services for processing documents. It includes Google Drive integration for 
        file synchronization, CLIP for image embeddings, LLaVA for deep image analysis, and now 
        LM Studio for local text processing. All data is stored in PostgreSQL with vector search 
        capabilities. The system runs entirely locally for privacy and can process thousands of 
        documents without API costs.
        """
        
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes documents concisely."},
                {"role": "user", "content": f"Summarize this in 2 sentences: {document}"}
            ],
            "max_tokens": 100,
            "temperature": 0.5
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    summary = data["choices"][0]["message"]["content"]
                    print(f"Summary: {summary}")
                else:
                    error = await resp.text()
                    print(f"Error: {error}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_models())