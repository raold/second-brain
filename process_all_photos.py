"""
Process ALL Google Takeout photos
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
                    print("   Start it with: cd services/gpu/clip && python clip_api.py")
                    return
                status = await response.json()
                print(f"✅ CLIP service ready: {status}")
        
        # Process ALL zip files
        print("\n🚀 Processing ALL Google Takeout archives")
        print("="*50)
        await processor.process_all_zips()
            
    finally:
        await processor.close()

if __name__ == "__main__":
    print("="*50)
    print("PHOTO PROCESSOR - FULL ARCHIVE MODE")
    print("="*50)
    print("This will process ALL your Google Takeout zip files")
    print("Estimated: 32 zip files × ~2000 photos each = 64,000 photos")
    print()
    print("🚀 Starting automatic processing...")
    asyncio.run(run())