"""BRUTAL GPU STRESS TEST - MAKE THAT 4090 SCREAM!"""

import asyncio
import aiohttp
import time
import io
from PIL import Image, ImageDraw, ImageFont
import random
import numpy as np
from typing import List
import base64

# Test configuration
BATCH_SIZE = 32  # Process 32 items at once
NUM_ROUNDS = 5   # Number of test rounds
IMAGE_SIZE = (512, 512)  # Image dimensions


async def generate_random_image(idx: int) -> bytes:
    """Generate a random test image."""
    img = Image.new('RGB', IMAGE_SIZE, color=(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    ))
    draw = ImageDraw.Draw(img)
    
    # Draw random shapes
    for _ in range(10):
        shape_type = random.choice(['rectangle', 'ellipse', 'line'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'rectangle':
            x_coords = sorted([random.randint(0, 512) for _ in range(2)])
            y_coords = sorted([random.randint(0, 512) for _ in range(2)])
            coords = [x_coords[0], y_coords[0], x_coords[1], y_coords[1]]
            draw.rectangle(coords, fill=color, outline=(255, 255, 255))
        elif shape_type == 'ellipse':
            x_coords = sorted([random.randint(0, 512) for _ in range(2)])
            y_coords = sorted([random.randint(0, 512) for _ in range(2)])
            coords = [x_coords[0], y_coords[0], x_coords[1], y_coords[1]]
            draw.ellipse(coords, fill=color, outline=(255, 255, 255))
        else:
            coords = [random.randint(0, 512) for _ in range(4)]
            draw.line(coords, fill=color, width=5)
    
    # Add text
    draw.text((50, 50), f"GPU STRESS TEST {idx}", fill=(255, 255, 255))
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


async def stress_test_clip(session: aiohttp.ClientSession, round_num: int):
    """Stress test CLIP service."""
    print(f"\n[ROUND {round_num}] CLIP STRESS TEST - {BATCH_SIZE} images")
    print("-" * 60)
    
    # Generate batch of images
    images = []
    for i in range(BATCH_SIZE):
        img_data = await generate_random_image(i + round_num * 100)
        images.append(img_data)
    
    # Test batch embedding
    start_time = time.time()
    
    # Process all images in parallel
    tasks = []
    for img_data in images:
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='test.png', content_type='image/png')
        
        task = session.post("http://localhost:8002/clip/embed/image", data=data)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
    
    elapsed = time.time() - start_time
    throughput = BATCH_SIZE / elapsed
    
    print(f"  Processed: {success_count}/{BATCH_SIZE} images")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  Throughput: {throughput:.2f} images/second")
    print(f"  Per image: {(elapsed/BATCH_SIZE)*1000:.2f} ms")
    
    # Also test text embeddings
    texts = [f"Test prompt {i} for GPU stress testing" for i in range(BATCH_SIZE)]
    
    start_time = time.time()
    
    payload = {"text": texts}
    async with session.post("http://localhost:8002/clip/embed/text", json=payload) as resp:
        if resp.status == 200:
            result = await resp.json()
            elapsed = time.time() - start_time
            print(f"\n  Text batch embedding: {BATCH_SIZE} texts in {elapsed:.2f}s")
            print(f"  Text throughput: {BATCH_SIZE/elapsed:.2f} texts/second")


async def check_gpu_memory():
    """Check GPU memory usage."""
    import subprocess
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        used, total = map(int, result.stdout.strip().split(', '))
        return used, total
    return None, None


async def main():
    """Run the GPU stress test."""
    print("=" * 60)
    print("RTX 4090 STRESS TEST - MULTIMODAL EMBEDDINGS")
    print("=" * 60)
    
    # Check initial GPU status
    used, total = await check_gpu_memory()
    if used and total:
        print(f"\nGPU Memory: {used} MB / {total} MB ({(used/total)*100:.1f}% used)")
    
    async with aiohttp.ClientSession() as session:
        # Check if CLIP is running
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"\nCLIP Service: ONLINE")
                    print(f"  Model: {status['model_name']}")
                    print(f"  Device: {status['device']}")
                    print(f"  VRAM: {status['vram_used_gb']:.2f} GB")
                    print(f"  Requests processed: {status['requests_processed']}")
        except:
            print("\nERROR: CLIP service not available on port 8002")
            print("Start it with: cd services/gpu && python clip/clip_api.py")
            return
        
        # Run stress test rounds
        print(f"\n{'='*60}")
        print(f"STARTING {NUM_ROUNDS} ROUNDS OF {BATCH_SIZE} IMAGES EACH")
        print(f"TOTAL: {NUM_ROUNDS * BATCH_SIZE} EMBEDDINGS")
        print(f"{'='*60}")
        
        total_start = time.time()
        
        for round_num in range(1, NUM_ROUNDS + 1):
            await stress_test_clip(session, round_num)
            
            # Check GPU memory after each round
            used, total = await check_gpu_memory()
            if used and total:
                print(f"\n  GPU Memory: {used} MB / {total} MB ({(used/total)*100:.1f}% used)")
        
        total_elapsed = time.time() - total_start
        
        # Final stats
        print(f"\n{'='*60}")
        print("STRESS TEST COMPLETE!")
        print(f"{'='*60}")
        print(f"Total images processed: {NUM_ROUNDS * BATCH_SIZE * 2}")  # *2 for images + texts
        print(f"Total time: {total_elapsed:.2f} seconds")
        print(f"Average throughput: {(NUM_ROUNDS * BATCH_SIZE * 2)/total_elapsed:.2f} items/second")
        
        # Check final status
        async with session.get("http://localhost:8002/clip/status") as resp:
            if resp.status == 200:
                status = await resp.json()
                print(f"\nFinal requests processed: {status['requests_processed']}")
                print(f"Final VRAM usage: {status['vram_used_gb']:.2f} GB")
        
        # Check final GPU memory
        used, total = await check_gpu_memory()
        if used and total:
            print(f"Final GPU Memory: {used} MB / {total} MB ({(used/total)*100:.1f}% used)")
        
        print(f"\n{'='*60}")
        print("YOUR RTX 4090 JUST CRUSHED IT!")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())