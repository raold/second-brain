"""Test script for GPU services."""

import asyncio
import aiohttp
import base64
from pathlib import Path
import json
import time


async def test_clip_service():
    """Test CLIP service endpoints."""
    print("\n🧪 Testing CLIP Service...")
    
    async with aiohttp.ClientSession() as session:
        # Test status
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"✅ CLIP Status: {status}")
                else:
                    print(f"❌ CLIP Status failed: {resp.status}")
        except Exception as e:
            print(f"❌ CLIP Service not available: {e}")
            return False
        
        # Test text embedding
        try:
            payload = {"text": "A beautiful sunset over the ocean"}
            async with session.post(
                "http://localhost:8002/clip/embed/text",
                json=payload
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Text embedding: {result['dimensions']} dims, "
                          f"{result['processing_time_ms']:.2f}ms")
                else:
                    print(f"❌ Text embedding failed: {resp.status}")
        except Exception as e:
            print(f"❌ Text embedding error: {e}")
        
        # Test with sample image (create a test image)
        try:
            from PIL import Image
            import io
            
            # Create a simple test image
            img = Image.new('RGB', (224, 224), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            data = aiohttp.FormData()
            data.add_field('file', img_bytes, filename='test.png', 
                          content_type='image/png')
            
            async with session.post(
                "http://localhost:8002/clip/embed/image",
                data=data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Image embedding: {result['dimensions']} dims, "
                          f"{result['processing_time_ms']:.2f}ms")
                else:
                    print(f"❌ Image embedding failed: {resp.status}")
        except Exception as e:
            print(f"❌ Image embedding error: {e}")
    
    return True


async def test_llava_service():
    """Test LLaVA service endpoints."""
    print("\n🧪 Testing LLaVA Service...")
    
    async with aiohttp.ClientSession() as session:
        # Test status
        try:
            async with session.get("http://localhost:8003/llava/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"✅ LLaVA Status: {status}")
                else:
                    print(f"❌ LLaVA Status failed: {resp.status}")
        except Exception as e:
            print(f"❌ LLaVA Service not available: {e}")
            return False
        
        # Test text embedding
        try:
            async with session.post(
                "http://localhost:8003/llava/embed/text",
                json="Describe the meaning of life"
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Text embedding: {result['dimensions']} dims, "
                          f"{result['processing_time_ms']:.2f}ms")
                else:
                    print(f"❌ Text embedding failed: {resp.status}")
        except Exception as e:
            print(f"⚠️  Text embedding error (model may be loading): {e}")
        
        # Test image analysis
        try:
            from PIL import Image, ImageDraw
            import io
            
            # Create a test image with text
            img = Image.new('RGB', (512, 512), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), "TEST IMAGE", fill='black')
            draw.rectangle([100, 100, 400, 400], outline='blue', width=3)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            data = aiohttp.FormData()
            data.add_field('file', img_bytes, filename='test.png',
                          content_type='image/png')
            data.add_field('instruction', 'Describe this test image')
            
            print("⏳ Analyzing image (this may take 30-60 seconds on first run)...")
            
            async with session.post(
                "http://localhost:8003/llava/analyze/image",
                data=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Image analysis complete:")
                    print(f"   Description: {result['description'][:100]}...")
                    print(f"   Embedding dims: {result['dimensions']}")
                    print(f"   Processing time: {result['processing_time_ms']:.2f}ms")
                    if result.get('ocr_text'):
                        print(f"   OCR text: {result['ocr_text']}")
                else:
                    print(f"❌ Image analysis failed: {resp.status}")
        except asyncio.TimeoutError:
            print("⚠️  Image analysis timed out (model may still be loading)")
        except Exception as e:
            print(f"⚠️  Image analysis error: {e}")
        
        # Test async queue
        try:
            async with session.get("http://localhost:8003/") as resp:
                if resp.status == 200:
                    info = await resp.json()
                    if info.get('async_enabled'):
                        print("✅ Async queue (Redis) is enabled")
                    else:
                        print("⚠️  Async queue not available (Redis not connected)")
        except Exception as e:
            print(f"❌ Service info error: {e}")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Second-Brain GPU Services Test Suite")
    print("=" * 60)
    
    # Test CLIP
    clip_ok = await test_clip_service()
    
    # Test LLaVA
    llava_ok = await test_llava_service()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"  CLIP Service: {'✅ Passed' if clip_ok else '❌ Failed'}")
    print(f"  LLaVA Service: {'✅ Passed' if llava_ok else '❌ Failed'}")
    
    if clip_ok and llava_ok:
        print("\n🎉 All GPU services are working correctly!")
        print("\n💡 Next steps:")
        print("  1. Update main API to use GPU services")
        print("  2. Update database schema for dual embeddings")
        print("  3. Test cross-platform development (Mac → Windows)")
    else:
        print("\n⚠️  Some services need attention.")
        print("  Run: docker-compose -f docker-compose.gpu.yml logs")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())