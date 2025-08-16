"""BULLETPROOF TEST - All modalities for CLIP and LLaVA"""

import asyncio
import aiohttp
import io
import time
from PIL import Image, ImageDraw, ImageFont
import json
import base64

# Test configuration
CLIP_URL = "http://localhost:8002"
LLAVA_URL = "http://localhost:8003"


def create_test_image(text: str = "TEST IMAGE") -> bytes:
    """Create a test image with text."""
    img = Image.new('RGB', (512, 512), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    
    # Draw shapes
    d.rectangle([50, 50, 200, 200], fill=(255, 0, 0))
    d.ellipse([250, 50, 400, 200], fill=(0, 255, 0))
    d.polygon([(100, 300), (200, 250), (300, 300), (250, 400), (150, 400)], fill=(0, 0, 255))
    
    # Add text
    d.text((256, 256), text, fill=(255, 255, 255))
    d.text((50, 450), "BULLETPROOF TEST", fill=(255, 255, 0))
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


async def test_clip_text(session: aiohttp.ClientSession):
    """Test CLIP text embedding."""
    print("\n[CLIP] Testing text embedding...")
    
    texts = [
        "A beautiful sunset over the mountains",
        "Technical documentation for API endpoints",
        "Machine learning model optimization techniques"
    ]
    
    for text in texts:
        try:
            payload = {"text": text}
            async with session.post(f"{CLIP_URL}/clip/embed/text", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"  [OK] Text embedding: dims={result['dimensions']}, text='{text[:30]}...'")
                else:
                    print(f"  [FAIL] Failed: {resp.status}")
        except Exception as e:
            print(f"  [FAIL] Error: {str(e)[:50]}")


async def test_clip_image(session: aiohttp.ClientSession):
    """Test CLIP image embedding."""
    print("\n[CLIP] Testing image embedding...")
    
    try:
        img_data = create_test_image("CLIP TEST")
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='test.png', content_type='image/png')
        
        async with session.post(f"{CLIP_URL}/clip/embed/image", data=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  [OK] Image embedding: dims={result['dimensions']}")
            else:
                print(f"  [FAIL] Failed: {resp.status}")
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:50]}")


async def test_clip_batch(session: aiohttp.ClientSession):
    """Test CLIP batch processing."""
    print("\n[CLIP] Testing batch processing...")
    
    try:
        # Batch text
        texts = [f"Test text {i}" for i in range(10)]
        payload = {"text": texts}
        
        async with session.post(f"{CLIP_URL}/clip/embed/text", json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  [OK] Batch text: {len(result['embeddings'])} embeddings")
            else:
                print(f"  [FAIL] Batch failed: {resp.status}")
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:50]}")


async def test_llava_text(session: aiohttp.ClientSession):
    """Test LLaVA text embedding."""
    print("\n[LLaVA] Testing text embedding...")
    
    texts = [
        "Advanced neural network architectures",
        "Quantum computing fundamentals",
        "Data pipeline optimization strategies"
    ]
    
    for text in texts:
        try:
            # LLaVA expects plain string for text endpoint
            async with session.post(
                f"{LLAVA_URL}/llava/embed/text",
                json=text,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"  [OK] Text embedding: dims={result['dimensions']}, text='{text[:30]}...'")
                else:
                    error = await resp.text()
                    print(f"  [FAIL] Failed ({resp.status}): {error[:100]}")
        except Exception as e:
            print(f"  [FAIL] Error: {str(e)[:50]}")


async def test_llava_image_analysis(session: aiohttp.ClientSession):
    """Test LLaVA image analysis."""
    print("\n[LLaVA] Testing image analysis...")
    
    try:
        img_data = create_test_image("LLAVA ANALYSIS")
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='llava_test.png', content_type='image/png')
        data.add_field('instruction', 'Describe this image in detail. What shapes and text do you see?')
        
        async with session.post(
            f"{LLAVA_URL}/llava/analyze/image",
            data=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  [OK] Image analysis successful!")
                print(f"    Description: {result['description'][:150]}...")
                print(f"    Embedding dims: {result['dimensions']}")
            else:
                error = await resp.text()
                print(f"  [FAIL] Failed ({resp.status}): {error[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:100]}")


async def test_llava_image_embedding(session: aiohttp.ClientSession):
    """Test LLaVA image embedding."""
    print("\n[LLaVA] Testing image embedding...")
    
    try:
        img_data = create_test_image("EMBEDDING TEST")
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='embed_test.png', content_type='image/png')
        
        async with session.post(
            f"{LLAVA_URL}/llava/embed/image",
            data=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  [OK] Image embedding: dims={result['dimensions']}")
            else:
                error = await resp.text()
                print(f"  [FAIL] Failed ({resp.status}): {error[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:100]}")


async def test_llava_ocr(session: aiohttp.ClientSession):
    """Test LLaVA OCR capability."""
    print("\n[LLaVA] Testing OCR...")
    
    try:
        # Create image with clear text
        img = Image.new('RGB', (800, 200), color='white')
        d = ImageDraw.Draw(img)
        d.text((50, 50), "EXTRACT THIS TEXT", fill='black')
        d.text((50, 100), "Multiple lines of text", fill='blue')
        d.text((50, 150), "OCR TEST SUCCESS", fill='red')
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='ocr_test.png', content_type='image/png')
        
        async with session.post(
            f"{LLAVA_URL}/llava/extract_text",
            data=data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  [OK] OCR successful!")
                print(f"    Extracted: {result['text'][:200]}")
            else:
                error = await resp.text()
                print(f"  [FAIL] Failed ({resp.status}): {error[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:100]}")


async def test_gpu_stats(session: aiohttp.ClientSession):
    """Check GPU utilization."""
    print("\n[GPU] Checking status...")
    
    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            gpu_util = int(parts[0])
            mem_used = int(parts[1])
            mem_total = int(parts[2])
            temp = int(parts[3])
            
            print(f"  GPU Utilization: {gpu_util}%")
            print(f"  VRAM: {mem_used} MB / {mem_total} MB ({(mem_used/mem_total)*100:.1f}%)")
            print(f"  Temperature: {temp}°C")
    except Exception as e:
        print(f"  Could not read GPU stats: {e}")


async def main():
    """Run all bulletproof tests."""
    print("=" * 80)
    print("BULLETPROOF MULTIMODAL TEST SUITE")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Check services
        print("\nChecking service availability...")
        
        try:
            async with session.get(f"{CLIP_URL}/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"[OK] CLIP: Ready (Model loaded: {status['model_loaded']})")
        except:
            print("[FAIL] CLIP: Not available")
            
        try:
            async with session.get(f"{LLAVA_URL}/llava/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"[OK] LLaVA: Ready (Model loaded: {status['model_loaded']})")
        except:
            print("[FAIL] LLaVA: Not available")
        
        # Run all tests
        print("\n" + "="*80)
        print("RUNNING COMPREHENSIVE TESTS")
        print("="*80)
        
        # CLIP tests
        await test_clip_text(session)
        await test_clip_image(session)
        await test_clip_batch(session)
        
        # LLaVA tests
        await test_llava_text(session)
        await test_llava_image_embedding(session)
        await test_llava_image_analysis(session)
        await test_llava_ocr(session)
        
        # GPU status
        await test_gpu_stats(session)
        
        print("\n" + "="*80)
        print("BULLETPROOF TEST COMPLETE!")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())