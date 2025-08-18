"""
Photo Pipeline Routes
Provides web interface for monitoring and controlling photo processing
"""

import asyncio
import json
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.services.photo_processor import GooglePhotosProcessor

router = APIRouter(prefix="/photo-pipeline", tags=["photo-pipeline"])

class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class PipelineManager:
    """Manages the photo processing pipeline with control capabilities"""

    def __init__(self) -> None:
        self.processor: GooglePhotosProcessor | None = None
        self.status = PipelineStatus.IDLE
        self.current_task: asyncio.Task | None = None
        self.websockets: list[WebSocket] = []
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Start unpaused

        # Metrics
        self.metrics = {
            "start_time": None,
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "current_zip": "",
            "current_file": "",
            "processing_rate": 0.0,
            "avg_time_per_image": 0.0,
            "estimated_time_remaining": 0,
            "heic_converted": 0,
            "llava_analyzed": 0,
            "total_zip_files": 0,
            "processed_zips": 0,
            "errors": [],
        }

        # Performance tracking
        self.performance_history = []
        self.last_update_time = time.time()
        self.last_processed_count = 0

    async def broadcast_update(self, data: dict) -> None:
        """Send update to all connected websockets"""
        message = json.dumps(data)
        disconnected = []

        for websocket in self.websockets:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)

        # Remove disconnected websockets
        for ws in disconnected:
            if ws in self.websockets:
                self.websockets.remove(ws)

    def calculate_performance_metrics(self) -> None:
        """Calculate real-time performance metrics"""
        current_time = time.time()
        time_delta = current_time - self.last_update_time

        if time_delta > 0:
            processed_delta = self.metrics["processed_files"] - self.last_processed_count
            self.metrics["processing_rate"] = processed_delta / time_delta

            if self.metrics["processed_files"] > 0:
                total_time = current_time - self.metrics["start_time"]
                self.metrics["avg_time_per_image"] = total_time / self.metrics["processed_files"]

                remaining_files = self.metrics["total_files"] - self.metrics["processed_files"]
                if self.metrics["processing_rate"] > 0:
                    self.metrics["estimated_time_remaining"] = remaining_files / self.metrics["processing_rate"]

        self.last_update_time = current_time
        self.last_processed_count = self.metrics["processed_files"]

        # Track performance history
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "processing_rate": self.metrics["processing_rate"],
            "total_processed": self.metrics["processed_files"],
        })

        # Keep only last 100 data points
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

    async def start_processing(self) -> None:
        """Start or resume processing"""
        if self.status == PipelineStatus.PAUSED:
            self.status = PipelineStatus.RUNNING
            self.pause_event.set()
            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing resumed",
            })
        elif self.status == PipelineStatus.IDLE:
            # Initialize processor if not already done
            if not self.processor:
                try:
                    print("🔧 Initializing GooglePhotosProcessor...")
                    self.processor = GooglePhotosProcessor()
                    await self.processor.initialize()
                    # Pass pipeline manager reference for updates
                    self.processor.pipeline_manager = self
                    print("✅ GooglePhotosProcessor initialized successfully")
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to initialize processor: {e}")
                    print(f"Traceback: {traceback.format_exc()}")
                    raise

            # Start processing in background task
            self.status = PipelineStatus.RUNNING
            self.metrics["start_time"] = time.time()
            self.current_task = asyncio.create_task(self._run_processing())

            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing started",
            })

    async def pause_processing(self) -> None:
        """Pause processing"""
        if self.status == PipelineStatus.RUNNING:
            self.status = PipelineStatus.PAUSED
            self.pause_event.clear()
            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing paused",
            })

    async def _run_processing(self) -> None:
        """Run the actual processing logic"""
        try:
            # Get all zip files to process
            # Check if running in Docker or locally
            if os.path.exists("/takeout_local") and list(Path("/takeout_local").glob("*.zip")):
                takeout_path = Path("/takeout_local")  # Docker local copy
                print(f"📁 Using Docker local copy: {takeout_path}")
            elif os.path.exists("/takeout") and list(Path("/takeout").glob("*.zip")):
                takeout_path = Path("/takeout")  # Docker mount
                print(f"📁 Using Docker mount: {takeout_path}")
            elif os.path.exists("G:/My Drive/Takeout"):
                takeout_path = Path("G:/My Drive/Takeout")  # Windows local
                print(f"📁 Using Windows path: {takeout_path}")
            else:
                takeout_path = Path("./takeout")  # Fallback to local folder
                print(f"📁 Using fallback path: {takeout_path}")

            # Log what we're looking for
            print(f"🔍 Looking for zip files in: {takeout_path}")
            print(f"📂 Path exists: {takeout_path.exists()}")

            # Try to list all files first
            if takeout_path.exists():
                all_files = list(takeout_path.glob("*"))
                print(f"📊 Total files in directory: {len(all_files)}")
                zip_files = sorted(takeout_path.glob("*.zip"))
                print(f"📦 Total zip files found: {len(zip_files)}")
                # Process ALL zip files
                zip_files = sorted(zip_files)
                print(f"✅ Filtered zip files to process: {len(zip_files)}")
            else:
                print(f"❌ Path does not exist: {takeout_path}")
                zip_files = []

            # Better estimate based on actual zip content
            estimated_images_per_zip = 2000  # More realistic for 10GB zips
            self.metrics["total_files"] = len(zip_files) * estimated_images_per_zip
            self.metrics["total_zip_files"] = len(zip_files)
            self.metrics["current_zip"] = "Scanning for zip files..."

            await self.broadcast_update({
                "type": "metrics",
                "metrics": self.metrics,
            })

            # Process each zip file
            for zip_file in zip_files:
                if self.status != PipelineStatus.RUNNING:
                    break

                # Wait if paused
                await self.pause_event.wait()

                self.metrics["current_zip"] = zip_file.name
                await self.broadcast_update({
                    "type": "processing",
                    "current_zip": zip_file.name,
                    "metrics": self.metrics,
                })

                try:
                    # Process the zip file
                    print(f"🔄 Starting to process {zip_file.name}")
                    
                    # Create a callback to update metrics in real-time
                    async def update_progress(count: int):
                        self.metrics["processed_files"] = count
                        self.calculate_performance_metrics()
                        await self.broadcast_update({
                            "type": "metrics",
                            "metrics": self.metrics,
                        })
                    
                    # Pass the callback to the processor
                    processed = await self.processor.extract_and_process_zip(zip_file)
                    self.metrics["processed_files"] += processed
                    self.metrics["processed_zips"] += 1
                    print(f"✅ Processed {processed} files from {zip_file.name}")

                    # Final update
                    self.calculate_performance_metrics()
                    await self.broadcast_update({
                        "type": "metrics",
                        "metrics": self.metrics,
                    })

                except Exception as e:
                    import traceback
                    error_msg = f"Failed to process {zip_file.name}: {e!s}"
                    print(f"❌ {error_msg}")
                    print(f"Traceback: {traceback.format_exc()}")
                    self.metrics["failed_files"] += 1
                    await self.broadcast_update({
                        "type": "error",
                        "message": error_msg,
                        "metrics": self.metrics,
                    })

            # Processing complete
            self.status = PipelineStatus.COMPLETED
            await self.broadcast_update({
                "type": "completed",
                "status": self.status.value,
                "message": "All processing complete!",
                "metrics": self.metrics,
            })

        except asyncio.CancelledError:
            # Task was cancelled (stop was called)
            pass
        except Exception as e:
            self.status = PipelineStatus.ERROR
            await self.broadcast_update({
                "type": "error",
                "status": self.status.value,
                "message": f"Pipeline error: {e!s}",
                "metrics": self.metrics,
            })

    async def stop_processing(self) -> None:
        """Stop processing completely"""
        if self.current_task:
            self.current_task.cancel()
            self.current_task = None
        self.status = PipelineStatus.IDLE
        self.pause_event.set()  # Release any pause
        await self.broadcast_update({
            "type": "status",
            "status": self.status.value,
            "message": "Processing stopped",
        })

