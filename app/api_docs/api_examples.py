"""
API Documentation Examples for Second Brain

This module provides comprehensive examples for all API endpoints
to enhance the FastAPI auto-generated documentation.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import FastAPI


class APIExample:
    """Container for API endpoint examples"""
    
    # Memory Creation Examples
    MEMORY_CREATE_EXAMPLES = {
        "semantic_memory": {
            "summary": "Create a semantic memory (fact/concept)",
            "description": "Store a fact or concept for long-term retention",
            "value": {
                "content": "Python is a high-level programming language created by Guido van Rossum",
                "memory_type": "semantic",
                "tags": ["programming", "python", "technology"],
                "importance": 0.8,
                "metadata": {
                    "category": "technical_knowledge",
                    "source": "documentation"
                }
            }
        },
        "episodic_memory": {
            "summary": "Create an episodic memory (personal experience)",
            "description": "Store a personal experience or event",
            "value": {
                "content": "Had a productive meeting with the team about the new AI features",
                "memory_type": "episodic",
                "tags": ["meeting", "team", "ai", "work"],
                "importance": 0.7,
                "metadata": {
                    "date": "2025-01-14",
                    "participants": ["John", "Sarah", "Mike"],
                    "location": "Conference Room A"
                }
            }
        },
        "procedural_memory": {
            "summary": "Create a procedural memory (how-to)",
            "description": "Store step-by-step instructions or procedures",
            "value": {
                "content": "To deploy with Docker: 1) Build image with docker build -t app . 2) Run container with docker run -p 8000:8000 app 3) Check health at /health",
                "memory_type": "procedural",
                "tags": ["docker", "deployment", "devops"],
                "importance": 0.9,
                "metadata": {
                    "tool": "docker",
                    "difficulty": "intermediate",
                    "time_estimate": "5 minutes"
                }
            }
        }
    }
    
    # Search Examples
    SEARCH_EXAMPLES = {
        "semantic_search": {
            "summary": "Semantic search for similar concepts",
            "description": "Find memories related to a concept using vector similarity",
            "value": {
                "query": "machine learning algorithms",
                "search_type": "semantic",
                "limit": 10,
                "threshold": 0.7,
                "filters": {
                    "tags": ["ai", "ml"],
                    "memory_type": "semantic"
                }
            }
        },
        "contextual_search": {
            "summary": "Contextual search with metadata",
            "description": "Search with context awareness and metadata filters",
            "value": {
                "query": "team meetings about product features",
                "search_type": "contextual",
                "context": "Looking for recent discussions about AI integration",
                "limit": 5,
                "date_range": {
                    "start": "2025-01-01",
                    "end": "2025-01-31"
                }
            }
        },
        "hybrid_search": {
            "summary": "Hybrid search combining multiple strategies",
            "description": "Combine keyword and semantic search for best results",
            "value": {
                "query": "docker deployment",
                "search_type": "hybrid",
                "limit": 15,
                "boost_keywords": ["container", "kubernetes"],
                "exclude_tags": ["deprecated"]
            }
        }
    }
    
    # Google Drive Examples
    GDRIVE_EXAMPLES = {
        "oauth_initiate": {
            "summary": "Start Google Drive OAuth flow",
            "description": "Begin the OAuth process to connect Google Drive",
            "value": {
                "redirect_after_auth": "/dashboard",
                "scopes": ["drive.readonly"]
            }
        },
        "sync_folder": {
            "summary": "Sync a Google Drive folder",
            "description": "Stream and process files from a Drive folder",
            "value": {
                "folder_id": "1ABC123DEF456GHI",
                "recursive": True,
                "file_types": ["document", "spreadsheet", "pdf"],
                "processing_options": {
                    "extract_text": True,
                    "generate_embeddings": True,
                    "create_memories": True
                }
            }
        },
        "webhook_subscribe": {
            "summary": "Subscribe to Drive changes",
            "description": "Set up real-time notifications for Drive changes",
            "value": {
                "resource_id": "drive_root",
                "notification_url": "https://yourdomain.com/webhooks/gdrive",
                "events": ["file.created", "file.modified", "file.deleted"],
                "expiration": "2025-02-14T00:00:00Z"
            }
        }
    }
    
    # Bulk Operations Examples
    BULK_EXAMPLES = {
        "bulk_create": {
            "summary": "Create multiple memories at once",
            "description": "Efficiently create many memories in a single request",
            "value": {
                "memories": [
                    {
                        "content": "First memory content",
                        "memory_type": "semantic",
                        "tags": ["bulk", "test"]
                    },
                    {
                        "content": "Second memory content",
                        "memory_type": "episodic",
                        "tags": ["bulk", "test"]
                    }
                ],
                "batch_metadata": {
                    "source": "import",
                    "timestamp": "2025-01-14T10:00:00Z"
                }
            }
        },
        "bulk_update": {
            "summary": "Update multiple memories",
            "description": "Update tags or metadata for multiple memories",
            "value": {
                "memory_ids": ["mem_123", "mem_456", "mem_789"],
                "updates": {
                    "add_tags": ["reviewed", "important"],
                    "update_metadata": {
                        "last_reviewed": "2025-01-14"
                    },
                    "importance": 0.9
                }
            }
        }
    }
    
    # Analysis Examples
    ANALYSIS_EXAMPLES = {
        "pattern_analysis": {
            "summary": "Analyze patterns in memories",
            "description": "Identify patterns and trends in your knowledge base",
            "value": {
                "analysis_type": "pattern",
                "time_range": "last_30_days",
                "focus_areas": ["technology", "meetings"],
                "min_occurrence": 3
            }
        },
        "knowledge_gaps": {
            "summary": "Identify knowledge gaps",
            "description": "Find areas where more information is needed",
            "value": {
                "analysis_type": "gaps",
                "domains": ["programming", "ai", "cloud"],
                "compare_with": "industry_standard",
                "suggest_resources": True
            }
        }
    }
    
    # Session Examples
    SESSION_EXAMPLES = {
        "create_session": {
            "summary": "Create a new conversation session",
            "description": "Start a new context-aware conversation",
            "value": {
                "title": "AI Project Discussion",
                "context": "Planning the new AI features for Q1",
                "participants": ["user", "assistant"],
                "metadata": {
                    "project": "second-brain",
                    "priority": "high"
                }
            }
        },
        "add_message": {
            "summary": "Add message to session",
            "description": "Add a message to an ongoing conversation",
            "value": {
                "session_id": "sess_123abc",
                "message": {
                    "role": "user",
                    "content": "What are the key features we discussed?",
                    "timestamp": "2025-01-14T10:30:00Z"
                }
            }
        }
    }


class APIDocumentation:
    """Enhanced API documentation with detailed examples"""
    
    @staticmethod
    def get_endpoint_docs() -> Dict[str, Any]:
        """Get comprehensive documentation for all endpoints"""
        return {
            "memories": {
                "description": """
                ## Memory Management API
                
                The memory endpoints handle creation, retrieval, updating, and deletion of memories.
                Second Brain supports three types of memories:
                
                - **Semantic**: Facts, concepts, general knowledge
                - **Episodic**: Personal experiences, events, meetings
                - **Procedural**: How-to instructions, procedures, workflows
                
                ### Key Features:
                - Vector embeddings for semantic search
                - Automatic tagging and categorization
                - Importance scoring
                - Rich metadata support
                - Relationship mapping between memories
                
                ### Authentication:
                All endpoints require an API key passed as a query parameter: `?api_key=YOUR_KEY`
                """,
                "examples": APIExample.MEMORY_CREATE_EXAMPLES
            },
            "search": {
                "description": """
                ## Search API
                
                Advanced search capabilities using multiple strategies:
                
                - **Semantic Search**: Find conceptually similar content using embeddings
                - **Keyword Search**: Traditional text matching
                - **Contextual Search**: Context-aware search with metadata filters
                - **Hybrid Search**: Combines multiple strategies for best results
                
                ### Search Features:
                - Similarity threshold configuration
                - Date range filtering
                - Tag-based filtering
                - Metadata queries
                - Result ranking and boosting
                
                ### Performance:
                - Cached results for common queries
                - Parallel search execution
                - Configurable result limits
                """,
                "examples": APIExample.SEARCH_EXAMPLES
            },
            "gdrive": {
                "description": """
                ## Google Drive Integration API
                
                Stream and process Google Drive content without storing files locally.
                
                ### Capabilities:
                - **OAuth 2.0 Authentication**: Secure Google account connection
                - **File Streaming**: Process files without downloading
                - **Real-time Sync**: Webhook-based change detection
                - **Multiple File Types**: Docs, Sheets, PDFs, Images
                
                ### Security:
                - Read-only access (drive.readonly scope)
                - Encrypted token storage
                - Automatic token refresh
                - Secure webhook endpoints
                
                ### Processing Pipeline:
                1. Stream file content from Drive
                2. Extract text (OCR for images/PDFs)
                3. Generate embeddings
                4. Create searchable memories
                5. Build knowledge graph relationships
                """,
                "examples": APIExample.GDRIVE_EXAMPLES
            },
            "bulk": {
                "description": """
                ## Bulk Operations API
                
                Efficiently handle large-scale operations on memories.
                
                ### Use Cases:
                - Import existing knowledge bases
                - Batch updates to memories
                - Mass tagging operations
                - Bulk deletion with filters
                
                ### Performance Optimizations:
                - Batch database operations
                - Parallel processing
                - Transaction support
                - Progress tracking for long operations
                """,
                "examples": APIExample.BULK_EXAMPLES
            },
            "analysis": {
                "description": """
                ## Analysis & Insights API
                
                Extract insights and patterns from your knowledge base.
                
                ### Analysis Types:
                - **Pattern Detection**: Identify recurring themes
                - **Knowledge Gaps**: Find missing information
                - **Trend Analysis**: Track changes over time
                - **Relationship Mapping**: Visualize connections
                
                ### Features:
                - Customizable analysis parameters
                - Export results to various formats
                - Scheduled analysis jobs
                - Comparative analysis across time periods
                """,
                "examples": APIExample.ANALYSIS_EXAMPLES
            },
            "sessions": {
                "description": """
                ## Conversation Sessions API
                
                Manage context-aware conversations with memory integration.
                
                ### Features:
                - Persistent conversation context
                - Memory-augmented responses
                - Multi-turn dialogue support
                - Session branching and merging
                
                ### Context Management:
                - Automatic context summarization
                - Relevant memory retrieval
                - Dynamic context window adjustment
                - Cross-session learning
                """,
                "examples": APIExample.SESSION_EXAMPLES
            }
        }
    
    @staticmethod
    def get_error_responses() -> Dict[int, Dict[str, Any]]:
        """Get standardized error response documentation"""
        return {
            400: {
                "description": "Bad Request - Invalid parameters or malformed request",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Invalid memory type. Must be one of: semantic, episodic, procedural",
                            "error_code": "INVALID_MEMORY_TYPE",
                            "request_id": "req_123abc"
                        }
                    }
                }
            },
            401: {
                "description": "Unauthorized - Invalid or missing API key",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Invalid API key provided",
                            "error_code": "INVALID_API_KEY",
                            "request_id": "req_456def"
                        }
                    }
                }
            },
            404: {
                "description": "Not Found - Resource does not exist",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Memory with ID 'mem_789' not found",
                            "error_code": "RESOURCE_NOT_FOUND",
                            "request_id": "req_789ghi"
                        }
                    }
                }
            },
            429: {
                "description": "Too Many Requests - Rate limit exceeded",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Rate limit exceeded. Try again in 60 seconds",
                            "error_code": "RATE_LIMIT_EXCEEDED",
                            "retry_after": 60,
                            "request_id": "req_101jkl"
                        }
                    }
                }
            },
            500: {
                "description": "Internal Server Error",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "An unexpected error occurred",
                            "error_code": "INTERNAL_ERROR",
                            "request_id": "req_202mno"
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_rate_limits() -> Dict[str, Any]:
        """Get rate limiting documentation"""
        return {
            "description": """
            ## Rate Limiting
            
            API endpoints are rate-limited to ensure fair usage and system stability.
            
            ### Limits by Endpoint:
            - **Memory Creation**: 100 requests/minute
            - **Search**: 200 requests/minute
            - **Bulk Operations**: 10 requests/minute
            - **Analysis**: 20 requests/minute
            - **Google Drive Sync**: 30 requests/minute
            
            ### Rate Limit Headers:
            - `X-RateLimit-Limit`: Maximum requests allowed
            - `X-RateLimit-Remaining`: Requests remaining
            - `X-RateLimit-Reset`: Unix timestamp when limit resets
            
            ### Handling Rate Limits:
            When rate limited, implement exponential backoff:
            ```python
            import time
            import random
            
            def retry_with_backoff(func, max_retries=3):
                for i in range(max_retries):
                    try:
                        return func()
                    except RateLimitError as e:
                        if i == max_retries - 1:
                            raise
                        wait_time = (2 ** i) + random.uniform(0, 1)
                        time.sleep(wait_time)
            ```
            """
        }
    
    @staticmethod
    def get_authentication_guide() -> Dict[str, Any]:
        """Get authentication documentation"""
        return {
            "description": """
            ## Authentication
            
            Second Brain uses API key authentication for all endpoints.
            
            ### Getting an API Key:
            1. Sign up at the dashboard
            2. Navigate to Settings > API Keys
            3. Generate a new key with appropriate permissions
            
            ### Using Your API Key:
            Include the key as a query parameter in all requests:
            ```
            GET https://api.second-brain.com/memories?api_key=YOUR_KEY
            ```
            
            ### Security Best Practices:
            - **Never commit API keys** to version control
            - **Use environment variables** for key storage
            - **Rotate keys regularly** (recommended: every 90 days)
            - **Use separate keys** for development and production
            - **Implement IP whitelisting** for production keys
            
            ### Example with Python:
            ```python
            import os
            import requests
            
            API_KEY = os.environ.get('SECOND_BRAIN_API_KEY')
            BASE_URL = 'https://api.second-brain.com'
            
            def make_request(endpoint, method='GET', **kwargs):
                url = f"{BASE_URL}{endpoint}"
                params = kwargs.get('params', {})
                params['api_key'] = API_KEY
                kwargs['params'] = params
                
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            ```
            """
        }


def apply_documentation_to_app(app: FastAPI) -> None:
    """Apply comprehensive documentation to FastAPI app"""
    
    docs = APIDocumentation()
    
    # Update OpenAPI schema with detailed descriptions
    app.description = """
    # Second Brain API v4.2.3
    
    A cognitive architecture for intelligent memory management and knowledge synthesis.
    
    ## 📚 Documentation
    - **[Comprehensive API Documentation with Examples](/api-docs)** - Full reference with code examples
    - **[Interactive API Explorer](/docs)** - Try out endpoints with Swagger UI
    - **[Dashboard](/dashboard)** - Web interface for memory management
    
    ## Key Features
    - 🧠 **Three Memory Types**: Semantic, Episodic, and Procedural
    - 🔍 **Advanced Search**: Semantic, contextual, and hybrid search strategies
    - 📁 **Google Drive Integration**: Stream and process files without local storage
    - 📊 **Analytics & Insights**: Pattern detection and knowledge gap analysis
    - 🔄 **Real-time Sync**: Webhook-based change detection
    - 🔐 **Enterprise Security**: OAuth 2.0, encrypted storage, rate limiting
    
    ## Getting Started
    1. Obtain an API key from the dashboard
    2. Include the key in all requests as a query parameter
    3. Start with creating memories, then explore search and analysis
    
    ## Quick Start Example
    ```python
    import requests
    
    # Your API key
    API_KEY = "your_api_key_here"
    
    # Create a memory
    response = requests.post(
        "http://localhost:8001/api/v1/memories",
        params={"api_key": API_KEY},
        json={
            "content": "Second Brain is an AI-powered memory system",
            "memory_type": "semantic",
            "tags": ["ai", "memory", "knowledge"]
        }
    )
    print(response.json())
    ```
    
    ## Support
    - Documentation: [API Docs](/api-docs)
    - GitHub: [Issues & Features](https://github.com/raold/second-brain)
    - Dashboard: [Web Interface](/dashboard)
    """
    
    # Add tags with descriptions
    app.openapi_tags = [
        {
            "name": "Memories",
            "description": docs.get_endpoint_docs()["memories"]["description"]
        },
        {
            "name": "Search",
            "description": docs.get_endpoint_docs()["search"]["description"]
        },
        {
            "name": "Google Drive",
            "description": docs.get_endpoint_docs()["gdrive"]["description"]
        },
        {
            "name": "Bulk Operations",
            "description": docs.get_endpoint_docs()["bulk"]["description"]
        },
        {
            "name": "Analysis",
            "description": docs.get_endpoint_docs()["analysis"]["description"]
        },
        {
            "name": "Sessions",
            "description": docs.get_endpoint_docs()["sessions"]["description"]
        },
        {
            "name": "Health",
            "description": "System health and monitoring endpoints"
        }
    ]
    
    # Add authentication guide to docs
    if not hasattr(app, 'openapi'):
        app.openapi = lambda: None
        
    original_openapi = app.openapi
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = original_openapi()
        
        # Add authentication documentation
        openapi_schema["info"]["x-authentication"] = docs.get_authentication_guide()
        
        # Add rate limiting documentation
        openapi_schema["info"]["x-rate-limits"] = docs.get_rate_limits()
        
        # Add global error responses
        openapi_schema["components"]["responses"] = docs.get_error_responses()
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi