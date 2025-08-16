"""MAXIMUM GPU ASSAULT - MAKE THAT 4090 BEG FOR MERCY!"""

import asyncio
import aiohttp
import time
import io
from PIL import Image, ImageDraw, ImageFont
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import json

# EXTREME ASSAULT CONFIGURATION
MASSIVE_BATCH_SIZE = 128  # HUGE BATCHES
CONCURRENT_STREAMS = 32   # MULTIPLE PARALLEL STREAMS
NUM_ASSAULT_ROUNDS = 15   # LONG SUSTAINED ASSAULT
IMAGE_SIZE = (1024, 1024) # MASSIVE IMAGES
TEXT_BATCH_SIZE = 256     # HUGE TEXT BATCHES


async def generate_massive_image(idx: int) -> bytes:
    """Generate a massive, complex image."""
    img = Image.new('RGB', IMAGE_SIZE, color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fill with complex patterns
    for _ in range(50):  # MORE SHAPES
        shape_type = random.choice(['rectangle', 'ellipse', 'polygon', 'arc'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'rectangle':
            x1, x2 = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y1, y2 = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            draw.rectangle([x1, y1, x2, y2], fill=color, outline=(255, 255, 255), width=5)
        elif shape_type == 'ellipse':
            x1, x2 = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y1, y2 = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            draw.ellipse([x1, y1, x2, y2], fill=color, outline=(255, 255, 255), width=5)
        elif shape_type == 'polygon':
            points = [(random.randint(0, IMAGE_SIZE[0]), random.randint(0, IMAGE_SIZE[1])) for _ in range(8)]
            draw.polygon(points, fill=color, outline=(255, 255, 255))
        else:  # arc
            x1, x2 = sorted([random.randint(0, IMAGE_SIZE[0]) for _ in range(2)])
            y1, y2 = sorted([random.randint(0, IMAGE_SIZE[1]) for _ in range(2)])
            start_angle = random.randint(0, 360)
            end_angle = start_angle + random.randint(30, 180)
            draw.arc([x1, y1, x2, y2], start_angle, end_angle, fill=color, width=10)
    
    # Add text everywhere
    texts = [
        f"MAXIMUM GPU ASSAULT {idx}",
        "RTX 4090 TORTURE TEST",
        f"BATCH SIZE: {MASSIVE_BATCH_SIZE}",
        "MULTIMODAL EMBEDDING STRESS",
        f"IMAGE {idx} PROCESSING",
        "CLIP + LLAVA SIMULTANEOUSLY",
        "VRAM UTILIZATION EXTREME",
        f"CONCURRENT STREAM {idx % CONCURRENT_STREAMS}"
    ]
    
    for i, text in enumerate(texts):
        x = random.randint(0, IMAGE_SIZE[0] - 400)
        y = random.randint(0, IMAGE_SIZE[1] - 100)
        draw.text((x, y), text, fill=(255, 255, 255))
    
    # Convert to high-quality bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG', optimize=False, compress_level=1)  # Fast compression
    img_bytes.seek(0)
    return img_bytes.getvalue()


async def assault_clip_batch(session: aiohttp.ClientSession, batch_images: list, batch_id: int):
    """Assault CLIP with a massive batch."""
    print(f"    Launching CLIP assault batch {batch_id} with {len(batch_images)} images...")
    
    start_time = time.time()
    
    # Split into concurrent chunks
    chunk_size = CONCURRENT_STREAMS
    chunks = [batch_images[i:i+chunk_size] for i in range(0, len(batch_images), chunk_size)]
    
    total_processed = 0
    chunk_tasks = []
    
    for chunk_idx, chunk in enumerate(chunks):
        tasks = []
        for img_data in chunk:
            data = aiohttp.FormData()
            data.add_field('file', img_data, filename=f'assault_{batch_id}_{chunk_idx}.png', content_type='image/png')
            task = session.post("http://localhost:8002/clip/embed/image", data=data)
            tasks.append(task)
        
        chunk_task = asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
        chunk_tasks.append(chunk_task)
    
    # Process all chunks concurrently
    chunk_results = await asyncio.gather(*chunk_tasks)
    
    for chunk_result in chunk_results:
        for response in chunk_result:
            if not isinstance(response, Exception) and hasattr(response, 'status') and response.status == 200:
                total_processed += 1
    
    elapsed = time.time() - start_time
    throughput = len(batch_images) / elapsed if elapsed > 0 else 0
    
    print(f"    CLIP Batch {batch_id}: {total_processed}/{len(batch_images)} processed in {elapsed:.2f}s ({throughput:.2f} img/s)")
    return total_processed, elapsed


async def assault_clip_text_batch(session: aiohttp.ClientSession, batch_id: int):
    """Assault CLIP with massive text batches."""
    texts = [
        f"GPU assault text batch {batch_id} item {i}: Complex multimodal embedding test with RTX 4090 maximum utilization scenario"
        for i in range(TEXT_BATCH_SIZE)
    ]
    
    start_time = time.time()
    
    try:
        payload = {"text": texts}
        async with session.post("http://localhost:8002/clip/embed/text", json=payload) as resp:
            if resp.status == 200:
                elapsed = time.time() - start_time
                throughput = TEXT_BATCH_SIZE / elapsed
                print(f"    CLIP Text Batch {batch_id}: {TEXT_BATCH_SIZE} texts in {elapsed:.2f}s ({throughput:.2f} texts/s)")
                return TEXT_BATCH_SIZE, elapsed
    except Exception as e:
        print(f"    CLIP Text Batch {batch_id}: Error - {str(e)[:50]}")
    
    return 0, 0


async def assault_llava_samples(session: aiohttp.ClientSession, images: list, round_num: int):
    """Assault LLaVA with selected images."""
    # Test if LLaVA is ready
    try:
        async with session.get("http://localhost:8003/llava/status", timeout=aiohttp.ClientTimeout(total=2)) as resp:
            if resp.status != 200:
                return 0, 0
            status = await resp.json()
            if not status.get('model_loaded', False):
                return 0, 0
    except:
        return 0, 0
    
    print(f"    Launching LLaVA assault on {len(images)} selected images...")
    
    start_time = time.time()
    processed = 0
    
    # Process multiple images in parallel (but fewer than CLIP due to complexity)
    semaphore = asyncio.Semaphore(4)  # Limit concurrent LLaVA requests
    
    async def process_llava_image(img_data, img_idx):
        async with semaphore:
            try:
                data = aiohttp.FormData()
                data.add_field('file', img_data, filename=f'llava_test_{img_idx}.png', content_type='image/png')
                data.add_field('instruction', f'Analyze this complex image {img_idx} in detail. Extract any text and describe all visual elements.')
                
                async with session.post(
                    "http://localhost:8003/llava/analyze/image",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return 1, result.get('processing_time_ms', 0)
            except Exception as e:
                print(f"      LLaVA image {img_idx}: {str(e)[:30]}")
            return 0, 0
    
    tasks = [process_llava_image(img, i) for i, img in enumerate(images)]
    results = await asyncio.gather(*tasks)
    
    processed = sum(r[0] for r in results)
    total_time = time.time() - start_time
    
    if processed > 0:
        avg_time_per_image = total_time / processed
        print(f"    LLaVA Assault: {processed}/{len(images)} processed in {total_time:.2f}s ({avg_time_per_image:.2f}s per image)")
    
    return processed, total_time


async def monitor_gpu_devastation():
    """Monitor GPU as we devastate it."""
    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw", 
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            return {
                'gpu_util': int(parts[0]),
                'mem_used': int(parts[1]),
                'mem_total': int(parts[2]),
                'temp': int(parts[3]),
                'power': float(parts[4]) if len(parts) > 4 else 0
            }
    except:
        pass
    return None


async def main():
    """LAUNCH THE MAXIMUM GPU ASSAULT!"""
    print("=" * 100)
    print("MAXIMUM RTX 4090 ASSAULT - PREPARE FOR GPU DEVASTATION")
    print("=" * 100)
    
    # Initial GPU status
    gpu_status = await monitor_gpu_devastation()
    if gpu_status:
        print(f"\n🎯 PRE-ASSAULT GPU STATUS:")
        print(f"   GPU Utilization: {gpu_status['gpu_util']}%")
        print(f"   Memory: {gpu_status['mem_used']} MB / {gpu_status['mem_total']} MB ({(gpu_status['mem_used']/gpu_status['mem_total'])*100:.1f}%)")
        print(f"   Temperature: {gpu_status['temp']}°C")
        print(f"   Power Draw: {gpu_status['power']}W")
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60),
        connector=aiohttp.TCPConnector(limit=200, limit_per_host=100)
    ) as session:
        
        # Verify CLIP is ready
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"\n✅ CLIP READY FOR ASSAULT:")
                    print(f"   Requests processed: {status['requests_processed']}")
                    print(f"   VRAM usage: {status['vram_used_gb']:.2f} GB")
        except:
            print("\n❌ CLIP NOT READY! Aborting assault.")
            return
        
        # Check LLaVA
        llava_ready = False
        try:
            async with session.get("http://localhost:8003/llava/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    llava_ready = status.get('model_loaded', False)
                    print(f"\n{'✅' if llava_ready else '⏳'} LLaVA STATUS:")
                    print(f"   Model loaded: {llava_ready}")
        except:
            print("\n⚠️ LLaVA not responding (may still be loading)")
        
        print(f"\n{'='*100}")
        print(f"🔥 COMMENCING {NUM_ASSAULT_ROUNDS} ROUNDS OF MAXIMUM ASSAULT 🔥")
        print(f"   Batch Size: {MASSIVE_BATCH_SIZE} images per round")
        print(f"   Text Batch: {TEXT_BATCH_SIZE} texts per round")
        print(f"   Concurrent Streams: {CONCURRENT_STREAMS}")
        print(f"   Image Size: {IMAGE_SIZE}")
        print(f"{'='*100}")
        
        # Track peak metrics
        peak_gpu_util = 0
        peak_memory = 0
        peak_temp = 0
        peak_power = 0
        total_images_processed = 0
        total_texts_processed = 0
        
        assault_start = time.time()
        
        for round_num in range(1, NUM_ASSAULT_ROUNDS + 1):
            print(f"\n🔥 ASSAULT ROUND {round_num}/{NUM_ASSAULT_ROUNDS} - MAXIMUM DEVASTATION 🔥")
            print("-" * 100)
            
            round_start = time.time()
            
            # Generate massive image batch
            print(f"  Generating {MASSIVE_BATCH_SIZE} complex {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]} images...")
            image_gen_start = time.time()
            
            # Generate images in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                loop = asyncio.get_event_loop()
                image_tasks = [
                    loop.run_in_executor(executor, asyncio.run, generate_massive_image(i + round_num * 10000))
                    for i in range(MASSIVE_BATCH_SIZE)
                ]
                images = await asyncio.gather(*image_tasks)
            
            image_gen_time = time.time() - image_gen_start
            print(f"  Generated {len(images)} images in {image_gen_time:.2f}s")
            
            # SIMULTANEOUS MULTI-MODEL ASSAULT
            print(f"\n  🚀 LAUNCHING SIMULTANEOUS MULTI-MODEL ASSAULT...")
            
            # Create parallel tasks for both models
            tasks = []
            
            # CLIP image assault
            tasks.append(assault_clip_batch(session, images, round_num))
            
            # CLIP text assault
            tasks.append(assault_clip_text_batch(session, round_num))
            
            # LLaVA assault (if ready)
            if llava_ready:
                # Select subset for LLaVA (it's slower)
                llava_images = images[:min(8, len(images))]
                tasks.append(assault_llava_samples(session, llava_images, round_num))
            
            # Execute all assaults simultaneously
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            clip_img_processed, clip_img_time = results[0] if len(results) > 0 and not isinstance(results[0], Exception) else (0, 0)
            clip_text_processed, clip_text_time = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else (0, 0)
            llava_processed, llava_time = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else (0, 0)
            
            total_images_processed += clip_img_processed
            total_texts_processed += clip_text_processed
            
            round_time = time.time() - round_start
            
            # Check GPU devastation
            gpu_status = await monitor_gpu_devastation()
            if gpu_status:
                peak_gpu_util = max(peak_gpu_util, gpu_status['gpu_util'])
                peak_memory = max(peak_memory, gpu_status['mem_used'])
                peak_temp = max(peak_temp, gpu_status['temp'])
                peak_power = max(peak_power, gpu_status['power'])
                
                print(f"\n  📊 GPU DEVASTATION METRICS:")
                print(f"     GPU Utilization: {gpu_status['gpu_util']}% (Peak: {peak_gpu_util}%)")
                print(f"     Memory Usage: {gpu_status['mem_used']} MB / {gpu_status['mem_total']} MB")
                print(f"     Temperature: {gpu_status['temp']}°C (Peak: {peak_temp}°C)")
                print(f"     Power Draw: {gpu_status['power']}W (Peak: {peak_power}W)")
            
            print(f"\n  ⚡ ROUND {round_num} DEVASTATION SUMMARY:")
            print(f"     Total round time: {round_time:.2f}s")
            print(f"     CLIP images: {clip_img_processed} processed")
            print(f"     CLIP texts: {clip_text_processed} processed")
            if llava_ready:
                print(f"     LLaVA analyses: {llava_processed} completed")
        
        total_assault_time = time.time() - assault_start
        
        # FINAL DEVASTATION REPORT
        print(f"\n{'='*100}")
        print(f"🎉 MAXIMUM ASSAULT COMPLETE - GPU DEVASTATION ACHIEVED! 🎉")
        print(f"{'='*100}")
        print(f"📊 TOTAL DEVASTATION METRICS:")
        print(f"   Total Assault Time: {total_assault_time:.2f} seconds")
        print(f"   Total Images Processed: {total_images_processed}")
        print(f"   Total Texts Processed: {total_texts_processed}")
        print(f"   Average Images/Second: {total_images_processed/total_assault_time:.2f}")
        print(f"   Average Texts/Second: {total_texts_processed/total_assault_time:.2f}")
        print(f"\n🔥 PEAK GPU DEVASTATION:")
        print(f"   Peak GPU Utilization: {peak_gpu_util}%")
        print(f"   Peak Memory Usage: {peak_memory} MB")
        print(f"   Peak Temperature: {peak_temp}°C")
        print(f"   Peak Power Draw: {peak_power}W")
        
        # Final service status
        try:
            async with session.get("http://localhost:8002/clip/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"\n✅ CLIP POST-ASSAULT STATUS:")
                    print(f"   Total requests processed: {status['requests_processed']}")
                    print(f"   Final VRAM usage: {status['vram_used_gb']:.2f} GB")
        except:
            pass
        
        print(f"\n{'='*100}")
        print(f"🚀 YOUR RTX 4090 IS AN ABSOLUTE FUCKING MONSTER! 🚀")
        print(f"{'='*100}")


if __name__ == "__main__":
    asyncio.run(main())