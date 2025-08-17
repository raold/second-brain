"""
Photo Pipeline Routes
Provides web interface for monitoring and controlling photo processing
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

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
    
    def __init__(self):
        self.processor: Optional[GooglePhotosProcessor] = None
        self.status = PipelineStatus.IDLE
        self.current_task: Optional[asyncio.Task] = None
        self.websockets: List[WebSocket] = []
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
            "errors": []
        }
        
        # Performance tracking
        self.performance_history = []
        self.last_update_time = time.time()
        self.last_processed_count = 0
    
    async def broadcast_update(self, data: dict):
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
    
    def calculate_performance_metrics(self):
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
            "total_processed": self.metrics["processed_files"]
        })
        
        # Keep only last 100 data points
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    async def start_processing(self):
        """Start or resume processing"""
        if self.status == PipelineStatus.PAUSED:
            self.status = PipelineStatus.RUNNING
            self.pause_event.set()
            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing resumed"
            })
        elif self.status == PipelineStatus.IDLE:
            # Processing logic would go here
            # For now, just update status
            self.status = PipelineStatus.RUNNING
            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing started"
            })
    
    async def pause_processing(self):
        """Pause processing"""
        if self.status == PipelineStatus.RUNNING:
            self.status = PipelineStatus.PAUSED
            self.pause_event.clear()
            await self.broadcast_update({
                "type": "status",
                "status": self.status.value,
                "message": "Processing paused"
            })
    
    async def stop_processing(self):
        """Stop processing completely"""
        if self.current_task:
            self.current_task.cancel()
        self.status = PipelineStatus.IDLE
        await self.broadcast_update({
            "type": "status",
            "status": self.status.value,
            "message": "Processing stopped"
        })

# Create pipeline manager instance
pipeline_manager = PipelineManager()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the photo pipeline dashboard"""
    with open("app/static/photo-pipeline.html", "r") as f:
        return HTMLResponse(content=f.read())

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    pipeline_manager.websockets.append(websocket)
    
    # Send initial status
    await websocket.send_json({
        "type": "connected",
        "status": pipeline_manager.status.value,
        "metrics": pipeline_manager.metrics
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
        "performance_history": pipeline_manager.performance_history[-20:]
    }