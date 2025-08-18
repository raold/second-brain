"""
Direct runner for photo processor - bypasses input prompt
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.photo_processor import GooglePhotosProcessor
import aiohttp

CLIP_SERVICE_URL = "http://localhost:8002"

async def run():
    processor = GooglePhotosProcessor()
    
    try:
        # Initialize
        await processor.initialize()
        
        # Check CLIP service
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CLIP_SERVICE_URL}/") as response:
                if response.status != 200:
                    print("❌ CLIP service not available at port 8002")
                    return
                status = await response.json()
                print(f"✅ CLIP service ready: {status}")
        
        # Run test mode automatically
        print("\n🚀 Starting photo processing (test mode - first zip only)")
        await processor.test_with_single_zip()
            
    finally:
        await processor.close()

if __name__ == "__main__":
    print("="*50)
    print("PHOTO PROCESSOR - DIRECT EXECUTION")
    print("="*50)
    asyncio.run(run())