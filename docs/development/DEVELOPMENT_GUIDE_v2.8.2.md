# Second Brain v2.8.2 - Development Guide 👨‍💻

**Version**: 2.8.2  
**Guide Version**: 1.0  
**Last Updated**: 2025-07-23

## 🚀 Getting Started

### Prerequisites

**System Requirements**
```bash
# Minimum Requirements
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB free
- OS: Ubuntu 20.04+ / macOS 12+ / Windows 10+

# Recommended for Development
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 50GB+ SSD
- GPU: NVIDIA GPU for ML development (optional)
```

**Software Dependencies**
```bash
# Required
- Python 3.11+
- PostgreSQL 16
- pgvector extension
- Git 2.30+
- Docker 20+ (optional but recommended)

# Development Tools
- VSCode or PyCharm
- Pre-commit hooks
- Make/Task runner
```

### Development Environment Setup

#### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

#### 2. Database Setup

```bash
# PostgreSQL with pgvector
sudo apt-get install postgresql-16 postgresql-16-pgvector

# Create database
createdb second_brain_dev
psql -d second_brain_dev -c "CREATE EXTENSION vector;"

# Run migrations
python scripts/migrate.py upgrade
```

#### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
DATABASE_URL=postgresql://user:password@localhost/second_brain_dev
API_KEY=your-dev-api-key
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│                   (FastAPI + Auth)                          │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
    ┌─────────▼─────────┐           ┌────────▼──────────┐
    │   Core Services   │           │   ML Services     │
    │  - Memory CRUD    │           │  - NLP Pipeline   │
    │  - Search Engine  │           │  - Topic Modeling │
    │  - Graph Builder  │           │  - Embeddings     │
    └─────────┬─────────┘           └────────┬──────────┘
              │                               │
    ┌─────────▼───────────────────────────────▼─────────┐
    │              Data Access Layer                    │
    │            (AsyncPG + pgvector)                  │
    └───────────────────────┬───────────────────────────┘
                            │
    ┌───────────────────────▼───────────────────────────┐
    │                PostgreSQL Database                │
    │              with pgvector extension              │
    └───────────────────────────────────────────────────┘
```

### Code Organization

```
second-brain/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── version.py           # Version management
│   ├── config.py            # Configuration
│   ├── models/              # Pydantic models
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   ├── database/            # Database operations
│   ├── ml/                  # Machine learning
│   └── utils/               # Utilities
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── performance/         # Performance tests
├── scripts/
│   ├── migrate.py           # Database migrations
│   ├── benchmark.py         # Performance benchmarks
│   └── setup.py             # Setup utilities
├── docs/                    # Documentation
├── .github/                 # GitHub Actions
└── docker/                  # Docker configurations
```

## 💻 Development Workflow

### 1. Feature Development

#### Branch Strategy

```bash
# Feature branches
git checkout -b feature/memory-compression

# Bug fixes
git checkout -b fix/query-performance

# Documentation
git checkout -b docs/api-reference

# Experiments
git checkout -b experiment/new-embedding-model
```

#### Coding Standards

**Python Style Guide**
```python
# Follow PEP 8 with these additions:
# - Type hints for all functions
# - Docstrings for all public methods
# - Maximum line length: 100 characters
# - Use Black for formatting

from typing import List, Optional, Dict
from app.models import Memory, SearchResult

