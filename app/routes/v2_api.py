"""
Second Brain V2 API - Single User Edition
A modern, powerful, and elegant API for single-user memory management
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.services.memory_service import MemoryService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# ========================= MODELS =========================


class MemoryBase(BaseModel):
    """Base memory model with common fields"""

    content: str = Field(..., min_length=1, max_length=50000, description="Memory content")
    memory_type: str = Field("generic", description="Type of memory")
    importance_score: float = Field(0.5, ge=0, le=1, description="Importance score")
    tags: List[str] = Field(default_factory=list, max_items=20)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryCreate(MemoryBase):
    """Memory creation request"""

    embedding_model: Optional[str] = Field(
        "text-embedding-ada-002", description="Embedding model to use"
    )
    auto_tag: bool = Field(True, description="Automatically generate tags")
    auto_importance: bool = Field(True, description="Automatically calculate importance")


class MemoryUpdate(BaseModel):
    """Memory update request - all fields optional"""

    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance_score: Optional[float] = Field(None, ge=0, le=1)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Memory(MemoryBase):
    """Complete memory model"""

    id: UUID
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    embedding: Optional[List[float]] = Field(None, exclude=True)

    model_config = ConfigDict(from_attributes=True)


class MemoryResponse(BaseModel):
    """Standard memory response"""

    success: bool
    memory: Memory
    message: Optional[str] = None


class MemoriesResponse(BaseModel):
    """Multiple memories response with pagination"""

    success: bool
    memories: List[Memory]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class SearchRequest(BaseModel):
    """Advanced search request"""

    query: str = Field(..., min_length=1, max_length=1000)
    search_type: str = Field("hybrid", pattern="^(keyword|semantic|hybrid)$")
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    include_similar: bool = True
    similarity_threshold: float = Field(0.7, ge=0, le=1)


class BulkOperation(BaseModel):
    """Bulk operation request"""

    operation: str = Field(..., pattern="^(update|delete|tag|export)$")
    memory_ids: List[UUID]
    data: Optional[Dict[str, Any]] = None


class AnalyticsQuery(BaseModel):
    """Analytics query request"""

    metric: str = Field(..., pattern="^(usage|trends|insights|relationships)$")
    time_range: str = Field("7d", pattern="^(1d|7d|30d|90d|1y|all)$")
    group_by: Optional[str] = Field(None, pattern="^(day|week|month|tag|type)$")
    filters: Dict[str, Any] = Field(default_factory=dict)


class WebSocketMessage(BaseModel):
    """WebSocket message format"""

    type: str = Field(..., pattern="^(subscribe|unsubscribe|ping|message)$")
    channel: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class WebSocketResponse(BaseModel):
    """WebSocket response format"""

    type: str
    channel: Optional[str] = None
    data: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None


# ========================= DEPENDENCIES =========================


async def get_memory_service() -> MemoryService:
    """Get memory service instance"""
    return MemoryService()


async def validate_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> Dict[str, int]:
    """Validate pagination parameters"""
    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }


# ========================= WEBSOCKET MANAGER =========================


class ConnectionManager:
    """Simple WebSocket connection manager for single user"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """Connect a WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {"connected_at": datetime.now(timezone.utc)}

        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await websocket.send_json(
            WebSocketResponse(type="connected", data={"status": "connected"}).dict()
        )

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Clean up metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: WebSocketResponse):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message.dict())
            except:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


# ========================= ROUTER =========================

router = APIRouter(
    prefix="/api/v2",
    tags=["V2 API"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        429: {"description": "Rate limit exceeded"},
    },
)


# ========================= MEMORY ENDPOINTS =========================


