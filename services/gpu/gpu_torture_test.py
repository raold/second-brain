"""EXTREME GPU TORTURE TEST - BOTH MODELS SIMULTANEOUSLY!"""

import asyncio
import aiohttp
import time
import io
from PIL import Image, ImageDraw
import random
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor

# EXTREME TEST CONFIGURATION
BATCH_SIZE = 64  # DOUBLE THE BATCH SIZE
NUM_ROUNDS = 10  # MORE ROUNDS
IMAGE_SIZE = (768, 768)  # BIGGER IMAGES
CONCURRENT_REQUESTS = 16  # PARALLEL REQUESTS


async def generate_complex_image(idx: int) -> bytes:
    """Generate a complex test image with text."""
    img = Image.new('RGB', IMAGE_SIZE, color=(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    ))
    draw = ImageDraw.Draw(img)
    
    # Draw MORE random shapes
    for _ in range(20):
        shape_type = random.choice(['rectangle', 'ellipse', 'polygon'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'rectangle':
            x_coords = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y_coords = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            coords = [x_coords[0], y_coords[0], x_coords[1], y_coords[1]]
            draw.rectangle(coords, fill=color, outline=(255, 255, 255), width=3)
        elif shape_type == 'ellipse':
            x_coords = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y_coords = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            coords = [x_coords[0], y_coords[0], x_coords[1], y_coords[1]]
            draw.ellipse(coords, fill=color, outline=(255, 255, 255), width=3)
        else:
            # Polygon
            points = [(random.randint(0, IMAGE_SIZE[0]), random.randint(0, IMAGE_SIZE[1])) for _ in range(5)]
            draw.polygon(points, fill=color, outline=(255, 255, 255))
    
    # Add multiple text elements
    for i in range(5):
        draw.text(
            (random.randint(0, IMAGE_SIZE[0]-200), random.randint(0, IMAGE_SIZE[1]-50)),
            f"TORTURE TEST {idx}-{i}\nGPU STRESS\nRTX 4090",
            fill=(255, 255, 255)
        )
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG', optimize=False)  # No optimization for speed
    img_bytes.seek(0)
    return img_bytes.getvalue()


async def torture_clip(session: aiohttp.ClientSession, round_num: int):
    """TORTURE TEST CLIP with massive parallel load."""
    print(f"\n[ROUND {round_num}] CLIP TORTURE - {BATCH_SIZE} images")
    print("-" * 80)
    
    # Generate batch of complex images
    print(f"  Generating {BATCH_SIZE} complex images...")
    images = []
    for i in range(BATCH_SIZE):
        img_data = await generate_complex_image(i + round_num * 1000)
        images.append(img_data)
    
    # PARALLEL ASSAULT ON CLIP
    start_time = time.time()
    
    # Split into chunks for concurrent processing
    chunk_size = CONCURRENT_REQUESTS
    chunks = [images[i:i+chunk_size] for i in range(0, len(images), chunk_size)]
    
    total_processed = 0
    for chunk_idx, chunk in enumerate(chunks):
        tasks = []
        for img_data in chunk:
            data = aiohttp.FormData()
            data.add_field('file', img_data, filename='test.png', content_type='image/png')
            task = session.post("http://localhost:8002/clip/embed/image", data=data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
        total_processed += success_count
        print(f"    Chunk {chunk_idx+1}: {success_count}/{len(chunk)} processed")
    
    elapsed = time.time() - start_time
    throughput = BATCH_SIZE / elapsed
    
    print(f"  CLIP Results:")
    print(f"    Total processed: {total_processed}/{BATCH_SIZE} images")
    print(f"    Total time: {elapsed:.2f} seconds")
    print(f"    Throughput: {throughput:.2f} images/second")
    print(f"    Per image: {(elapsed/BATCH_SIZE)*1000:.2f} ms")
    
    return elapsed


async def torture_llava(session: aiohttp.ClientSession, round_num: int):
    """TORTURE TEST LLaVA if available."""
    print(f"\n[ROUND {round_num}] LLAVA TORTURE TEST")
    print("-" * 80)
    
    try:
        # Check if LLaVA is running
        async with session.get("http://localhost:8003/llava/status", timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status != 200:
                print("  LLaVA not available yet")
                return 0
            status = await resp.json()
            print(f"  LLaVA Status: Model loaded = {status['model_loaded']}")
            
            if not status['model_loaded']:
                # Try to trigger model loading with a single request
                print("  Triggering LLaVA model load...")
                img_data = await generate_complex_image(999)
                data = aiohttp.FormData()
                data.add_field('file', img_data, filename='test.png', content_type='image/png')
                data.add_field('instruction', 'Describe this image')
                
                try:
                    async with session.post(
                        "http://localhost:8003/llava/analyze/image",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status == 200:
                            print("  LLaVA model loaded successfully!")
                except:
                    print("  LLaVA still loading...")
                return 0
    except:
        print("  LLaVA service not running")
        return 0
    
    # Run LLaVA analysis on a few images
    start_time = time.time()
    num_llava_tests = min(5, BATCH_SIZE // 10)  # Test fewer images due to slower processing
    
    for i in range(num_llava_tests):
        img_data = await generate_complex_image(round_num * 1000 + i)
        data = aiohttp.FormData()
        data.add_field('file', img_data, filename='test.png', content_type='image/png')
        data.add_field('instruction', f'Describe image {i} and extract any text')
        
        try:
            async with session.post(
                "http://localhost:8003/llava/analyze/image",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"    Image {i+1}: Analyzed in {result['processing_time_ms']:.0f}ms")
        except asyncio.TimeoutError:
            print(f"    Image {i+1}: Timeout")
        except Exception as e:
            print(f"    Image {i+1}: Error - {str(e)[:50]}")
    
    elapsed = time.time() - start_time
    if num_llava_tests > 0:
        print(f"  LLaVA Total time: {elapsed:.2f}s for {num_llava_tests} images")
        print(f"  LLaVA Per image: {(elapsed/num_llava_tests):.2f}s")
    
    return elapsed


async def check_gpu_status():
    """Check detailed GPU status."""
    import subprocess
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", 
         "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        parts = result.stdout.strip().split(', ')
        return {
            'gpu_util': int(parts[0]),
            'mem_used': int(parts[1]),
            'mem_total': int(parts[2]),
            'temp': int(parts[3])
        }
    return None


async def main():
    """Run the EXTREME GPU torture test."""
    print("=" * 80)
    print("RTX 4090 EXTREME TORTURE TEST")
    print("DUAL MODEL STRESS TEST - CLIP + LLAVA")
    print("=" * 80)
    
    # Check initial GPU status
    gpu_status = await check_gpu_status()
    if gpu_status:
        print(f"\nInitial GPU Status:")
        print(f"  GPU Utilization: {gpu_status['gpu_util']}%")
        print(f"  Memory: {gpu_status['mem_used']} MB / {gpu_status['mem_total']} MB ({(gpu_status['mem_used']/gpu_status['mem_total'])*100:.1f}%)")
        print(f"  Temperature: {gpu_status['temp']}°C")
    
    async with aiohttp.ClientSession() as session:
        # Check services
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    print("\nCLIP Service: READY FOR TORTURE")
        except:
            print("\nERROR: CLIP not running! Start with: cd services/gpu && python clip/clip_api.py")
            return
        
        print(f"\n{'='*80}")
        print(f"STARTING {NUM_ROUNDS} ROUNDS OF TORTURE")
        print(f"BATCH SIZE: {BATCH_SIZE} | IMAGE SIZE: {IMAGE_SIZE}")
        print(f"CONCURRENT REQUESTS: {CONCURRENT_REQUESTS}")
        print(f"{'='*80}")
        
        total_start = time.time()
        max_gpu_util = 0
        max_mem_used = 0
        max_temp = 0
        
        for round_num in range(1, NUM_ROUNDS + 1):
            print(f"\n{'='*80}")
            print(f"TORTURE ROUND {round_num}/{NUM_ROUNDS}")
            print(f"{'='*80}")
            
            # Run both models in parallel if possible
            clip_task = asyncio.create_task(torture_clip(session, round_num))
            llava_task = asyncio.create_task(torture_llava(session, round_num))
            
            clip_time, llava_time = await asyncio.gather(clip_task, llava_task)
            
            # Check GPU status after each round
            gpu_status = await check_gpu_status()
            if gpu_status:
                max_gpu_util = max(max_gpu_util, gpu_status['gpu_util'])
                max_mem_used = max(max_mem_used, gpu_status['mem_used'])
                max_temp = max(max_temp, gpu_status['temp'])
                
                print(f"\n  GPU Status After Round {round_num}:")
                print(f"    GPU Utilization: {gpu_status['gpu_util']}% (Peak: {max_gpu_util}%)")
                print(f"    Memory: {gpu_status['mem_used']} MB / {gpu_status['mem_total']} MB")
                print(f"    Temperature: {gpu_status['temp']}°C (Peak: {max_temp}°C)")
        
        total_elapsed = time.time() - total_start
        
        # Final stats
        print(f"\n{'='*80}")
        print("TORTURE TEST COMPLETE!")
        print(f"{'='*80}")
        print(f"Total time: {total_elapsed:.2f} seconds")
        print(f"Total images processed: ~{NUM_ROUNDS * BATCH_SIZE}")
        print(f"\nPEAK GPU METRICS:")
        print(f"  Max GPU Utilization: {max_gpu_util}%")
        print(f"  Max Memory Used: {max_mem_used} MB")
        print(f"  Max Temperature: {max_temp}°C")
        
        # Check final service status
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"\nCLIP Final Stats:")
                    print(f"  Total requests: {status['requests_processed']}")
                    print(f"  VRAM usage: {status['vram_used_gb']:.2f} GB")
        except:
            pass
        
        try:
            async with session.get("http://localhost:8003/llava/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"\nLLaVA Final Stats:")
                    print(f"  Model loaded: {status['model_loaded']}")
                    if status.get('vram_used_gb'):
                        print(f"  VRAM usage: {status['vram_used_gb']:.2f} GB")
        except:
            pass
        
        print(f"\n{'='*80}")
        print("YOUR RTX 4090 IS A FUCKING MONSTER!")
        print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())