async def search_memories(
    query: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """
    Search memories using vector similarity and filters.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        filters: Optional filters to apply
        
    Returns:
        List of search results ordered by relevance
        
    Raises:
        ValueError: If query is empty
        DatabaseError: If search fails
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
        
    # Implementation...
```

**Import Organization**
```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local imports
from app.config import settings
from app.models import Memory
from app.services import MemoryService
```

### 2. Testing Requirements

#### Test Structure

```python
# tests/unit/test_memory_service.py
import pytest
from unittest.mock import Mock, AsyncMock

from app.services import MemoryService
from app.models import Memory


class TestMemoryService:
    """Test cases for MemoryService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked dependencies."""
        return MemoryService(db=AsyncMock())
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, service):
        """Test successful memory creation."""
        # Arrange
        memory_data = {
            "content": "Test memory",
            "metadata": {"source": "test"}
        }
        
        # Act
        result = await service.create_memory(memory_data)
        
        # Assert
        assert result.id is not None
        assert result.content == "Test memory"
```

#### Test Coverage Requirements

```yaml
coverage_requirements:
  overall: 85%
  new_code: 90%
  critical_paths: 95%
  
excluded_from_coverage:
  - "*/tests/*"
  - "*/migrations/*"
  - "*/__pycache__/*"
  - "*/venv/*"
```

### 3. Performance Optimization

#### Profiling Code

```python
# Use decorators for performance monitoring
from app.utils.profiling import profile_async

@profile_async
async def expensive_operation():
    """Operation that needs performance monitoring."""
    # Your code here
    pass

# Results logged automatically:
# [PROFILE] expensive_operation took 1.234s
```

#### Database Query Optimization

```python
# Bad: N+1 query problem
memories = await get_all_memories()
for memory in memories:
    relationships = await get_relationships(memory.id)
    
# Good: Single query with joins
memories_with_relationships = await db.fetch("""
    SELECT m.*, 
           array_agg(r.*) as relationships
    FROM memories m
    LEFT JOIN relationships r ON m.id = r.memory_id
    GROUP BY m.id
""")
```

### 4. API Development

#### Endpoint Structure

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.models import Memory, MemoryCreate
from app.services import MemoryService
from app.auth import verify_api_key

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])

@router.post("/", response_model=Memory)
async def create_memory(
    memory: MemoryCreate,
    service: MemoryService = Depends(get_memory_service),
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new memory.
    
    - **content**: The memory content
    - **metadata**: Optional metadata
    
    Returns the created memory with ID.
    """
    try:
        return await service.create_memory(memory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

#### Error Handling

```python
# Custom exception classes
class MemoryNotFoundError(Exception):
    """Raised when memory is not found."""
    pass

class QuotaExceededError(Exception):
    """Raised when user quota is exceeded."""
    pass

# Global exception handlers
@app.exception_handler(MemoryNotFoundError)
async def memory_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Memory not found", "id": str(exc)}
    )
```

### 5. Machine Learning Integration

#### Model Management

```python
# app/ml/models.py
from typing import Optional
import torch
from transformers import AutoModel

class ModelManager:
    """Manages ML model lifecycle."""
    
    def __init__(self):
        self._models = {}
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
    
    async def load_model(
        self, 
        model_name: str, 
        model_class: Optional[type] = None
    ):
        """Load model with caching and lazy loading."""
        if model_name in self._models:
            return self._models[model_name]
            
        model = (model_class or AutoModel).from_pretrained(model_name)
        model.to(self._device)
        model.eval()
        
        self._models[model_name] = model
        return model
```

#### Feature Development

```python
# Adding new NLP features
class SentimentAnalyzer:
    """Analyze sentiment of memories."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.model = None
        
    async def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment with confidence scores.
        
        Returns:
            {
                "positive": 0.8,
                "negative": 0.1,
                "neutral": 0.1
            }
        """
        if not self.model:
            self.model = await self.model_manager.load_model(
                "nlptown/bert-base-multilingual-uncased-sentiment"
            )
            
        # Implementation...
```

## 🐛 Debugging Guide

### Local Debugging

```python
# Enable debug mode in .env
DEBUG=true
LOG_LEVEL=DEBUG

# Use debugger
import pdb; pdb.set_trace()  # Standard debugger
import ipdb; ipdb.set_trace()  # Enhanced debugger

# Async debugging
import asyncio
import aiodebug
aiodebug.log_slow_callbacks.enable(0.05)
```

### Logging Best Practices

```python
import logging
from app.utils.logging import get_logger

logger = get_logger(__name__)

class MemoryService:
    async def process_memory(self, memory_id: str):
        logger.info(f"Processing memory", extra={
            "memory_id": memory_id,
            "timestamp": datetime.utcnow()
        })
        
        try:
            # Process...
            logger.debug("Memory processed successfully")
        except Exception as e:
            logger.error(
                f"Failed to process memory",
                exc_info=True,
                extra={"memory_id": memory_id}
            )
            raise
```

### Performance Debugging

```bash
# CPU profiling
python -m cProfile -o profile.out app/main.py
snakeviz profile.out

# Memory profiling
pip install memory-profiler
python -m memory_profiler app/main.py

# Async profiling
pip install aiomonitor
# Add to your code:
import aiomonitor
aiomonitor.start_monitor(loop=asyncio.get_event_loop())
```

## 🔧 Configuration Management

### Environment Variables

```python
# app/config.py
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    db_pool_min: int = Field(10, env="DB_POOL_MIN")
    db_pool_max: int = Field(100, env="DB_POOL_MAX")
    
    # API
    api_key: str = Field(..., env="API_KEY")
    rate_limit: int = Field(100, env="RATE_LIMIT")
    
    # ML Models
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    
    # Feature Flags
    enable_webhooks: bool = Field(False, env="ENABLE_WEBHOOKS")
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Feature Flags

```python
# app/features.py
from app.config import settings

class FeatureFlags:
    """Manage feature flags."""
    
    @staticmethod
    def is_enabled(feature: str) -> bool:
        """Check if feature is enabled."""
        return getattr(settings, f"enable_{feature}", False)
    
    @staticmethod
    def require_feature(feature: str):
        """Decorator to require feature flag."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if not FeatureFlags.is_enabled(feature):
                    raise HTTPException(
                        status_code=501,
                        detail=f"Feature '{feature}' not enabled"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

## 📦 Dependency Management

### Adding Dependencies

```bash
# Production dependencies
pip install package-name
pip freeze | grep package-name >> requirements.txt

# Development dependencies
pip install --dev package-name
pip freeze | grep package-name >> requirements-dev.txt

# Update all dependencies
pip install pip-tools
pip-compile requirements.in
pip-sync requirements.txt
```

### Security Scanning

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update vulnerable packages
pip install pip-audit
pip-audit --fix
```

## 🚀 Deployment Preparation

### Build Process

```bash
# Run all checks
make check

# Includes:
# - Linting (black, flake8, mypy)
# - Tests (pytest)
# - Coverage check
# - Security scan
# - Documentation build
```

### Performance Optimization

```python
# Compile Python files
python -m compileall app/

# Optimize imports
isort app/ tests/

# Remove debug code
python scripts/remove_debug.py

# Minimize Docker image
docker build -f Dockerfile.production -t second-brain:v2.8.2 .
```

## 📚 Documentation

### Code Documentation

```python
def complex_algorithm(
    data: List[Dict[str, Any]],
    threshold: float = 0.8,
    max_iterations: int = 100
) -> Tuple[List[int], float]:
    """
    Perform complex algorithmic processing on data.
    
    This algorithm implements a modified k-means clustering
    with adaptive thresholding for memory grouping.
    
    Args:
        data: List of memory dictionaries with embeddings
        threshold: Similarity threshold for grouping (0.0-1.0)
        max_iterations: Maximum iterations for convergence
        
    Returns:
        Tuple containing:
            - List of cluster assignments
            - Final inertia value
            
    Example:
        >>> data = [{"id": 1, "embedding": [0.1, 0.2, ...]}, ...]
        >>> clusters, inertia = complex_algorithm(data, 0.85)
        >>> print(f"Found {len(set(clusters))} clusters")
        
    Note:
        This algorithm has O(n²) complexity and should not
        be used for datasets larger than 10,000 items.
    """
```

### API Documentation

```python
@router.post(
    "/analyze",
    response_model=AnalysisResult,
    summary="Analyze memory content",
    description="""
    Perform comprehensive analysis on memory content including:
    - Topic extraction
    - Entity recognition
    - Sentiment analysis
    - Relationship detection
    """,
    response_description="Analysis results with confidence scores"
)
```

## 🤝 Contributing

### Pull Request Process

1. **Create feature branch**
2. **Implement changes with tests**
3. **Run local checks**: `make check`
4. **Update documentation**
5. **Submit PR with description**
6. **Address review feedback**
7. **Squash commits if needed**
8. **Merge after approval**

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Performance impact assessed
- [ ] Security implications reviewed
- [ ] Backward compatibility maintained
- [ ] Error handling implemented
- [ ] Logging added appropriately
- [ ] Configuration documented

## 🆘 Getting Help

### Resources

- **Documentation**: `/docs`
- **API Reference**: `/docs/api`
- **Discord**: [Join our community]
- **Issues**: GitHub Issues
- **Wiki**: GitHub Wiki

### Common Issues

**Database Connection**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify pgvector installed
psql -d second_brain_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Import Errors**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or use development install
pip install -e .
```

**Performance Issues**
```bash
# Check for missing indexes
python scripts/analyze_db.py

# Profile slow queries
export EXPLAIN_QUERIES=true
```

This development guide provides comprehensive information for contributing to Second Brain v2.8.2. For specific questions, reach out to the development team or check our documentation.