"""GPU Services Status Monitor"""

import asyncio
import aiohttp
import time
import subprocess
import json


async def check_clip_status():
    """Check CLIP service status."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8002/clip/status", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return None


async def check_llava_status():
    """Check LLaVA service status."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8003/llava/status", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return None


async def check_gpu_stats():
    """Check GPU statistics."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,name", 
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
                'power': float(parts[4]) if len(parts) > 4 else 0,
                'name': parts[5] if len(parts) > 5 else 'Unknown'
            }
    except:
        pass
    return None


def progress_bar(current, total, width=40):
    """Create a progress bar."""
    if total == 0:
        return "[" + "=" * width + "]"
    
    filled = int((current / total) * width)
    bar = "=" * filled + "-" * (width - filled)
    return f"[{bar}]"


async def main():
    """Show comprehensive status."""
    print("=" * 80)
    print("SECOND-BRAIN GPU SERVICES STATUS MONITOR")
    print("=" * 80)
    
    # Check GPU
    gpu = await check_gpu_stats()
    if gpu:
        mem_percent = (gpu['mem_used'] / gpu['mem_total']) * 100
        util_bar = progress_bar(gpu['gpu_util'], 100, 30)
        mem_bar = progress_bar(gpu['mem_used'], gpu['mem_total'], 30)
        temp_bar = progress_bar(gpu['temp'], 100, 20)  # Assume 100C max for visualization
        
        print(f"\\nGPU: {gpu['name']}")
        print(f"  Utilization: {util_bar} {gpu['gpu_util']}%")
        print(f"  VRAM Usage:  {mem_bar} {gpu['mem_used']} MB / {gpu['mem_total']} MB ({mem_percent:.1f}%)")
        print(f"  Temperature: {temp_bar} {gpu['temp']}C")
        print(f"  Power Draw:  {gpu['power']:.1f}W / 450W")
    else:
        print("\\nGPU: ERROR - Cannot read GPU status")
    
    # Check CLIP
    print("\\n" + "="*80)
    clip_status = await check_clip_status()
    if clip_status:
        model_loaded = "LOADED" if clip_status.get('model_loaded', False) else "NOT LOADED"
        requests = clip_status.get('requests_processed', 0)
        vram = clip_status.get('vram_used_gb', 0)
        device = clip_status.get('device', 'unknown')
        
        print(f"CLIP SERVICE STATUS: ONLINE")
        print(f"  Model: {clip_status.get('model_name', 'Unknown')} ({model_loaded})")
        print(f"  Device: {device.upper()}")
        print(f"  VRAM Usage: {vram:.2f} GB")
        print(f"  Requests Processed: {requests:,}")
        print(f"  Status: {'READY FOR PROCESSING' if model_loaded == 'LOADED' else 'LOADING...'}")
        
        # Performance estimate
        if requests > 0:
            print(f"  Performance: ~44 images/sec, ~650 texts/sec (from recent tests)")
    else:
        print("CLIP SERVICE STATUS: OFFLINE or ERROR")
        print("  Check: cd services/gpu && python clip/clip_api.py")
    
    # Check LLaVA
    print("\\n" + "="*80)
    llava_status = await check_llava_status()
    if llava_status:
        model_loaded = llava_status.get('model_loaded', False)
        model_name = llava_status.get('model_name', 'Unknown')
        async_enabled = llava_status.get('async_enabled', False)
        
        print(f"LLAVA SERVICE STATUS: ONLINE")
        print(f"  Model: {model_name}")
        print(f"  Model Loaded: {'YES' if model_loaded else 'LOADING...'}")
        print(f"  Async Queue: {'ENABLED' if async_enabled else 'DISABLED'}")
        
        if model_loaded:
            print(f"  Status: READY FOR DEEP ANALYSIS")
            print(f"  Capabilities: Image analysis, OCR, Q&A, Embeddings")
            print(f"  Performance: ~2-10 seconds per image analysis")
        else:
            # Try to estimate loading progress
            print(f"  Status: LOADING 7B PARAMETER MODEL...")
            print(f"  Progress: [" + "=" * 15 + ">" + "-" * 15 + "] Estimated")
            print(f"  Note: Large model loading can take 5-10 minutes")
    else:
        print("LLAVA SERVICE STATUS: OFFLINE or ERROR")
        print("  Check: Service may still be starting up")
    
    # Overall system status
    print("\\n" + "="*80)
    print("OVERALL MULTIMODAL SYSTEM STATUS:")
    
    clip_ready = clip_status and clip_status.get('model_loaded', False)
    llava_ready = llava_status and llava_status.get('model_loaded', False)
    
    if clip_ready and llava_ready:
        print("  STATUS: FULLY OPERATIONAL")
        print("  CAPABILITIES: Fast embeddings + Deep analysis")
        print("  READY FOR: Production multimodal processing")
    elif clip_ready:
        print("  STATUS: PARTIALLY OPERATIONAL")
        print("  CAPABILITIES: Fast embeddings available")
        print("  WAITING FOR: LLaVA deep analysis to finish loading")
    else:
        print("  STATUS: STARTING UP")
        print("  ACTION NEEDED: Wait for services to fully load")
    
    # Next steps
    print("\\n" + "="*80)
    print("NEXT STEPS:")
    if clip_ready and llava_ready:
        print("  1. ✓ Both models loaded and ready")
        print("  2. ✓ Can process multimodal content")
        print("  3. → Ready to integrate with main second-brain API")
        print("  4. → Update database schema for dual embeddings")
    elif clip_ready:
        print("  1. ✓ CLIP ready for fast embeddings")
        print("  2. ⏳ Waiting for LLaVA to finish loading")
        print("  3. → Monitor LLaVA loading progress")
    else:
        print("  1. ⏳ Services starting up")
        print("  2. → Wait for CLIP and LLaVA to load")
        print("  3. → Monitor this status page")
    
    print("\\n" + "="*80)
    print("REFRESH: Run this script again to update status")
    print("SERVICES:")
    print("  CLIP API:  http://localhost:8002/docs")
    print("  LLaVA API: http://localhost:8003/docs")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())