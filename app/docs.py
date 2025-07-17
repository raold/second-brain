"""
OpenAPI documentation configuration for Second Brain API
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.version import get_version_info


# Response models for OpenAPI documentation
class MemoryResponse(BaseModel):
    """Response model for memory objects"""

    id: str = Field(..., description="Unique memory identifier")
    content: str = Field(..., description="Memory content text")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata")
    created_at: str = Field(..., description="Memory creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    similarity: Optional[float] = Field(default=None, description="Similarity score for search results")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "mem_123456",
                "content": "Important meeting notes from client discussion",
                "metadata": {"type": "meeting", "priority": "high"},
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
    """Request model for creating memories"""

    content: str = Field(..., description="Memory content to store", min_length=1)
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Remember to follow up on the project proposal by Friday",
                "metadata": {"type": "reminder", "priority": "high", "due_date": "2024-01-19"},
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")

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
