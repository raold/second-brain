"""
Memory CRUD operations router
Handles creation, retrieval, update, and deletion of memories
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger
from app.services.memory_service import MemoryService

logger = get_logger(__name__)

# Router with tag for OpenAPI organization
router = APIRouter(
    prefix="/memories",
    tags=["Memories"],
    responses={
        404: {"description": "Memory not found"},
        500: {"description": "Internal server error"}
    }
)


# ==================== Models ====================

class MemoryBase(BaseModel):
    """Base memory model with common fields"""
    content: str = Field(..., min_length=1, max_length=50000, description="Memory content")
    memory_type: str = Field("generic", description="Type of memory")
    importance_score: float = Field(0.5, ge=0, le=1, description="Importance score")
    tags: List[str] = Field(default_factory=list, max_items=20)
    metadata: Dict = Field(default_factory=dict)


class MemoryCreate(MemoryBase):
    """Memory creation request"""
    embedding_model: Optional[str] = Field("text-embedding-ada-002", description="Embedding model to use")
    auto_tag: bool = Field(True, description="Automatically generate tags")
    auto_importance: bool = Field(True, description="Automatically calculate importance")


class MemoryUpdate(BaseModel):
    """Memory update request - all fields optional"""
    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance_score: Optional[float] = Field(None, ge=0, le=1)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class Memory(MemoryBase):
    """Complete memory model"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


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


# ==================== Dependencies ====================

async def get_memory_service() -> MemoryService:
    """Get memory service instance"""
    return MemoryService()


async def validate_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
) -> Dict[str, int]:
    """Validate pagination parameters"""
    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "limit": page_size
    }


# ==================== Endpoints ====================

@router.post(
    "/",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
    description="Store a new memory with automatic importance scoring and tagging"
)
async def create_memory(
    memory: MemoryCreate,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Create a new memory in the user's brain.
    
    - **content**: The memory content to store
    - **importance_score**: How important this memory is (0-1)
    - **tags**: Tags for categorization
    - **auto_tag**: Whether to automatically generate tags
    - **auto_importance**: Whether to automatically calculate importance
    """
    try:
        created_memory = await memory_service.create_memory(
            content=memory.content,
            importance_score=memory.importance_score,
            tags=memory.tags,
            metadata=memory.metadata
        )
        
        memory_obj = Memory(
            id=UUID(created_memory["id"]),
            content=created_memory["content"],
            memory_type=created_memory["memory_type"],
            importance_score=created_memory["importance_score"],
            tags=created_memory["tags"],
            metadata=created_memory["metadata"],
            created_at=datetime.fromisoformat(created_memory["created_at"]),
            updated_at=datetime.fromisoformat(created_memory["updated_at"]),
            access_count=0
        )
        
        return MemoryResponse(
            success=True,
            memory=memory_obj,
            message="Memory created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a specific memory",
    description="Retrieve a memory by its ID"
)
async def get_memory(
    memory_id: UUID,
    memory_service: MemoryService = Depends(get_memory_service)
):
    """Get a specific memory by ID"""
    memory_data = await memory_service.get_memory(str(memory_id))
    
    if not memory_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found"
        )
    
    memory = Memory(
        id=UUID(memory_data["id"]),
        content=memory_data["content"],
        memory_type=memory_data["memory_type"],
        importance_score=memory_data["importance_score"],
        tags=memory_data["tags"],
        metadata=memory_data["metadata"],
        created_at=datetime.fromisoformat(memory_data["created_at"]),
        updated_at=datetime.fromisoformat(memory_data["updated_at"]),
        access_count=memory_data.get("access_count", 0)
    )
    
    return MemoryResponse(success=True, memory=memory)


@router.get(
    "/",
    response_model=MemoriesResponse,
    summary="List memories",
    description="List all memories with optional filtering and pagination"
)
async def list_memories(
    pagination: Dict[str, int] = Depends(validate_pagination),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    importance_min: Optional[float] = Query(None, ge=0, le=1),
    memory_service: MemoryService = Depends(get_memory_service)
):
    """List memories with advanced filtering and pagination"""
    memories_data = await memory_service.list_memories(
        limit=pagination["limit"],
        offset=pagination["offset"]
    )
    
    memories = []
    for mem_data in memories_data:
        # Apply filters
        if memory_type and mem_data["memory_type"] != memory_type:
            continue
        if tags and not any(tag in mem_data["tags"] for tag in tags):
            continue
        if importance_min and mem_data["importance_score"] < importance_min:
            continue
            
        memories.append(Memory(
            id=UUID(mem_data["id"]),
            content=mem_data["content"],
            memory_type=mem_data["memory_type"],
            importance_score=mem_data["importance_score"],
            tags=mem_data["tags"],
            metadata=mem_data["metadata"],
            created_at=datetime.fromisoformat(mem_data["created_at"]),
            updated_at=datetime.fromisoformat(mem_data["updated_at"]),
            access_count=mem_data.get("access_count", 0)
        ))
    
    total = len(memories_data) * 10  # Estimate
    
    return MemoriesResponse(
        success=True,
        memories=memories,
        total=total,
        page=pagination["page"],
        page_size=pagination["page_size"],
        has_next=len(memories) == pagination["page_size"],
        has_prev=pagination["page"] > 1
    )


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update a memory",
    description="Update a memory with partial data"
)
async def update_memory(
    memory_id: UUID,
    update: MemoryUpdate,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service)
):
    """Update a memory with partial data"""
    existing = await memory_service.get_memory(str(memory_id))
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found"
        )
    
    updated_data = await memory_service.update_memory(
        str(memory_id),
        content=update.content,
        importance_score=update.importance_score,
        tags=update.tags
    )
    
    if not updated_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory"
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
        access_count=updated_data.get("access_count", 0)
    )
    
    return MemoryResponse(
        success=True,
        memory=memory,
        message="Memory updated successfully"
    )


@router.delete(
    "/{memory_id}",
    summary="Delete a memory",
    description="Permanently delete a memory"
)
async def delete_memory(
    memory_id: UUID,
    background_tasks: BackgroundTasks,
    memory_service: MemoryService = Depends(get_memory_service)
):
    """Delete a memory"""
    existing = await memory_service.get_memory(str(memory_id))
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found"
        )
    
    success = await memory_service.delete_memory(str(memory_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory"
        )
    
    return {"success": True, "message": "Memory deleted successfully"}