@router.post("/memories", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory: MemoryCreate,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Create a new memory with advanced features"""
    try:
        # Create memory (no user_id needed)
        created_memory = await memory_service.create_memory(
            content=memory.content,
            importance_score=memory.importance_score,
            tags=memory.tags,
            metadata=memory.metadata,
        )

        # Convert to Memory model
        memory_obj = Memory(
            id=UUID(created_memory["id"]),
            content=created_memory["content"],
            memory_type=created_memory["memory_type"],
            importance_score=created_memory["importance_score"],
            tags=created_memory["tags"],
            metadata=created_memory["metadata"],
            created_at=datetime.fromisoformat(created_memory["created_at"]),
            updated_at=datetime.fromisoformat(created_memory["updated_at"]),
            access_count=0,
        )

        # Background tasks
        background_tasks.add_task(broadcast_memory_created, memory_obj)

        return MemoryResponse(
            success=True, memory=memory_obj, message="Memory created successfully"
        )

    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: UUID, memory_service: MemoryService = Depends(get_memory_service)):
    """Get a specific memory by ID"""
    memory_data = await memory_service.get_memory(str(memory_id))

    if not memory_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    memory = Memory(
        id=UUID(memory_data["id"]),
        content=memory_data["content"],
        memory_type=memory_data["memory_type"],
        importance_score=memory_data["importance_score"],
        tags=memory_data["tags"],
        metadata=memory_data["metadata"],
        created_at=datetime.fromisoformat(memory_data["created_at"]),
        updated_at=datetime.fromisoformat(memory_data["updated_at"]),
        access_count=memory_data.get("access_count", 0),
    )

    return MemoryResponse(success=True, memory=memory)


@router.get("/memories", response_model=MemoriesResponse)
async def list_memories(
    pagination: Dict[str, int] = Depends(validate_pagination),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    importance_min: Optional[float] = Query(None, ge=0, le=1),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """List memories with advanced filtering and pagination"""
    # Get memories (no user_id filtering)
    memories_data = await memory_service.list_memories(
        limit=pagination["limit"], offset=pagination["offset"]
    )

    # Convert to Memory objects
    memories = []
    for mem_data in memories_data:
        # Apply filters
        if memory_type and mem_data["memory_type"] != memory_type:
            continue
        if tags and not any(tag in mem_data["tags"] for tag in tags):
            continue
        if importance_min and mem_data["importance_score"] < importance_min:
            continue

        memories.append(
            Memory(
                id=UUID(mem_data["id"]),
                content=mem_data["content"],
                memory_type=mem_data["memory_type"],
                importance_score=mem_data["importance_score"],
                tags=mem_data["tags"],
                metadata=mem_data["metadata"],
                created_at=datetime.fromisoformat(mem_data["created_at"]),
                updated_at=datetime.fromisoformat(mem_data["updated_at"]),
                access_count=mem_data.get("access_count", 0),
            )
        )

    # Calculate total (simplified)
    total = len(memories_data) * 10  # Estimate

    return MemoriesResponse(
        success=True,
        memories=memories,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        has_next=len(memories) == pagination["page_size"],
        has_prev=pagination["page"] > 1,
    )


@router.patch("/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    update: MemoryUpdate,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Update a memory with partial data"""
    # Get existing memory
    existing = await memory_service.get_memory(str(memory_id))
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    # Update memory
    updated_data = await memory_service.update_memory(
        str(memory_id),
        content=update.content,
        importance_score=update.importance_score,
        tags=update.tags,
    )

    if not updated_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update memory"
        )

    memory = Memory(
        id=UUID(updated_data["id"]),
        content=updated_data["content"],
        memory_type=updated_data["memory_type"],
        importance_score=updated_data["importance_score"],
        tags=updated_data["tags"],
        metadata=updated_data["metadata"],
        created_at=datetime.fromisoformat(updated_data["created_at"]),
        updated_at=datetime.fromisoformat(updated_data["updated_at"]),
        access_count=updated_data.get("access_count", 0),
    )

    # Background task
    background_tasks.add_task(broadcast_memory_updated, memory)

    return MemoryResponse(success=True, memory=memory, message="Memory updated successfully")


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Delete a memory"""
    # Check if exists
    existing = await memory_service.get_memory(str(memory_id))
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    # Delete
    success = await memory_service.delete_memory(str(memory_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete memory"
        )

    # Background task
    background_tasks.add_task(broadcast_memory_deleted, str(memory_id))

    return {"success": True, "message": "Memory deleted successfully"}


# ========================= SEARCH ENDPOINTS =========================


@router.post("/search")
async def search_memories(
    search: SearchRequest, memory_service: MemoryService = Depends(get_memory_service)
):
    """Advanced search with multiple strategies"""
    results = await memory_service.search_memories(query=search.query, limit=search.limit)

    # Convert to Memory objects
    memories = []
    for mem_data in results:
        memories.append(
            Memory(
                id=UUID(mem_data["id"]),
                content=mem_data["content"],
                memory_type=mem_data["memory_type"],
                importance_score=mem_data["importance_score"],
                tags=mem_data["tags"],
                metadata=mem_data["metadata"],
                created_at=datetime.fromisoformat(mem_data["created_at"]),
                updated_at=datetime.fromisoformat(mem_data["updated_at"]),
                access_count=mem_data.get("access_count", 0),
            )
        )

    return {
        "success": True,
        "results": memories,
        "total": len(memories),
        "query": search.query,
        "search_type": search.search_type,
    }


# ========================= BULK OPERATIONS =========================


@router.post("/bulk")
async def bulk_operation(
    operation: BulkOperation,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Perform bulk operations on multiple memories"""
    results = {"success": [], "failed": [], "total": len(operation.memory_ids)}

    for memory_id in operation.memory_ids:
        try:
            # Check if exists
            existing = await memory_service.get_memory(str(memory_id))
            if not existing:
                results["failed"].append({"id": str(memory_id), "error": "Not found"})
                continue

            # Perform operation
            if operation.operation == "delete":
                success = await memory_service.delete_memory(str(memory_id))
                if success:
                    results["success"].append(str(memory_id))
                else:
                    results["failed"].append({"id": str(memory_id), "error": "Delete failed"})

            elif operation.operation == "update" and operation.data:
                # Update with provided data
                await memory_service.update_memory(str(memory_id), **operation.data)
                results["success"].append(str(memory_id))

            elif operation.operation == "tag" and operation.data and "tags" in operation.data:
                # Add tags
                existing_tags = existing.get("tags", [])
                new_tags = list(set(existing_tags + operation.data["tags"]))
                await memory_service.update_memory(str(memory_id), tags=new_tags)
                results["success"].append(str(memory_id))

        except Exception as e:
            results["failed"].append({"id": str(memory_id), "error": str(e)})

    # Background notification
    background_tasks.add_task(broadcast_bulk_operation, operation.operation, results)

    return {"success": True, "operation": operation.operation, "results": results}


