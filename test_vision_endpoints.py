#!/usr/bin/env python3
"""
Test LM Studio vision-specific endpoints
"""
import asyncio
import base64
import io

import aiohttp
from PIL import Image, ImageDraw


async def test_vision_endpoints():
    base_url = "http://127.0.0.1:1234"

    print("=" * 60)
    print("TESTING VISION ENDPOINTS")
    print("=" * 60)

    # Create test image
    img = Image.new('RGB', (512, 512), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 200, 200], fill='red', outline='black', width=3)
    draw.ellipse([250, 50, 400, 200], fill='blue', outline='black', width=3)
    draw.text((100, 300), "TEST IMAGE", fill='black')

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    async with aiohttp.ClientSession() as session:
        # Test 1: /vision/completions endpoint
        print("\n1. Testing /vision/completions endpoint...")
        payload = {
            "model": "llava-1.6",
            "prompt": "Describe this image",
            "image": img_base64
        }

        try:
            async with session.post(
                f"{base_url}/vision/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"   Status: {resp.status}")
                result = await resp.text()
                print(f"   Response: {result[:200]}")
        except Exception as e:
            print(f"   Failed: {e}")

        # Test 2: /v1/vision endpoint
        print("\n2. Testing /v1/vision endpoint...")
        payload = {
            "model": "llava-1.6",
            "messages": [{
                "role": "user",
                "content": "What do you see in this image?",
                "images": [img_base64]
            }]
        }

        try:
            async with session.post(
                f"{base_url}/v1/vision",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"   Status: {resp.status}")
                result = await resp.text()
                print(f"   Response: {result[:200]}")
        except Exception as e:
            print(f"   Failed: {e}")

        # Test 3: Alternative format
        print("\n3. Testing alternative image format...")
        payload = {
            "model": "llava-1.6",
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
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"   Status: {resp.status}")
                result = await resp.text()
                print(f"   Response: {result[:200]}")
        except Exception as e:
            print(f"   Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_vision_endpoints())
