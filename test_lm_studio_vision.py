#!/usr/bin/env python3
"""
Debug LM Studio vision/multimodal capabilities
Test different approaches to send images to JoyCaption
"""
import asyncio
import aiohttp
import json
import base64
from PIL import Image, ImageDraw
import io

async def test_vision_approaches():
    """Test different ways to send images to LM Studio"""
    base_url = "http://127.0.0.1:1234/v1"
    
    print("=" * 60)
    print("LM STUDIO VISION CAPABILITY TEST")
    print("=" * 60)
    
    # Create a test image with clear visual elements
    img = Image.new('RGB', (512, 512), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 200, 200], fill='red', outline='black', width=3)
    draw.ellipse([250, 50, 400, 200], fill='blue', outline='black', width=3)
    draw.text((100, 300), "TEST IMAGE", fill='black')
    draw.text((100, 350), "Red Rectangle + Blue Circle", fill='green')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    async with aiohttp.ClientSession() as session:
        # Check what the model thinks it can do
        print("\n1. Checking model capabilities...")
        async with session.get(f"{base_url}/models") as resp:
            data = await resp.json()
            print("Available models:")
            for model in data["data"]:
                print(f"  - {model['id']}")
        
        # Test 1: OpenAI Vision API format (most standard)
        print("\n2. Testing OpenAI Vision API format...")
        payload = {
            "model": "llama-joycaption-beta-one-hf-llava",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What do you see in this image? Describe the shapes and colors."
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
            "temperature": 0.7
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    print(f"  Error: {result['error']}")
                else:
                    content = result["choices"][0]["message"]["content"]
                    print(f"  Response: {content[:300]}...")
        except Exception as e:
            print(f"  Failed: {e}")
        
        # Test 2: Try with image first, then text (some models prefer this)
        print("\n3. Testing with image-first format...")
        payload = {
            "model": "llama-joycaption-beta-one-hf-llava",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe this image."
                        }
                    ]
                }
            ],
            "max_tokens": 200
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    print(f"  Error: {result['error']}")
                else:
                    content = result["choices"][0]["message"]["content"]
                    print(f"  Response: {content[:300]}...")
        except Exception as e:
            print(f"  Failed: {e}")
        
        # Test 3: Simple string format (some implementations)
        print("\n4. Testing simple concatenated format...")
        payload = {
            "model": "llama-joycaption-beta-one-hf-llava",
            "messages": [
                {
                    "role": "user",
                    "content": f"[IMAGE]{img_base64}[/IMAGE]\nDescribe this image."
                }
            ],
            "max_tokens": 200
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    print(f"  Error: {result['error']}")
                else:
                    content = result["choices"][0]["message"]["content"]
                    print(f"  Response: {content[:300]}...")
        except Exception as e:
            print(f"  Failed: {e}")
        
        # Test 4: Check if there's a specific vision endpoint
        print("\n5. Checking for vision-specific endpoints...")
        endpoints = [
            "/vision/completions",
            "/v1/vision",
            "/v1/images/generations",
            "/v1/images/edits"
        ]
        
        for endpoint in endpoints:
            try:
                async with session.get(f"http://127.0.0.1:1234{endpoint}") as resp:
                    if resp.status != 404:
                        print(f"  Found endpoint: {endpoint} (status: {resp.status})")
            except:
                pass
        
        # Test 5: Try the model without image to see its behavior
        print("\n6. Testing model's default behavior...")
        payload = {
            "model": "llama-joycaption-beta-one-hf-llava",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an image captioning model. Describe images in detail."
                },
                {
                    "role": "user",
                    "content": "Can you process images? If yes, how should I send them to you?"
                }
            ],
            "max_tokens": 200
        }
        
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                result = await resp.json()
                if "error" not in result:
                    content = result["choices"][0]["message"]["content"]
                    print(f"  Model says: {content}")
        except Exception as e:
            print(f"  Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_vision_approaches())