# ========================= ANALYTICS ENDPOINTS =========================


@router.post("/analytics")
async def get_analytics(
    query: AnalyticsQuery, memory_service: MemoryService = Depends(get_memory_service)
):
    """Get advanced analytics and insights"""
    # This is a placeholder - in real implementation would query analytics service

    # Parse time range
    now = datetime.now(timezone.utc)
    time_ranges = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }

    start_date = now - time_ranges.get(query.time_range, timedelta(days=7))

    # Mock analytics data
    analytics_data = {
        "metric": query.metric,
        "time_range": query.time_range,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "data": {
            "total_memories": 1234,
            "active_days": 25,
            "top_tags": ["work", "personal", "ideas", "learning"],
            "memory_types": {"generic": 450, "episodic": 320, "semantic": 264, "procedural": 200},
            "importance_distribution": {
                "0-0.2": 100,
                "0.2-0.4": 200,
                "0.4-0.6": 400,
                "0.6-0.8": 350,
                "0.8-1.0": 184,
            },
            "growth_rate": 0.15,
            "engagement_score": 0.82,
        },
    }

    if query.metric == "trends":
        # Add trend data
        analytics_data["data"]["trends"] = {
            "memory_creation": [
                {"date": (now - timedelta(days=i)).date().isoformat(), "count": 40 + (i % 10)}
                for i in range(7, 0, -1)
            ],
            "tags_evolution": {
                "emerging": ["ai", "productivity", "health"],
                "declining": ["todo", "temp"],
                "stable": ["work", "personal"],
            },
        }

    elif query.metric == "insights":
        # Add insights
        analytics_data["data"]["insights"] = [
            {
                "type": "pattern",
                "title": "Peak productivity hours",
                "description": "Most memories created between 9-11 AM",
                "confidence": 0.87,
            },
            {
                "type": "recommendation",
                "title": "Consider reviewing old memories",
                "description": "45 memories not accessed in 30+ days",
                "action": "review_old_memories",
            },
        ]

    return {"success": True, "analytics": analytics_data}


# ========================= EXPORT/IMPORT =========================


