"""
Simple FastAPI backend with in-memory storage for development
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

app = FastAPI(
    title="Second Brain API",
    version="4.2.0-dev",
    description="Simplified development API"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
memories_db: Dict[str, Dict[str, Any]] = {}

class MemoryCreate(BaseModel):
    content: str
    memory_type: str = "generic"
    importance_score: float = 0.5
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

class Memory(BaseModel):
    id: str
    content: str
    memory_type: str
    importance_score: float
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@app.get("/")
async def root():
    return {
        "message": "Second Brain API",
        "version": "4.2.0-dev",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "memories": "/api/v2/memories",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "memory_count": len(memories_db),
        "backend": "in-memory",
        "version": "4.2.0-dev"
    }

@app.post("/api/v2/memories", response_model=Memory)
async def create_memory(memory: MemoryCreate):
    memory_id = str(uuid.uuid4())
    now = datetime.now()
    
    memory_data = {
        "id": memory_id,
        "content": memory.content,
        "memory_type": memory.memory_type,
        "importance_score": memory.importance_score,
        "tags": memory.tags,
        "metadata": memory.metadata,
        "created_at": now,
        "updated_at": now
    }
    
    memories_db[memory_id] = memory_data
    return Memory(**memory_data)

@app.get("/api/v2/memories", response_model=List[Memory])
async def list_memories(
    limit: int = 100,
    offset: int = 0,
    memory_type: Optional[str] = None,
    tag: Optional[str] = None
):
    # Filter memories
    filtered = list(memories_db.values())
    
    if memory_type:
        filtered = [m for m in filtered if m["memory_type"] == memory_type]
    
    if tag:
        filtered = [m for m in filtered if tag in m["tags"]]
    
    # Sort by created_at descending
    filtered.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    paginated = filtered[offset:offset + limit]
    
    return [Memory(**m) for m in paginated]

@app.get("/api/v2/memories/{memory_id}", response_model=Memory)
async def get_memory(memory_id: str):
    if memory_id not in memories_db:
        raise HTTPException(status_code=404, detail="Memory not found")
    return Memory(**memories_db[memory_id])

@app.put("/api/v2/memories/{memory_id}", response_model=Memory)
async def update_memory(memory_id: str, memory: MemoryCreate):
    if memory_id not in memories_db:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    existing = memories_db[memory_id]
    existing.update({
        "content": memory.content,
        "memory_type": memory.memory_type,
        "importance_score": memory.importance_score,
        "tags": memory.tags,
        "metadata": memory.metadata,
        "updated_at": datetime.now()
    })
    
    return Memory(**existing)

@app.delete("/api/v2/memories/{memory_id}")
async def delete_memory(memory_id: str):
    if memory_id not in memories_db:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    del memories_db[memory_id]
    return {"message": "Memory deleted successfully"}

@app.get("/api/v2/search")
async def search_memories(
    q: str,
    limit: int = 10
):
    """Simple text search in memory content"""
    query = q.lower()
    results = []
    
    for memory in memories_db.values():
        if query in memory["content"].lower():
            results.append(Memory(**memory))
    
    # Sort by importance score
    results.sort(key=lambda x: x.importance_score, reverse=True)
    
    return results[:limit]

# Add some sample data on startup
@app.on_event("startup")
async def startup_event():
    # Add sample memories
    sample_memories = [
        {
            "content": "FastAPI is a modern web framework for building APIs with Python",
            "memory_type": "fact",
            "importance_score": 0.8,
            "tags": ["python", "fastapi", "web"]
        },
        {
            "content": "The Second Brain project helps organize and retrieve information",
            "memory_type": "concept",
            "importance_score": 0.9,
            "tags": ["second-brain", "knowledge-management"]
        },
        {
            "content": "PostgreSQL with pgvector enables semantic search capabilities",
            "memory_type": "technical",
            "importance_score": 0.7,
            "tags": ["database", "postgresql", "vectors"]
        }
    ]
    
    for memory_data in sample_memories:
        memory = MemoryCreate(**memory_data)
        memory_id = str(uuid.uuid4())
        now = datetime.now()
        
        memories_db[memory_id] = {
            "id": memory_id,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "importance_score": memory.importance_score,
            "tags": memory.tags,
            "metadata": memory.metadata,
            "created_at": now,
            "updated_at": now
        }