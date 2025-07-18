# Contributing to Second Brain

## 🤝 Welcome Contributors

Thank you for your interest in contributing to Second Brain! This document provides guidelines for contributing to this single-user AI memory system.

## 📋 Project Overview

Second Brain is a **personal AI memory system** designed for **single-user deployments**. It's not intended for multi-user or enterprise scenarios.

### Key Principles
- **Simplicity**: Minimal dependencies, clean architecture
- **Personal Use**: Single-user focus, not multi-tenant
- **Performance**: Sub-100ms search times
- **Reliability**: Comprehensive testing and quality standards

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key (optional, can use mock mode)

### Development Setup
```bash
# Clone repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp config/environments/env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/setup/setup_database.py

# Run tests
pytest tests/ -v

# Start development server
uvicorn app.app:app --reload
```

## 📁 Repository Structure

```
second-brain/
├── app/                    # Core application code
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   ├── architecture/      # System design
│   ├── deployment/        # Deployment guides
│   ├── development/       # Development guides
│   └── user/              # User guides
├── tests/                 # All testing code
│   ├── integration/       # Integration tests
│   ├── unit/             # Unit tests
│   ├── performance/      # Performance tests
│   └── fixtures/         # Test utilities
├── scripts/               # Utility scripts
├── config/                # Configuration files
└── README.md             # Main documentation
```

## 🧪 Testing Guidelines

### Test Organization
- **Unit Tests**: `tests/unit/` - Individual function testing
- **Integration Tests**: `tests/integration/` - API endpoint testing
- **Performance Tests**: `tests/performance/` - Benchmarking

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test category
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Performance benchmarks
pytest tests/performance/ -v
```

### Test Requirements
- ✅ All new features must include tests
- ✅ Maintain >80% code coverage
- ✅ Integration tests for all API endpoints
- ✅ Performance tests for critical paths

## 📝 Code Standards

### Python Style
- **Formatter**: Black (configured in pyproject.toml)
- **Linter**: Ruff (configured in ruff.toml)
- **Type Hints**: Required for all functions
- **Docstrings**: Required for all public functions

### Code Quality
```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature description"

# Push and create pull request
git push origin feature/your-feature-name
```

## 🔄 Development Workflow

### 1. Issue Creation
- Check existing issues before creating new ones
- Use issue templates for bugs and features
- Provide clear reproduction steps for bugs

### 2. Development Process
1. **Fork and Clone**: Fork the repository and clone locally
2. **Branch**: Create feature branch from `main`
3. **Develop**: Write code following style guidelines
4. **Test**: Add tests and ensure all tests pass
5. **Document**: Update documentation as needed
6. **Commit**: Use conventional commit messages
7. **Push**: Push to your fork and create pull request

### 3. Pull Request Process
- Fill out the PR template completely
- Ensure CI/CD pipeline passes
- Request review from maintainers
- Address review feedback
- Squash commits before merge

## 🐛 Bug Reports

### Before Reporting
- Check existing issues
- Verify with latest version
- Test with minimal reproduction case

### Bug Report Template
```markdown
## Bug Description
Clear description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Windows 11, Ubuntu 20.04]
- Python: [e.g., 3.10.6]
- Version: [e.g., 2.0.2]
- Database: [e.g., PostgreSQL 15.1]
```

## ✨ Feature Requests

### Feature Request Template
```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed?

## Proposed Implementation
How should this feature work?

## Alternatives Considered
What other approaches were considered?

## Additional Context
Any other relevant information
```

## 📚 Documentation

### Documentation Standards
- **README**: Keep updated with latest features
- **API Docs**: OpenAPI specification in `app/docs.py`
- **Architecture**: Document design decisions
- **Deployment**: Update deployment guides

### Documentation Structure
- **User-facing**: Clear, example-driven documentation
- **Developer-facing**: Technical implementation details
- **API Reference**: Complete OpenAPI specification

## 🔒 Security

### Security Guidelines
- Never commit secrets or API keys
- Use environment variables for configuration
- Report security issues privately to security@oldham.io
- Follow responsible disclosure practices

### Security Scope
- **In Scope**: Personal data protection, API security
- **Out of Scope**: Multi-user security, enterprise compliance

## 📋 Release Process

### Version Management
- **Configuration-Driven**: Use centralized `docs/releases/version_config.json`
- **Automated Release Preparation**: Use `scripts/version_manager.py`
- **Professional Documentation**: Auto-generated release notes

### Release Steps
1. **Configure Version**: Add version info to `docs/releases/version_config.json`
2. **Prepare Release**: `python scripts/version_manager.py prepare X.Y.Z`
3. **Execute Git Commands**: Follow the generated workflow commands
4. **GitHub Release**: Use the auto-generated release notes

## 🎯 Areas for Contribution

### High Priority
- **Performance Optimization**: Response time improvements
- **Test Coverage**: Additional edge cases
- **Documentation**: User guides and examples
- **Security**: Input validation and rate limiting

### Medium Priority
- **Monitoring**: Performance metrics and logging
- **Error Handling**: Better error messages
- **Developer Tools**: Development utilities
- **CI/CD**: Pipeline improvements

### Low Priority
- **Advanced Features**: Export capabilities
- **Integrations**: Additional data sources
- **UI/UX**: Web interface (future consideration)

## 📞 Getting Help

### Community
- **Issues**: GitHub issues for bugs and features
- **Discussions**: GitHub discussions for questions
- **Email**: Technical questions to development team

### Resources
- **Documentation**: [docs/](docs/)
- **API Reference**: Start server and visit `/docs`
- **Architecture**: [docs/architecture/](docs/architecture/)
- **Examples**: [docs/user/](docs/user/)

---

**Thank you for contributing to Second Brain!** 🧠✨

*This document is maintained by the development team and updated regularly.*
