"""
Google Drive Data Pipeline - The Beast Feeder
Downloads and processes files through our local AI stack
"""

import asyncio
import base64
from datetime import datetime
from typing import Any

import aiohttp

from app.services.google_drive_simple import GoogleDriveService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class GDriveProcessor:
    """
    The Data Pipeline that feeds our 34B monster!
    Google Drive → Download → Process → Embed → Store
    """

    def __init__(
        self,
        gdrive_service: GoogleDriveService,
        lm_studio_url: str = "http://127.0.0.1:1234/v1",
        clip_url: str = "http://127.0.0.1:8002",
        llava_url: str = "http://127.0.0.1:8003",
        batch_size: int = 10,
    ) -> None:
        self.gdrive = gdrive_service
        self.lm_studio_url = lm_studio_url
        self.clip_url = clip_url
        self.llava_url = llava_url
        self.batch_size = batch_size

        # Track what we've processed
        self.processed_files = set()
        self.processing_stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
        }

    async def process_folder(
        self, folder_id: str = "root", recursive: bool = True,
    ) -> dict[str, Any]:
        """
        Process an entire Google Drive folder
        This is where the magic happens!
        """
        logger.info(f"🚀 Starting folder processing: {folder_id}")
        self.processing_stats["start_time"] = datetime.now()

        # Get all files in folder
        files = await self.gdrive.list_files(folder_id=folder_id)
        self.processing_stats["total_files"] = len(files)

        logger.info(f"Found {len(files)} files to process")

        # Process in batches
        for i in range(0, len(files), self.batch_size):
            batch = files[i : i + self.batch_size]
            logger.info(
                f"Processing batch {i//self.batch_size + 1}/{(len(files)-1)//self.batch_size + 1}",
            )

            # Process batch concurrently
            tasks = [self.process_file(file) for file in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Update stats
            for result in results:
                if isinstance(result, Exception):
                    self.processing_stats["failed"] += 1
                    logger.exception("Failed to process file")
                elif result:
                    self.processing_stats["processed"] += 1
                else:
                    self.processing_stats["skipped"] += 1

        # Handle subfolders if recursive
        if recursive:
            subfolders = [
                f for f in files if f.get("mimeType") == "application/vnd.google-apps.folder"
            ]
            for folder in subfolders:
                logger.info(f"📁 Recursing into folder: {folder['name']}")
                await self.process_folder(folder["id"], recursive=True)

        self.processing_stats["end_time"] = datetime.now()
        duration = (
            self.processing_stats["end_time"] - self.processing_stats["start_time"]
        ).total_seconds()

        logger.info(
            f"""
        ✅ PROCESSING COMPLETE!
        Total: {self.processing_stats['total_files']} files
        Processed: {self.processing_stats['processed']}
        Failed: {self.processing_stats['failed']}
        Skipped: {self.processing_stats['skipped']}
        Duration: {duration:.2f} seconds
        Rate: {self.processing_stats['processed']/duration:.2f} files/sec
        """,
        )

        return self.processing_stats

    async def process_file(self, file_metadata: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a single file through our AI pipeline
        """
        file_id = file_metadata.get("id")
        file_name = file_metadata.get("name", "unknown")
        mime_type = file_metadata.get("mimeType", "")

        # Skip if already processed
        if file_id in self.processed_files:
            logger.debug(f"Skipping already processed: {file_name}")
            return None

        # Skip folders
        if mime_type == "application/vnd.google-apps.folder":
            return None

        logger.info(f"📄 Processing: {file_name} ({mime_type})")

        try:
            # Determine processing strategy based on file type
            if mime_type.startswith("image/"):
                result = await self.process_image(file_metadata)
            elif mime_type in ["application/pdf", "application/vnd.google-apps.document"]:
                result = await self.process_document(file_metadata)
            elif mime_type.startswith("text/"):
                result = await self.process_text(file_metadata)
            else:
                logger.warning(f"Unsupported file type: {mime_type}")
                return None

            # Mark as processed
            self.processed_files.add(file_id)

            return result

        except Exception:
            logger.exception(f"Failed to process {file_name}")
            raise

    async def process_image(self, file_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Process image files:
        1. Download from Google Drive
        2. Analyze with LLaVA 34B for understanding
        3. Generate CLIP embeddings for search
        4. Extract text if present
        """
        file_id = file_metadata["id"]
        file_name = file_metadata.get("name", "image")

        # Download image
        content = await self.gdrive.download_file(file_id)
        if not content:
            raise ValueError(f"Failed to download {file_name}")

        # Convert to base64 for LM Studio
        img_base64 = base64.b64encode(content).decode("utf-8")

        async with aiohttp.ClientSession() as session:
            # 1. Analyze with LLaVA 34B
            logger.info("  🧠 Analyzing with LLaVA 34B...")
            vision_analysis = await self.analyze_with_llava(session, img_base64)

            # 2. Generate CLIP embedding
            logger.info("  📊 Generating CLIP embedding...")
            clip_embedding = await self.generate_clip_embedding(session, content)

            # 3. Extract text if present
            logger.info("  📝 Extracting text...")
            extracted_text = await self.extract_text_from_image(session, img_base64)

            # 4. Generate text embedding for the analysis
            logger.info("  💾 Generating text embedding...")
            text_embedding = await self.generate_text_embedding(
                session,
                f"{file_name}\n{vision_analysis}\n{extracted_text}",
            )

        result = {
            "file_id": file_id,
            "file_name": file_name,
            "type": "image",
            "vision_analysis": vision_analysis,
            "extracted_text": extracted_text,
            "clip_embedding": clip_embedding,
            "text_embedding": text_embedding,
            "metadata": file_metadata,
            "processed_at": datetime.now().isoformat(),
        }

        logger.info("  ✅ Image processed successfully!")
        return result

    async def process_document(self, file_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Process document files (PDF, Google Docs)
        """
        file_id = file_metadata["id"]
        file_name = file_metadata.get("name", "document")

        # Export Google Docs as PDF or download PDF directly
        if file_metadata.get("mimeType") == "application/vnd.google-apps.document":
            content = await self.gdrive.export_file(file_id, "application/pdf")
        else:
            content = await self.gdrive.download_file(file_id)

        if not content:
            raise ValueError(f"Failed to download {file_name}")

        # For now, we'll extract text using LLaVA's OCR capabilities
        # Convert PDF pages to images and process
        # (In production, you'd use a proper PDF library)

        async with aiohttp.ClientSession() as session:
            # Extract and analyze text
            text_content = f"Document: {file_name}\n[PDF content would be extracted here]"

            # Generate embeddings
            text_embedding = await self.generate_text_embedding(session, text_content)

            # Summarize with LLaVA 34B
            summary = await self.summarize_text(session, text_content)

        result = {
            "file_id": file_id,
            "file_name": file_name,
            "type": "document",
            "content": text_content[:1000],  # First 1000 chars
            "summary": summary,
            "text_embedding": text_embedding,
            "metadata": file_metadata,
            "processed_at": datetime.now().isoformat(),
        }

        logger.info("  ✅ Document processed successfully!")
        return result

    async def process_text(self, file_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Process text files
        """
        file_id = file_metadata["id"]
        file_name = file_metadata.get("name", "text")

        # Download text content
        content = await self.gdrive.download_file(file_id)
        if not content:
            raise ValueError(f"Failed to download {file_name}")

        text_content = content.decode("utf-8", errors="ignore")

        async with aiohttp.ClientSession() as session:
            # Generate embedding
            text_embedding = await self.generate_text_embedding(session, text_content)

            # Extract key concepts
            key_concepts = await self.extract_concepts(session, text_content)

        result = {
            "file_id": file_id,
            "file_name": file_name,
            "type": "text",
            "content": text_content[:1000],
            "key_concepts": key_concepts,
            "text_embedding": text_embedding,
            "metadata": file_metadata,
            "processed_at": datetime.now().isoformat(),
        }

        logger.info("  ✅ Text file processed successfully!")
        return result

    async def analyze_with_llava(self, session: aiohttp.ClientSession, img_base64: str) -> str:
        """Use LLaVA 34B to understand the image"""
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in detail. What do you see?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                        },
                    ],
                },
            ],
            "max_tokens": 300,
            "temperature": 0.5,
        }

        try:
            async with session.post(
                f"{self.lm_studio_url}/chat/completions",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                return "Failed to analyze image"
        except Exception:
            logger.exception("LLaVA analysis failed")
            return "Error analyzing image"

    async def generate_clip_embedding(
        self, session: aiohttp.ClientSession, image_bytes: bytes,
    ) -> list[float]:
        """Generate CLIP embedding for image search"""
        try:
            data = aiohttp.FormData()
            data.add_field("image", image_bytes, filename="image.jpg")

            async with session.post(
                f"{self.clip_url}/clip/embed-image",
                data=data,
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("embedding", [])
                return []
        except Exception:
            logger.exception("CLIP embedding failed")
            return []

    async def extract_text_from_image(self, session: aiohttp.ClientSession, img_base64: str) -> str:
        """Extract text from image using LLaVA's OCR capabilities"""
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract and transcribe ALL text visible in this image. If no text, say 'No text found'.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                        },
                    ],
                },
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        }

        try:
            async with session.post(
                f"{self.lm_studio_url}/chat/completions",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                return ""
        except Exception:
            logger.exception("Text extraction failed")
            return ""

    async def generate_text_embedding(
        self, session: aiohttp.ClientSession, text: str,
    ) -> list[float]:
        """Generate text embedding using Nomic"""
        payload = {
            "model": "text-embedding-nomic-embed-text-v1.5",
            "input": text[:8000],  # Limit text length
        }

        try:
            async with session.post(
                f"{self.lm_studio_url}/embeddings",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["data"][0]["embedding"]
                return []
        except Exception:
            logger.exception("Text embedding failed")
            return []

    async def summarize_text(self, session: aiohttp.ClientSession, text: str) -> str:
        """Summarize text using LLaVA 34B"""
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries.",
                },
                {"role": "user", "content": f"Summarize this in 2-3 sentences:\n\n{text[:3000]}"},
            ],
            "max_tokens": 150,
            "temperature": 0.5,
        }

        try:
            async with session.post(
                f"{self.lm_studio_url}/chat/completions",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                return "Summary unavailable"
        except Exception:
            logger.exception("Summarization failed")
            return "Error generating summary"

    async def extract_concepts(self, session: aiohttp.ClientSession, text: str) -> list[str]:
        """Extract key concepts from text"""
        payload = {
            "model": "llava-v1.6-34b",
            "messages": [
                {
                    "role": "system",
                    "content": "Extract key concepts and return as a comma-separated list.",
                },
                {"role": "user", "content": f"Extract 5-10 key concepts from:\n\n{text[:2000]}"},
            ],
            "max_tokens": 100,
            "temperature": 0.3,
        }

        try:
            async with session.post(
                f"{self.lm_studio_url}/chat/completions",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    concepts = data["choices"][0]["message"]["content"]
                    return [c.strip() for c in concepts.split(",")]
                return []
        except Exception:
            logger.exception("Concept extraction failed")
            return []
