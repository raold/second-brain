from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.core.exceptions import SecondBrainException, UnauthorizedException, ValidationException

"""
Common request and response models for API routes
"""




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
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}", status_code=429
        )


# Memory-related models
class MemoryRequest(BaseModel):
    """Request model for storing memories"""

    content: str
    memory_type: str = "semantic"
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None
    semantic_metadata: dict[str, Any] | None = None
    episodic_metadata: dict[str, Any] | None = None
    procedural_metadata: dict[str, Any] | None = None


class SearchRequest(BaseModel):
    """Request model for memory search"""

    query: str
    limit: int | None = 10
    memory_types: list[str] | None = None


class SemanticMemoryRequest(BaseModel):
    """Request model for semantic memories"""

    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_metadata: dict[str, Any] | None = None


class EpisodicMemoryRequest(BaseModel):
    """Request model for episodic memories"""

    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    episodic_metadata: dict[str, Any] | None = None


class ProceduralMemoryRequest(BaseModel):
    """Request model for procedural memories"""

    content: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    procedural_metadata: dict[str, Any] | None = None


class ContextualSearchRequest(BaseModel):
    """Request model for contextual search"""

    query: str
    memory_types: list[str] | None = None
    importance_threshold: float | None = None
    limit: int = 10


# Report-related models
class ReportRequest(BaseModel):
    """Request model for report generation"""

    report_type: str = "summary"
    memory_types: list[str] | None = None
    date_range: dict[str, str] | None = None
    include_insights: bool = True


class ReportResponse(BaseModel):
    """Response model for reports"""

    id: str
    report_type: str
    content: str
    created_at: str
    metadata: dict[str, Any] | None = None


class BulkReviewRequest(BaseModel):
    """Request model for bulk review operations"""

    memory_ids: list[str]
    action: str = "review"
    criteria: dict[str, Any] | None = None


class SubscriptionRequest(BaseModel):
    """Request model for subscriptions"""

    endpoint: str
    event_types: list[str]
    filters: dict[str, Any] | None = None
