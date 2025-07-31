"""
OpenAPI documentation configuration for Second Brain API
"""

from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.version import get_version_info
from typing import Optional
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


# Memory type enumeration
class MemoryType(str, Enum):
    """Memory type classification based on cognitive psychology"""

    SEMANTIC = "semantic"  # Facts, concepts, general knowledge
    EPISODIC = "episodic"  # Time-bound experiences, contextual events
    PROCEDURAL = "procedural"  # Process knowledge, workflows, instructions


# Priority enumeration for task/todo management
class Priority(str, Enum):
    """Priority levels for tasks and todos"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Type-specific metadata models
class SemanticMetadata(BaseModel):
    """Metadata specific to semantic memories"""

    category: str | None = Field(default=None, description="Knowledge category")
    domain: str | None = Field(default=None, description="Subject domain")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Confidence level")
    verified: bool | None = Field(default=None, description="Fact verification status")

    class Config:
        json_schema_extra = {
            "example": {"category": "technology", "domain": "database", "confidence": 0.95, "verified": True}
        }


class EpisodicMetadata(BaseModel):
    """Metadata specific to episodic memories"""

    timestamp: str | None = Field(default=None, description="Event timestamp")
    context: str | None = Field(default=None, description="Situational context")
    location: str | None = Field(default=None, description="Physical or virtual location")
    outcome: str | None = Field(default=None, description="Event outcome")
    emotional_valence: str | None = Field(default=None, description="Emotional tone")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-07-17T16:30:00Z",
                "context": "debugging_session",
                "location": "development_environment",
                "outcome": "resolved",
                "emotional_valence": "relief",
            }
        }


class ProceduralMetadata(BaseModel):
    """Metadata specific to procedural memories"""

    skill_level: str | None = Field(default=None, description="Required skill level")
    complexity: str | None = Field(default=None, description="Process complexity")
    success_rate: float | None = Field(default=None, ge=0.0, le=1.0, description="Success rate")
    steps: int | None = Field(default=None, ge=1, description="Number of steps")
    domain: str | None = Field(default=None, description="Domain area")

    class Config:
        json_schema_extra = {
            "example": {
                "skill_level": "expert",
                "complexity": "medium",
                "success_rate": 0.98,
                "steps": 5,
                "domain": "devops",
            }
        }


# Response models for OpenAPI documentation
class MemoryResponse(BaseModel):
    """Response model for memory objects with cognitive memory types"""

    id: str = Field(..., description="Unique memory identifier")
    content: str = Field(..., description="Memory content text")
    memory_type: MemoryType = Field(..., description="Memory type classification")

    # Cognitive metadata
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Memory importance score")
    access_count: int = Field(default=0, description="Number of times accessed")
    last_accessed: str = Field(..., description="Last access timestamp")

    # Type-specific metadata
    semantic_metadata: dict[str, Any] | None = Field(default=None, description="Semantic memory metadata")
    episodic_metadata: dict[str, Any] | None = Field(default=None, description="Episodic memory metadata")
    procedural_metadata: dict[str, Any] | None = Field(default=None, description="Procedural memory metadata")

    # Consolidation tracking
    consolidation_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Memory consolidation score")

    # Legacy compatibility
    metadata: dict[str, Any] | None = Field(default=None, description="General metadata (legacy)")

    # Timestamps
    created_at: str = Field(..., description="Memory creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    # Search-specific
    similarity: float | None = Field(default=None, description="Similarity score for search results")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "mem_123456",
                "content": "PostgreSQL pgvector enables efficient semantic search",
                "memory_type": "semantic",
                "importance_score": 0.85,
                "access_count": 12,
                "last_accessed": "2024-01-15T10:30:00Z",
                "semantic_metadata": {
                    "category": "technology",
                    "domain": "database",
                    "confidence": 0.95,
                    "verified": True,
                },
                "consolidation_score": 0.75,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "similarity": 0.85,
            }
        }


class SearchResponse(BaseModel):
    """Response model for search results"""

    id: str = Field(..., description="Memory ID")
    content: str = Field(..., description="Memory content")
    relevance_score: float = Field(..., description="Similarity score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "mem_789012",
                "content": "Meeting with client about new project requirements",
                "relevance_score": 0.85,
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str = Field(..., description="Application health status")
    version: str = Field(..., description="Current version")
    timestamp: datetime = Field(..., description="Health check timestamp")

    class Config:
        json_schema_extra = {"example": {"status": "healthy", "version": "2.0.0", "timestamp": "2024-01-15T12:00:00Z"}}


class StatusResponse(BaseModel):
    """Response model for system status"""

    database: str = Field(..., description="Database connection status")
    index_status: dict[str, Any] = Field(..., description="Vector index statistics")
    recommendations: dict[str, Any] = Field(..., description="Performance recommendations")

    class Config:
        json_schema_extra = {
            "example": {
                "database": "connected",
                "index_status": {
                    "total_memories": 1500,
                    "memories_with_embeddings": 1500,
                    "hnsw_index_exists": True,
                    "index_ready": True,
                },
                "recommendations": {"create_index": False, "index_type": "HNSW (preferred)"},
            }
        }


class MemoryRequest(BaseModel):
    """Request model for creating memories with cognitive types"""

    content: str = Field(..., description="Memory content to store", min_length=1)
    memory_type: MemoryType = Field(default=MemoryType.SEMANTIC, description="Memory type classification")

    # Type-specific metadata
    semantic_metadata: SemanticMetadata | None = Field(default=None, description="Semantic memory metadata")
    episodic_metadata: EpisodicMetadata | None = Field(default=None, description="Episodic memory metadata")
    procedural_metadata: ProceduralMetadata | None = Field(default=None, description="Procedural memory metadata")

    # Legacy compatibility
    metadata: dict[str, Any] | None = Field(default=None, description="General metadata (legacy)")

    # Optional cognitive parameters
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Initial importance score")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "PostgreSQL pgvector extension enables efficient vector similarity search with HNSW indexing",
                "memory_type": "semantic",
                "semantic_metadata": {
                    "category": "technology",
                    "domain": "database",
                    "confidence": 0.95,
                    "verified": True,
                },
                "importance_score": 0.8,
            }
        }


# Type-specific request models
class SemanticMemoryRequest(BaseModel):
    """Request model for semantic memories"""

    content: str = Field(..., description="Semantic memory content", min_length=1)
    semantic_metadata: SemanticMetadata | None = Field(default=None, description="Semantic metadata")
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Importance score")


class EpisodicMemoryRequest(BaseModel):
    """Request model for episodic memories"""

    content: str = Field(..., description="Episodic memory content", min_length=1)
    episodic_metadata: EpisodicMetadata | None = Field(default=None, description="Episodic metadata")
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Importance score")


class ProceduralMemoryRequest(BaseModel):
    """Request model for procedural memories"""

    content: str = Field(..., description="Procedural memory content", min_length=1)
    procedural_metadata: ProceduralMetadata | None = Field(default=None, description="Procedural metadata")
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Importance score")


# Enhanced search request model
class ContextualSearchRequest(BaseModel):
    """Request model for contextual search with memory type filtering"""

    query: str = Field(..., description="Search query", min_length=1)
    memory_types: list[MemoryType] | None = Field(default=None, description="Filter by memory types")
    importance_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="Minimum importance score")
    timeframe: str | None = Field(default=None, description="Time-based filtering (e.g., 'last_week', 'last_month')")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    include_archived: bool = Field(default=False, description="Include archived memories")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "CI/CD debugging process",
                "memory_types": ["episodic", "procedural"],
                "importance_threshold": 0.6,
                "timeframe": "last_week",
                "limit": 5,
                "include_archived": False,
            }
        }


# Legacy search request model for backward compatibility
class SearchRequest(BaseModel):
    """Request model for simple search queries"""

    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")

    class Config:
        json_schema_extra = {"example": {"query": "database optimization techniques", "limit": 5}}


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str = Field(..., description="Error message")
    details: str | None = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {"error": "Memory not found", "details": "No memory exists with the provided ID"}
        }


def setup_openapi_documentation(app: FastAPI):
    """Setup comprehensive OpenAPI documentation."""
    version_info = get_version_info()

    app.openapi_version = "3.0.2"
    app.title = "Second Brain API"
    app.description = """
