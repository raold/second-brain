"""
Search-related models for Second Brain
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.memory import MemoryType


class SearchCriteria(BaseModel):
    """Criteria for searching memories"""
    query: Optional[str] = Field(None, description="Search query text")
    user_id: Optional[str] = Field(None, description="User ID filter")
    memory_type: Optional[MemoryType] = Field(None, description="Memory type filter")
    tags: Optional[List[str]] = Field(None, description="Tags to filter by")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    limit: Optional[int] = Field(100, description="Maximum results to return")
    offset: Optional[int] = Field(0, description="Offset for pagination")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "python programming",
                "memory_type": "note",
                "tags": ["python", "programming"],
                "limit": 50
            }
        }


class SearchResult(BaseModel):
    """Search result with memory and relevance score"""
    memory_id: str
    content: str
    memory_type: MemoryType
    created_at: datetime
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    highlights: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Python is a high-level programming language...",
                "memory_type": "note",
                "created_at": "2024-01-15T10:30:00Z",
                "relevance_score": 0.95,
                "highlights": ["Python", "programming language"]
            }
        }