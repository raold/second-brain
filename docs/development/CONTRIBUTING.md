# Contributing to Second Brain v3.0.0

Thank you for your interest in contributing to Second Brain! 🎉

We welcome contributions of all kinds — bug fixes, new features, documentation improvements, and tests.

## Quick Start

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/yourusername/second-brain.git
cd second-brain
```

### 2. Set Up Virtual Environment (CRITICAL)

**ALWAYS use the project's virtual environment to ensure consistency:**

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Install dependencies
.venv/Scripts/python.exe -m pip install -r config/requirements.txt
.venv/Scripts/python.exe -m pip install -r config/requirements-dev.txt

# Verify setup
.venv/Scripts/python.exe scripts/test_runner.py --validation
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 4. Make Your Changes

Follow the project structure and coding standards. Test your changes locally.

### 5. Run Tests

```bash
# Run all tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Run specific test category
.venv/Scripts/python.exe -m pytest tests/unit/ -v

# Run with coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=app --cov-report=html
```

### 6. Commit Your Changes

Use conventional commits format:

```bash
# Feature
git commit -m "feat: add memory export functionality"

# Bug fix
git commit -m "fix: resolve database connection timeout"

# Documentation
git commit -m "docs: update API endpoint documentation"

# Tests
git commit -m "test: add unit tests for memory service"

# Refactoring
git commit -m "refactor: simplify authentication middleware"
```

### 7. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Open a Pull Request against the main branch
```

## Development Guidelines

### Project Structure

```
second-brain/
├── app/                  # Main application code
│   ├── core/            # Core functionality
│   ├── models/          # Data models
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   └── database.py      # Database management
├── config/              # Configuration files
├── scripts/             # Development scripts
├── tests/               # Test suite
└── docs/                # Documentation
```

### Code Style

- **Python**: Follow PEP 8
- **Formatting**: Use Black (line length 100)
- **Type Hints**: Use where beneficial
- **Docstrings**: Required for public functions

Example:
```python
from typing import Optional, List
from app.models.memory import Memory

async def search_memories(
    query: str,
    limit: int = 10,
    user_id: Optional[str] = None
) -> List[Memory]:
    """
    Search memories by query string.
    
    Args:
        query: Search query
        limit: Maximum results to return
        user_id: Optional user filter
        
    Returns:
        List of matching memories
    """
    # Implementation here
```

### Testing Requirements

All new features and bug fixes must include tests:

1. **Unit Tests**: For isolated components
2. **Integration Tests**: For API endpoints
3. **Edge Cases**: Handle errors and boundaries

Example test:
```python
import pytest
from app.services.memory_service import MemoryService

class TestMemoryService:
    @pytest.mark.asyncio
    async def test_create_memory(self, mock_database):
        service = MemoryService(database=mock_database)
        memory = await service.create_memory("Test content")
        assert memory.id is not None
        assert memory.content == "Test content"
```

### API Development

When adding new endpoints:

1. Create router in `app/routes/`
2. Add service logic in `app/services/`
3. Include request/response models
4. Add comprehensive tests
5. Update API documentation

### Database Changes

For database schema changes:

1. Create migration script in `scripts/migrations/`
2. Test migration on fresh database
3. Document the changes
4. Update relevant models

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally: `.venv/Scripts/python.exe -m pytest tests/`
- [ ] Code follows style guidelines
- [ ] New code has tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventions

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Comments added where needed
- [ ] Documentation updated
```

## Environment Variables

Key environment variables for development:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/secondbrain
USE_MOCK_DATABASE=false

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=your-api-key

# Security
API_TOKENS=test-token-1,test-token-2
SECRET_KEY=your-secret-key

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## Common Commands

```bash
# Run application
.venv/Scripts/python.exe -m uvicorn app.app:app --reload

# Run tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Format code
.venv/Scripts/python.exe -m black app/ tests/

# Type checking
.venv/Scripts/python.exe -m mypy app/

# Start services with Docker
docker-compose up -d postgres redis
```

## Getting Help

- **Issues**: Check existing [issues](https://github.com/yourusername/second-brain/issues) or create a new one
- **Discussions**: For ideas or questions, use GitHub Discussions
- **Documentation**: See `/docs` directory for detailed guides

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing private information

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Special thanks section

Thank you for contributing to Second Brain! 🧠