## Second Brain - AI Memory System

A minimal, fast, and reliable AI memory system built with PostgreSQL and pgvector.

### Features
- **Semantic Search**: Vector similarity search with automatic HNSW indexing
- **Memory Management**: Store, retrieve, update, and delete memories
- **Performance Optimized**: Sub-100ms search times with PostgreSQL pgvector
- **Mock Database**: Cost-free testing without external dependencies
- **Version Tracking**: Comprehensive version management and monitoring

### Authentication
All endpoints require an API key passed as a query parameter:
```
?api_key=your_api_key_here
```

### Performance
- **Search Response Time**: < 100ms average
- **Memory Storage**: < 500ms average
- **Automatic Indexing**: HNSW index created at 1000+ memories
- **Scalability**: Tested with 1M+ memories

### Error Handling
- **400**: Bad Request - Invalid input data
- **401**: Unauthorized - Invalid or missing API key
- **404**: Not Found - Resource not found
- **422**: Unprocessable Entity - Validation error
- **500**: Internal Server Error - System error

### Rate Limits
- **Default**: 1000 requests per minute per API key
- **Burst**: 100 requests per 10 seconds
    """
    app.version = version_info["version"]
    app.contact = {
        "name": "Second Brain Development Team",
        "url": "https://github.com/raold/second-brain",
        "email": "support@secondbrain.ai",
    }
    app.license_info = {
        "name": "GNU Affero General Public License v3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0",
    }
    app.servers = [
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.secondbrain.ai", "description": "Production server"},
    ]

    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            contact=app.contact,
            license_info=app.license_info,
            servers=app.servers,
        )

        # Add custom tags
        openapi_schema["tags"] = [
            {"name": "Health", "description": "System health and status endpoints"},
            {"name": "Memories", "description": "Memory management operations"},
            {"name": "Search", "description": "Semantic search functionality"},
            {"name": "Synthesis", "description": "Knowledge synthesis and automation (v2.8.2)"},
            {"name": "Consolidation", "description": "Memory consolidation operations"},
            {"name": "Summarization", "description": "AI-powered knowledge summarization"},
            {"name": "Suggestions", "description": "Smart memory suggestions"},
            {"name": "Metrics", "description": "Real-time graph metrics and analytics"},
        ]

        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "query",
                "name": "api_key",
                "description": "API key for authentication",
            }
        }

        # Add security to all endpoints
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                if method != "parameters":
                    openapi_schema["paths"][path][method]["security"] = [{"ApiKeyAuth": []}]

        # Add examples
        openapi_schema["components"]["examples"] = {
            "MemoryExample": {
                "summary": "Simple memory",
                "value": {
                    "content": "PostgreSQL is a powerful relational database",
                    "metadata": {"type": "fact", "category": "database", "importance": "high"},
                },
            },
            "SearchExample": {"summary": "Search query", "value": {"query": "database performance", "limit": 10}},
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