# Create pipeline manager instance
pipeline_manager = PipelineManager()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the photo pipeline dashboard"""
    # Fix path to work from container's /app directory
    with open("static/photo-pipeline.html") as f:
        return HTMLResponse(content=f.read())

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    pipeline_manager.websockets.append(websocket)

    # Send initial status
    await websocket.send_json({
        "type": "connected",
        "status": pipeline_manager.status.value,
        "metrics": pipeline_manager.metrics,
    })

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        if websocket in pipeline_manager.websockets:
            pipeline_manager.websockets.remove(websocket)

@router.post("/start")
async def start_pipeline():
    """Start or resume the pipeline"""
    await pipeline_manager.start_processing()
    return {"status": "started"}

@router.post("/pause")
async def pause_pipeline():
    """Pause the pipeline"""
    await pipeline_manager.pause_processing()
    return {"status": "paused"}

@router.post("/stop")
async def stop_pipeline():
    """Stop the pipeline"""
    await pipeline_manager.stop_processing()
    return {"status": "stopped"}

@router.get("/status")
async def get_status():
    """Get current pipeline status and metrics"""
    return {
        "status": pipeline_manager.status.value,
        "metrics": pipeline_manager.metrics,
        "performance_history": pipeline_manager.performance_history[-20:],
    }
