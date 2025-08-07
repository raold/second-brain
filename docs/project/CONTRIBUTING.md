# Contributing to Second Brain v3.0.0

## 🤝 Welcome Contributors

Thank you for your interest in contributing to Second Brain! This document provides guidelines for contributing to our enterprise-ready AI memory system.

## 📋 Project Overview

Second Brain v3.0.0 is an **enterprise-ready AI memory system** built with clean architecture principles, designed for scalability, maintainability, and production deployment.

### Key Principles
- **Clean Architecture**: Domain-driven design with clear separation of concerns
- **Event Sourcing**: Complete audit trail and event-driven architecture
- **Test-Driven Development**: Comprehensive test coverage at all layers
- **Enterprise-Ready**: Production-grade observability, caching, and messaging
- **API-First**: Well-documented RESTful API with OpenAPI specification

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Redis 7+
- RabbitMQ 3.12+
- MinIO (or S3-compatible storage)
- Docker & Docker Compose (optional but recommended)

### Development Setup

#### Using Docker Compose (Recommended)
```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Install dependencies in virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-v3.txt
pip install -r requirements-dev.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn src.main:app --reload
```

#### Manual Setup
```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-v3.txt
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start required services (PostgreSQL, Redis, RabbitMQ, MinIO)
# ... (configure each service)

# Run migrations
alembic upgrade head

# Run tests
pytest

# Start development server
uvicorn src.main:app --reload
```

## 🏗️ Architecture Overview

```
src/
├── domain/           # Core business logic
│   ├── models/      # Entities, value objects
│   ├── events/      # Domain events
│   └── repositories/# Repository interfaces
├── application/      # Use cases and DTOs
│   ├── use_cases/   # Business operations
│   └── dto/         # Data transfer objects
├── infrastructure/   # External services
│   ├── database/    # PostgreSQL repositories
│   ├── caching/     # Redis implementation
│   ├── messaging/   # RabbitMQ integration
│   └── storage/     # MinIO/S3 client
└── api/             # FastAPI application
    ├── routes/      # API endpoints
    └── middleware/  # Cross-cutting concerns
```

### Development Guidelines

1. **Follow Clean Architecture**: Dependencies should always point inward
2. **Domain First**: Start with domain models and business logic
3. **Test Coverage**: Maintain >90% test coverage
4. **Type Hints**: Use Python type hints throughout
5. **Documentation**: Update docs for all public APIs

## 🌿 Development Workflow

### Branch Strategy
- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/*`**: Individual feature branches
- **`hotfix/*`**: Emergency fixes for production

### Contributing Process

#### 1. Create Feature Branch
```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name
```

#### 2. Development
```bash
# Run tests during development
pytest tests/unit/  # Fast unit tests
pytest tests/integration/  # Integration tests
pytest  # All tests

# Check code quality
black src/ tests/
ruff check src/ tests/
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

#### 3. Commit Guidelines
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```bash
# Features
git commit -m "feat: add bulk memory import"

# Fixes
git commit -m "fix: resolve cache invalidation issue"

# Documentation
git commit -m "docs: update API documentation"

# Performance
git commit -m "perf: optimize vector search query"

# Refactoring
git commit -m "refactor: simplify repository pattern"
```

#### 4. Create Pull Request
1. Push your feature branch
2. Create PR against `develop` branch
3. Ensure all CI checks pass
4. Request review from maintainers

### Code Review Checklist
- [ ] Tests pass and coverage maintained
- [ ] Code follows project style guide
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Breaking changes documented

## 🧪 Testing

### Test Structure
```
tests/
├── unit/          # Domain and application logic
├── integration/   # Infrastructure and API
├── e2e/          # End-to-end scenarios
└── fixtures/     # Test data and mocks
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific suite
pytest tests/unit/
pytest tests/integration/
pytest -m "not slow"

# Watch mode
pytest-watch
```

### Writing Tests
```python
# Example unit test
def test_memory_creation():
    """Test memory entity creation with valid data."""
    memory = Memory.create(
        content="Test content",
        user_id=uuid4(),
        tags=["test"]
    )
    
    assert memory.content == "Test content"
    assert len(memory.events) == 1
    assert isinstance(memory.events[0], MemoryCreatedEvent)
```

## 📚 Documentation

### API Documentation
- Update OpenAPI annotations on routes
- Include request/response examples
- Document error scenarios

### Code Documentation
- Use docstrings for all public functions
- Include type hints
- Add usage examples where helpful

### Architecture Documentation
- Update architecture diagrams for significant changes
- Document design decisions in ADRs (Architecture Decision Records)

## 🔍 Code Quality

### Style Guide
- Follow PEP 8 with Black formatting
- Use meaningful variable names
- Keep functions focused and small
- Apply SOLID principles

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Security
- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Follow OWASP guidelines

## 🚀 Release Process

1. **Feature Freeze**: Stop adding features to release branch
2. **Testing**: Run full test suite including performance tests
3. **Documentation**: Update changelog and version numbers
4. **Tag Release**: Create git tag following semantic versioning
5. **Deploy**: Use CI/CD pipeline for deployment

## 📞 Getting Help

- **Documentation**: Check `/docs` directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our community (link in README)

## 🙏 Recognition

Contributors will be recognized in:
- Release notes
- Contributors file
- Project documentation

Thank you for contributing to Second Brain! 🧠