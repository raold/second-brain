#!/usr/bin/env python3
"""
Direct test of LM Studio models
"""
import asyncio

import aiohttp


async def test_models():
    base_url = "http://127.0.0.1:1234/v1"

    print("=" * 60)
    print("TESTING LM STUDIO MODELS")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 1. List available models
        print("\n1. Available models:")
        async with session.get(f"{base_url}/models") as resp:
            data = await resp.json()
            for model in data["data"]:
                print(f"   - {model['id']}")

        # 2. Test Nomic embeddings
        print("\n2. Testing Nomic Embed Text v1.5...")
        payload = {
            "model": "text-embedding-nomic-embed-text-v1.5",
            "input": "Second Brain is a local AI knowledge management system"
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
                    print(f"SUCCESS: Embeddings work! Dimensions: {len(embedding)}")
                else:
                    print(f"ERROR: {await resp.text()}")
        except Exception as e:
            print(f"FAILED: {e}")

        # 3. Test Vicuna 13B text generation (without image first)
        print("\n3. Testing LLaVA 1.6 Vicuna 13B text generation...")

        # Try different model name formats
        model_names = ["llava-1.6", "llava-1.6-vicuna-13b", "llava-v1.6-vicuna-13b"]

        for model_name in model_names:
            print(f"\n   Trying model name: {model_name}")
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "What is the capital of France? Answer in one word."}
                ],
                "max_tokens": 50,
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
                        print(f"   SUCCESS - Response: {response}")
                        break
                    else:
                        error = await resp.text()
                        print(f"   ERROR: {error[:100]}")
            except Exception as e:
                print(f"   FAILED: {e}")

        # 4. Check server info
        print("\n4. Checking server info...")
        try:
            async with session.get("http://127.0.0.1:1234/") as resp:
                if resp.status == 200:
                    info = await resp.text()
                    print(f"Server response: {info[:200]}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_models())