@router.get("/export")
async def export_memories(
    format: str = Query("json", pattern="^(json|csv|markdown)$"),
    include_metadata: bool = Query(True),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Export all memories in various formats"""
    # Get all memories
    all_memories = []
    offset = 0
    batch_size = 100

    while True:
        batch = await memory_service.list_memories(limit=batch_size, offset=offset)
        if not batch:
            break
        all_memories.extend(batch)
        offset += batch_size
        if len(batch) < batch_size:
            break

    # Format based on request
    if format == "json":
        content = json.dumps(all_memories, indent=2, default=str)
        media_type = "application/json"
        filename = f"memories_export_{datetime.now().date()}.json"

    elif format == "csv":
        import csv
        import io

        output = io.StringIO()
        if all_memories:
            writer = csv.DictWriter(output, fieldnames=all_memories[0].keys())
            writer.writeheader()
            writer.writerows(all_memories)

        content = output.getvalue()
        media_type = "text/csv"
        filename = f"memories_export_{datetime.now().date()}.csv"

    else:  # markdown
        lines = ["# Memory Export\n\n"]
        for mem in all_memories:
            lines.append(f"## {mem['created_at']}\n\n")
            lines.append(f"{mem['content']}\n\n")
            if include_metadata:
                lines.append(f"- **Type**: {mem['memory_type']}\n")
                lines.append(f"- **Importance**: {mem['importance_score']}\n")
                lines.append(f"- **Tags**: {', '.join(mem['tags'])}\n")
            lines.append("\n---\n\n")

        content = "".join(lines)
        media_type = "text/markdown"
        filename = f"memories_export_{datetime.now().date()}.md"

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
async def import_memories(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Import memories from file"""
    if not file.filename.endswith((".json", ".csv")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only JSON and CSV files are supported"
        )

    content = await file.read()

    try:
        if file.filename.endswith(".json"):
            memories_data = json.loads(content)
        else:
            # CSV parsing would go here
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="CSV import not yet implemented"
            )

        # Import memories
        imported = 0
        failed = 0

        for mem_data in memories_data:
            try:
                await memory_service.create_memory(
                    content=mem_data.get("content", ""),
                    importance_score=mem_data.get("importance_score", 0.5),
                    tags=mem_data.get("tags", []),
                    metadata=mem_data.get("metadata", {}),
                )
                imported += 1
            except:
                failed += 1

        # Background notification
        background_tasks.add_task(broadcast_import_complete, imported, failed)

        return {
            "success": True,
            "imported": imported,
            "failed": failed,
            "total": len(memories_data),
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON file")


# ========================= WEBSOCKET ENDPOINT =========================


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    try:
        await manager.connect(websocket)

        while True:
            # Receive message
            data = await websocket.receive_json()
            message = WebSocketMessage(**data)

            # Handle message types
            if message.type == "ping":
                await websocket.send_json(
                    WebSocketResponse(
                        type="pong", correlation_id=message.data.get("id") if message.data else None
                    ).dict()
                )

            elif message.type == "message":
                # Broadcast message to all connections
                await manager.broadcast(WebSocketResponse(type="message", data=message.data))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ========================= BACKGROUND TASKS =========================


async def broadcast_memory_created(memory: Memory):
    """Broadcast memory creation event"""
    await manager.broadcast(WebSocketResponse(type="memory_created", data=memory.dict()))


async def broadcast_memory_updated(memory: Memory):
    """Broadcast memory update event"""
    await manager.broadcast(WebSocketResponse(type="memory_updated", data=memory.dict()))


async def broadcast_memory_deleted(memory_id: str):
    """Broadcast memory deletion event"""
    await manager.broadcast(WebSocketResponse(type="memory_deleted", data={"memory_id": memory_id}))


async def broadcast_bulk_operation(operation: str, results: Dict):
    """Broadcast bulk operation results"""
    await manager.broadcast(
        WebSocketResponse(
            type="bulk_operation_complete", data={"operation": operation, "results": results}
        )
    )


async def broadcast_import_complete(imported: int, failed: int):
    """Broadcast import completion"""
    await manager.broadcast(
        WebSocketResponse(type="import_complete", data={"imported": imported, "failed": failed})
    )


# ========================= HEALTH & STATUS =========================


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": {
            "websocket": True,
            "bulk_operations": True,
            "analytics": True,
            "export_import": True,
            "real_time_updates": True,
        },
    }
