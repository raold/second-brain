"""
Quick test to process photos with LLaVA only
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import asyncio
import zipfile
from pathlib import Path
import aiohttp
import base64
from PIL import Image
from io import BytesIO

TAKEOUT_PATH = "G:/My Drive/Takeout"
LLAVA_SERVICE_URL = "http://127.0.0.1:1234"

async def process_image_with_llava(image_bytes):
    """Send image to LLaVA for analysis"""
    try:
        # Convert to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        async with aiohttp.ClientSession() as session:
            # Call LLaVA API
            payload = {
                "model": "llava-v1.6-mistral-7b",
                "prompt": "Describe this image in detail. What do you see?",
                "images": [base64_image],
                "stream": False
            }
            
            async with session.post(f"{LLAVA_SERVICE_URL}/v1/chat/completions", 
                                   json={"messages": [{"role": "user", "content": "Describe this image"}],
                                         "model": "llava-v1.6-mistral-7b"}) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("message", {}).get("content", "No description")
                else:
                    return f"LLaVA error: {response.status}"
    except Exception as e:
        return f"Error: {str(e)}"

async def test_pipeline():
    """Test the photo pipeline"""
    print("🚀 Starting photo pipeline test")
    print(f"📁 Looking in: {TAKEOUT_PATH}")
    
    takeout_dir = Path(TAKEOUT_PATH)
    # Skip archive_browser, get numbered zips with actual photos
    zip_files = sorted([f for f in takeout_dir.glob("*.zip") 
                       if '-1-' in f.name])[:1]  # Just process first photo zip
    
    print(f"📦 Found {len(zip_files)} zip files")
    
    if not zip_files:
        print("❌ No zip files found!")
        return
    
    zip_file = zip_files[0]
    print(f"📂 Processing: {zip_file.name}")
    
    processed = 0
    with zipfile.ZipFile(zip_file, 'r') as zf:
        # Get all image files
        image_files = [f for f in zf.namelist() 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:5]  # Just 5 images
        
        print(f"🖼️ Found {len(image_files)} images (processing first 5)")
        
        for img_file in image_files:
            try:
                print(f"  Processing: {img_file}")
                
                # Extract image
                img_data = zf.read(img_file)
                
                # Open with PIL to verify it's valid
                img = Image.open(BytesIO(img_data))
                print(f"    Size: {img.size}, Mode: {img.mode}")
                
                # Send to LLaVA
                description = await process_image_with_llava(img_data)
                print(f"    LLaVA says: {description[:100]}...")
                
                processed += 1
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    print(f"✅ Processed {processed} images successfully!")

if __name__ == "__main__":
    asyncio.run(test_pipeline())