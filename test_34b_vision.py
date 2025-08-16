#!/usr/bin/env python3
"""
Test LLaVA 34B vision capabilities
"""
import asyncio
import base64
import io
import json

import aiohttp
from PIL import Image, ImageDraw


async def test_34b():
    base_url = "http://127.0.0.1:1234/v1"

    print("=" * 60)
    print("TESTING LLAVA 34B MODEL")
    print("=" * 60)

    # Create test image with clear visual elements
    img = Image.new('RGB', (512, 512), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 200, 200], fill='red', outline='black', width=3)
    draw.ellipse([250, 50, 400, 200], fill='blue', outline='black', width=3)
    draw.text((100, 300), "TEST IMAGE", fill='black')
    draw.text((100, 350), "Red Square + Blue Circle", fill='green')

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    async with aiohttp.ClientSession() as session:
        # Test 1: Text generation first (sanity check)
        print("\n1. Testing text generation with 34B model...")
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer with just the number."}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data["choices"][0]["message"]["content"]
                    print(f"   SUCCESS: {response}")
                else:
                    print(f"   ERROR: {await resp.text()}")
        except Exception as e:
            print(f"   FAILED: {e}")

        # Test 2: OpenAI Vision format
        print("\n2. Testing vision with OpenAI format...")
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What shapes and colors do you see in this image?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 200,
            "temperature": 0.5
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "choices" in data:
                        response = data["choices"][0]["message"]["content"]
                        print(f"   SUCCESS: {response[:300]}")
                    else:
                        print(f"   Response: {json.dumps(data, indent=2)[:300]}")
                else:
                    error = await resp.text()
                    print(f"   ERROR ({resp.status}): {error[:200]}")
        except Exception as e:
            print(f"   FAILED: {e}")

        # Test 3: Try alternative format
        print("\n3. Testing with image in message content...")
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "user",
                    "content": "Describe this image",
                    "image": f"data:image/png;base64,{img_base64}"
                }
            ],
            "max_tokens": 200
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "choices" in data:
                        response = data["choices"][0]["message"]["content"]
                        print(f"   Response: {response[:300]}")
                    else:
                        print(f"   Data: {json.dumps(data, indent=2)[:300]}")
                else:
                    error = await resp.text()
                    print(f"   ERROR: {error[:200]}")
        except Exception as e:
            print(f"   FAILED: {e}")

        # Test 4: Check what the model thinks about images
        print("\n4. Asking model about image support...")
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {"role": "user", "content": "Can you process and analyze images? What formats do you accept?"}
            ],
            "max_tokens": 100
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data["choices"][0]["message"]["content"]
                    print(f"   Model says: {response}")
                else:
                    print(f"   ERROR: {await resp.text()}")
        except Exception as e:
            print(f"   FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_34b())
