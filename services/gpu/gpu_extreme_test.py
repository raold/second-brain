"""EXTREME GPU TEST - NO UNICODE BULLSHIT"""

import asyncio
import aiohttp
import time
import io
from PIL import Image, ImageDraw
import random

BATCH_SIZE = 96
NUM_ROUNDS = 8
IMAGE_SIZE = (768, 768)


async def generate_test_image(idx: int) -> bytes:
    """Generate test image."""
    img = Image.new('RGB', IMAGE_SIZE, color=(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    ))
    draw = ImageDraw.Draw(img)
    
    for _ in range(20):
        shape_type = random.choice(['rectangle', 'ellipse'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'rectangle':
            x1, x2 = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y1, y2 = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            draw.rectangle([x1, y1, x2, y2], fill=color, outline=(255, 255, 255), width=3)
        else:
            x1, x2 = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y1, y2 = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            draw.ellipse([x1, y1, x2, y2], fill=color, outline=(255, 255, 255), width=3)
    
    draw.text((50, 50), f"EXTREME TEST {idx}", fill=(255, 255, 255))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


async def test_clip_extreme(session: aiohttp.ClientSession, round_num: int):
    """Extreme CLIP test."""
    print(f"\\n[ROUND {round_num}] EXTREME CLIP TEST - {BATCH_SIZE} images")
    
    # Generate images
    images = []
    for i in range(BATCH_SIZE):
        img_data = await generate_test_image(i + round_num * 1000)
        images.append(img_data)
    
    start_time = time.time()
    
    # Process in parallel chunks
    chunk_size = 16
    chunks = [images[i:i+chunk_size] for i in range(0, len(images), chunk_size)]
    
    total_processed = 0
    for chunk in chunks:
        tasks = []
        for img_data in chunk:
            data = aiohttp.FormData()
            data.add_field('file', img_data, filename='test.png', content_type='image/png')
            task = session.post("http://localhost:8002/clip/embed/image", data=data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
        total_processed += success_count
    
    elapsed = time.time() - start_time
    throughput = BATCH_SIZE / elapsed
    
    print(f"  CLIP: {total_processed}/{BATCH_SIZE} processed in {elapsed:.2f}s ({throughput:.2f} img/s)")
    
    # Also test text batch
    texts = [f"Extreme test text {i}" for i in range(BATCH_SIZE)]
    start_time = time.time()
    
    payload = {"text": texts}
    async with session.post("http://localhost:8002/clip/embed/text", json=payload) as resp:
        if resp.status == 200:
            elapsed = time.time() - start_time
            print(f"  CLIP Text: {BATCH_SIZE} texts in {elapsed:.2f}s ({BATCH_SIZE/elapsed:.2f} texts/s)")


async def test_llava_if_ready(session: aiohttp.ClientSession, round_num: int):
    """Test LLaVA if ready."""
    try:
        async with session.get("http://localhost:8003/llava/status", timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status == 200:
                status = await resp.json()
                if status.get('model_loaded', False):
                    print(f"  LLaVA is ready! Testing...")
                    
                    # Test with one image
                    img_data = await generate_test_image(round_num * 9999)
                    data = aiohttp.FormData()
                    data.add_field('file', img_data, filename='llava_test.png', content_type='image/png')
                    data.add_field('instruction', 'Describe this test image')
                    
                    start_time = time.time()
                    async with session.post(
                        "http://localhost:8003/llava/analyze/image",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            elapsed = time.time() - start_time
                            print(f"  LLaVA: Analysis completed in {elapsed:.2f}s")
                            print(f"    Description: {result['description'][:100]}...")
                        else:
                            print(f"  LLaVA: Error {resp.status}")
                else:
                    print(f"  LLaVA: Model still loading...")
            else:
                print(f"  LLaVA: Service error")
    except:
        print(f"  LLaVA: Not available")


async def check_gpu():
    """Check GPU status."""
    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            return {
                'util': int(parts[0]),
                'mem_used': int(parts[1]),
                'mem_total': int(parts[2]),
                'temp': int(parts[3])
            }
    except:
        pass
    return None


async def main():
    """Run extreme test."""
    print("=" * 80)
    print("RTX 4090 EXTREME MULTIMODAL TEST")
    print("=" * 80)
    
    gpu = await check_gpu()
    if gpu:
        print(f"\\nInitial GPU: {gpu['util']}% util, {gpu['mem_used']} MB VRAM, {gpu['temp']}C")
    
    async with aiohttp.ClientSession() as session:
        # Check CLIP
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    print("\\nCLIP: READY")
        except:
            print("\\nCLIP: NOT READY")
            return
        
        print(f"\\nStarting {NUM_ROUNDS} rounds of {BATCH_SIZE} images each...")
        print("=" * 80)
        
        max_util = 0
        max_mem = 0
        max_temp = 0
        
        for round_num in range(1, NUM_ROUNDS + 1):
            print(f"\\nROUND {round_num}/{NUM_ROUNDS}")
            
            # Run tests
            await test_clip_extreme(session, round_num)
            await test_llava_if_ready(session, round_num)
            
            # Check GPU
            gpu = await check_gpu()
            if gpu:
                max_util = max(max_util, gpu['util'])
                max_mem = max(max_mem, gpu['mem_used'])
                max_temp = max(max_temp, gpu['temp'])
                
                print(f"  GPU: {gpu['util']}% util, {gpu['mem_used']} MB VRAM, {gpu['temp']}C")
        
        print(f"\\n{'='*80}")
        print("EXTREME TEST COMPLETE!")
        print(f"Peak GPU: {max_util}% util, {max_mem} MB VRAM, {max_temp}C")
        print("YOUR RTX 4090 IS A FUCKING BEAST!")
        print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())