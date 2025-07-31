"""
Common request and response models for API routes
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from fastapi import HTTPException


class SecondBrainException(HTTPException):
    """Base exception for Second Brain API"""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=message)


class ValidationException(SecondBrainException):
    """Validation error"""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)


class NotFoundException(SecondBrainException):
    """Resource not found"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(message=f"{resource} not found: {identifier}", status_code=404)


class UnauthorizedException(SecondBrainException):
    """Unauthorized access"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=401)


class RateLimitExceededException(SecondBrainException):
    """Rate limit exceeded"""
    def __init__(self, limit: int, window: str):
        super().__init__(message=f"Rate limit exceeded: {limit} requests per {window}", status_code=429)


# Memory-related models
class MemoryRequest(BaseModel):
    """Request model for storing memories"""
    content: str
    memory_type: str = "semantic"
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
    semantic_metadata: Optional[Dict[str, Any]] = None
    episodic_metadata: Optional[Dict[str, Any]] = None
    procedural_metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    """Request model for memory search"""
    query: str
    limit: Optional[int] = 10
    memory_types: Optional[List[str]] = None


class SemanticMemoryRequest(BaseModel):
    """Request model for semantic memories"""
    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_metadata: Optional[Dict[str, Any]] = None


class EpisodicMemoryRequest(BaseModel):
    """Request model for episodic memories"""
    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    episodic_metadata: Optional[Dict[str, Any]] = None


class ProceduralMemoryRequest(BaseModel):
    """Request model for procedural memories"""
    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    procedural_metadata: Optional[Dict[str, Any]] = None


class ContextualSearchRequest(BaseModel):
    """Request model for contextual search"""
    query: str
    memory_types: Optional[List[str]] = None
    importance_threshold: Optional[float] = None
    limit: int = 10


# Report-related models
class ReportRequest(BaseModel):
    """Request model for report generation"""
    report_type: str = "summary"
    memory_types: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
    include_insights: bool = True


class ReportResponse(BaseModel):
    """Response model for reports"""
    id: str
    report_type: str
    content: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class BulkReviewRequest(BaseModel):
    """Request model for bulk review operations"""
    memory_ids: List[str]
    action: str = "review"
    criteria: Optional[Dict[str, Any]] = None


class SubscriptionRequest(BaseModel):
    """Request model for subscriptions"""
    endpoint: str
    event_types: List[str]
    filters: Optional[Dict[str, Any]] = None