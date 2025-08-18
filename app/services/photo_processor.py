"""
Process Google Photos Takeout Export
Extracts images from zip files, generates embeddings, and stores in PostgreSQL
"""

import asyncio
import io
import os
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
import base64
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import aiohttp
import asyncpg
from PIL import Image

# HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False
    print("⚠️ HEIC support not available. Install pillow-heif for HEIC processing.")

# Configuration - Use centralized config
import builtins
import contextlib

from app.core.service_config import config

# Get all configuration from central source
# Use Windows path if available, otherwise Docker mount
if os.path.exists("G:/My Drive/Takeout"):
    TAKEOUT_PATH = "G:/My Drive/Takeout"
else:
    TAKEOUT_PATH = config.TAKEOUT_PATH
CLIP_SERVICE_URL = config.get_clip_url()
LLAVA_SERVICE_URL = config.get_llava_url()
DATABASE_URL = config.get_database_url()
BATCH_SIZE = config.PHOTO_BATCH_SIZE

# Include HEIC/HEIF if support is available
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
if HEIC_SUPPORT:
    SUPPORTED_FORMATS.update({".heic", ".heif"})
    print("✅ HEIC support enabled")


class GooglePhotosProcessor:
    """Process Google Photos from Takeout export"""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.pipeline_manager = None  # Optional reference for real-time updates

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        # Ensure table exists with image-specific columns
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    content TEXT,
                    embedding vector(768),  -- CLIP uses 768 dimensions
                    metadata JSONB DEFAULT '{}',
                    image_metadata JSONB DEFAULT '{}',
                    ai_description TEXT,  -- LLaVA analysis
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(file_path)
                )
            """)

            # Add ai_description column if it doesn't exist (for existing tables)
            await conn.execute("""
                ALTER TABLE photo_memories
                ADD COLUMN IF NOT EXISTS ai_description TEXT
            """)

            # Create index for vector similarity search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS photo_memories_embedding_idx
                ON photo_memories USING hnsw (embedding vector_cosine_ops)
            """)

        print("✅ Database initialized")

    async def close(self) -> None:
        """Close database connections"""
        if self.pool:
            await self.pool.close()

    async def extract_and_process_zip(self, zip_path: Path) -> int:
        """Extract and process images from a single zip file"""
        processed = 0

        # Try py7zr first for better compatibility with large/split archives
        try:
            import py7zr
            print(f"🔧 Attempting to open with py7zr: {zip_path.name}")
            with py7zr.SevenZipFile(zip_path, mode='r') as zf:
                # Get all files
                all_files = zf.getnames()
                print(f"📂 Found {len(all_files)} files in archive")
                
                # Filter for image files
                image_files = [
                    name for name in all_files
                    if Path(name).suffix.lower() in SUPPORTED_FORMATS
                ]
                print(f"🖼️ Found {len(image_files)} image files")
                
                # For now, just return to test
                return len(image_files)
        except Exception as e:
            print(f"⚠️ py7zr failed: {e}, trying standard zipfile...")
        
        # Fallback to standard zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Get all image files
            image_files = [
                name for name in zf.namelist()
                if Path(name).suffix.lower() in SUPPORTED_FORMATS
            ]

            print(f"📦 Processing {zip_path.name}: {len(image_files)} images")

            # Process in batches
            for i in range(0, len(image_files), BATCH_SIZE):
                batch = image_files[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(image_files) + BATCH_SIZE - 1) // BATCH_SIZE
                
                print(f"  Batch {batch_num}/{total_batches}: Processing {len(batch)} images...")

                tasks = []
                for file_name in batch:
                    try:
                        # Extract image data
                        image_data = zf.read(file_name)

                        # Get JSON metadata if exists
                        json_name = file_name + ".json"
                        metadata = {}
                        if json_name in zf.namelist():
                            with contextlib.suppress(builtins.BaseException):
                                metadata = json.loads(zf.read(json_name))

                        tasks.append(self.process_image(
                            image_data,
                            file_name,
                            metadata,
                            str(zip_path),
                        ))
                    except Exception as e:
                        print(f"❌ Failed to read {file_name}: {e}")
                        self.failed_count += 1

                # Process batch
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"❌ Processing failed: {result}")
                            self.failed_count += 1
                        else:
                            processed += 1
                            self.processed_count += 1

                print(f"  Batch {batch_num}: {self.processed_count} total processed, {processed}/{len(image_files)} from this zip")
                
                # Send real-time update if pipeline manager is available
                if self.pipeline_manager:
                    self.pipeline_manager.metrics["processed_files"] = self.processed_count
                    self.pipeline_manager.metrics["failed_files"] = self.failed_count
                    self.pipeline_manager.calculate_performance_metrics()
                    await self.pipeline_manager.broadcast_update({
                        "type": "metrics",
                        "metrics": self.pipeline_manager.metrics,
                    })

        return processed

    async def process_image(
        self,
        image_data: bytes,
        file_name: str,
        google_metadata: dict[str, Any],
        source_zip: str,
    ) -> bool:
        """Process a single image: generate embedding and store in database"""

        try:
            # Skip tiny files (likely corrupted)
            if len(image_data) < 100:
                print(f"  ⏭️  Skipping {file_name} (too small, likely corrupted)")
                return False
                
            # Check if already processed
            async with self.pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT 1 FROM photo_memories WHERE file_path = $1",
                    f"{source_zip}/{file_name}",
                )
                if exists:
                    print(f"  ⏭️  Skipping {file_name} (already processed)")
                    return True

            # Convert HEIC to JPEG if needed
            if Path(file_name).suffix.lower() in {".heic", ".heif"}:
                print(f"  🔄 Converting HEIC: {file_name}")
                image_data = self.convert_heic_to_jpeg(image_data)

            # Generate CLIP embedding
            embedding = await self.generate_clip_embedding(image_data)

            if not embedding:
                print(f"  ❌ Failed to generate embedding for {file_name}")
                return False

            # Analyze with LLaVA for rich description (sample 10% or first 100 images)
            llava_description = ""
            if self.processed_count < 100 or self.processed_count % 10 == 0:
                print(f"  🧠 Analyzing with LLaVA: {file_name}")
                llava_description = await self.analyze_with_llava(image_data, file_name)

            # Extract image metadata
            image_metadata = self.extract_image_metadata(image_data)

            # Prepare content description with LLaVA analysis
            content = self.create_content_description(
                file_name,
                google_metadata,
                image_metadata,
                llava_description,
            )

            # Store in database - convert list to pgvector format
            async with self.pool.acquire() as conn:
                # Convert list to pgvector string format: '[0.1, 0.2, ...]'
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                await conn.execute("""
                    INSERT INTO photo_memories
                    (file_path, file_name, content, embedding, metadata, image_metadata, ai_description)
                    VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
                    ON CONFLICT (file_path) DO UPDATE
                    SET embedding = $4::vector,
                        metadata = $5,
                        image_metadata = $6,
                        ai_description = $7,
                        updated_at = NOW()
                """,
                f"{source_zip}/{file_name}",
                file_name,
                content,
                embedding_str,
                json.dumps(google_metadata),
                json.dumps(image_metadata),
                llava_description,
                )

            print(f"  ✅ Processed {file_name}")
            return True

        except Exception as e:
            print(f"  ❌ Error processing {file_name}: {e}")
            return False

    def convert_heic_to_jpeg(self, image_data: bytes) -> bytes:
        """Convert HEIC image to JPEG format"""
        try:
            # Open HEIC image
            img = Image.open(BytesIO(image_data))

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Save as JPEG
            output = BytesIO()
            img.save(output, format="JPEG", quality=95)
            return output.getvalue()
        except Exception as e:
            print(f"Failed to convert HEIC: {e}")
            return image_data  # Return original if conversion fails

    async def analyze_with_llava(self, image_data: bytes, file_name: str) -> str:
        """Use LLaVA to understand and describe the image"""
        try:
            # Convert image to base64
            img_base64 = base64.b64encode(image_data).decode("utf-8")

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                payload = {
                    "model": "llava-v1.6-34b",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this image in detail. Include: what's in the image, people (if any), location/setting, mood/atmosphere, and any text visible.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_base64}",
                                    },
                                },
                            ],
                        },
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300,
                }

                async with session.post(
                    f"{LLAVA_SERVICE_URL}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    error = await response.text()
                    print(f"LLaVA error for {file_name}: {error}")
                    return ""

        except Exception as e:
            print(f"Failed to analyze with LLaVA: {e}")
            return ""

    async def generate_clip_embedding(self, image_data: bytes) -> list[float] | None:
        """Generate CLIP embedding for an image"""
        try:
            async with aiohttp.ClientSession() as session:
                # Create multipart form data
                data = aiohttp.FormData()
                data.add_field("file",
                              image_data,
                              filename="image.jpg",
                              content_type="image/jpeg")

                async with session.post(
                    f"{CLIP_SERVICE_URL}/clip/embed/image",
                    data=data,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["embeddings"][0]
                    error = await response.text()
                    print(f"CLIP service error: {error}")
                    return None

        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            return None

    def extract_image_metadata(self, image_data: bytes) -> dict[str, Any]:
        """Extract metadata from image file"""
        try:
            img = Image.open(BytesIO(image_data))
            metadata = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
            }

            # Extract EXIF data if available
            if hasattr(img, "_getexif") and img._getexif():
                exif = img._getexif()
                if exif:
                    metadata["has_exif"] = True
                    # Add specific EXIF tags if needed

            return metadata
        except Exception as e:
            print(f"Failed to extract image metadata: {e}")
            return {}

    def create_content_description(
        self,
        file_name: str,
        google_metadata: dict[str, Any],
        image_metadata: dict[str, Any],
        llava_description: str = "",
    ) -> str:
        """Create searchable text content from metadata and AI analysis"""
        parts = [f"Photo: {file_name}"]

        # Add LLaVA AI description if available
        if llava_description:
            parts.append(f"AI Description: {llava_description}")

        # Add Google Photos metadata
        if google_metadata:
            if "title" in google_metadata:
                parts.append(f"Title: {google_metadata['title']}")
            if "description" in google_metadata:
                parts.append(f"Description: {google_metadata['description']}")
            if "creationTime" in google_metadata:
                parts.append(f"Taken: {google_metadata['creationTime'].get('formatted', '')}")
            if "geoData" in google_metadata:
                geo = google_metadata["geoData"]
                if "latitude" in geo and "longitude" in geo:
                    parts.append(f"Location: {geo.get('latitude')}, {geo.get('longitude')}")

        # Add image properties
        if image_metadata and "width" in image_metadata and "height" in image_metadata:
            parts.append(f"Size: {image_metadata['width']}x{image_metadata['height']}")

        return "\n".join(parts)

    async def process_all_zips(self) -> None:
        """Process all zip files in the Takeout directory"""
        takeout_dir = Path(TAKEOUT_PATH)
        # Skip the first archive_browser zip, process numbered ones with actual photos
        zip_files = sorted([f for f in takeout_dir.glob("*.zip") if "-1-" in f.name or f.name.endswith("-032.zip")])

        print(f"📂 Found {len(zip_files)} zip files to process")

        for zip_file in zip_files:
            print(f"\n🔄 Processing {zip_file.name}...")
            try:
                processed = await self.extract_and_process_zip(zip_file)
                print(f"✅ Completed {zip_file.name}: {processed} images")
            except Exception as e:
                print(f"❌ Failed to process {zip_file.name}: {e}")

        print(f"""

        ========================================
        📊 PROCESSING COMPLETE
        ========================================
        Total processed: {self.processed_count}
        Failed: {self.failed_count}
        Success rate: {(self.processed_count/(self.processed_count+self.failed_count)*100):.1f}%
        """)

    async def test_with_single_zip(self) -> None:
        """Test with just the first zip file"""
        takeout_dir = Path(TAKEOUT_PATH)
        # Get first numbered zip with actual photos
        zip_files = sorted([f for f in takeout_dir.glob("*.zip") if "-1-" in f.name])

        if zip_files:
            print(f"🧪 Testing with {zip_files[0].name}")
            processed = await self.extract_and_process_zip(zip_files[0])
            print(f"✅ Test complete: {processed} images processed")
        else:
            print("❌ No zip files found")


async def main() -> None:
    """Main entry point"""
    processor = GooglePhotosProcessor()

    try:
        # Initialize
        await processor.initialize()

        # Check CLIP service
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{CLIP_SERVICE_URL}/") as response:
                    if response.status != 200:
                        print("❌ CLIP service not available. Please start it first:")
                        print("   cd services/gpu/clip")
                        print("   python clip_api.py")
                        return
                    status = await response.json()
                    print(f"✅ CLIP service ready: {status}")
            except Exception:
                print("❌ CLIP service not available at port 8002")
                print("   Please start CLIP service:")
                print("   cd services/gpu/clip")
                print("   python clip_api.py")
                return

        # Ask user for mode
        print("\nSelect mode:")
        print("1. Test with first zip file only")
        print("2. Process all zip files")
        choice = input("Enter choice (1 or 2): ").strip()

        if choice == "1":
            await processor.test_with_single_zip()
        else:
            await processor.process_all_zips()

    finally:
        await processor.close()


if __name__ == "__main__":
    asyncio.run(main())
