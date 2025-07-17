# Second Brain - Repository Structure

## 📁 **Directory Organization**

This document outlines the standardized directory structure for the Second Brain project, ensuring clean organization and maintainability.

```
second-brain/
├── 📁 app/                          # Core application code
│   ├── __init__.py                  # Package initialization
│   ├── app.py                       # Main FastAPI application
│   ├── database.py                  # Database operations
│   ├── database_mock.py             # Mock database for testing
│   ├── docs.py                      # OpenAPI documentation configuration
│   └── version.py                   # Version management
│
├── 📁 docs/                         # Project documentation
│   ├── api/                         # API-specific documentation
│   ├── architecture/                # System architecture documentation
│   ├── deployment/                  # Deployment guides and configs
│   ├── development/                 # Development guides and standards
│   └── user/                        # User guides and tutorials
│
├── 📁 tests/                        # All testing code
│   ├── integration/                 # Integration tests
│   ├── unit/                        # Unit tests
│   ├── performance/                 # Performance benchmarks
│   ├── fixtures/                    # Test fixtures and utilities
│   └── conftest.py                  # Pytest configuration
│
├── 📁 scripts/                      # Utility and automation scripts
│   ├── deployment/                  # Deployment automation
│   ├── development/                 # Development utilities
│   ├── maintenance/                 # Maintenance scripts
│   └── setup/                       # Initial setup scripts
│
├── 📁 config/                       # Configuration files
│   ├── docker/                      # Docker configurations
│   ├── database/                    # Database setup and migrations
│   └── environments/                # Environment-specific configs
│
├── 📁 tools/                        # Development and build tools
│   ├── linting/                     # Code quality tools
│   ├── monitoring/                  # Monitoring and logging tools
│   └── ci/                          # CI/CD pipeline configurations
│
├── 📄 README.md                     # Main project documentation
├── 📄 LICENSE                       # Project license (AGPLv3)
├── 📄 CHANGELOG.md                  # Version history and changes
├── 📄 SECURITY.md                   # Security policy and guidelines
├── 📄 CONTRIBUTING.md               # Contribution guidelines
├── 📄 requirements.txt              # Python dependencies
├── 📄 setup.py                      # Package setup configuration
├── 📄 .env.example                  # Environment variables template
├── 📄 .gitignore                    # Git ignore patterns
├── 📄 pytest.ini                    # Pytest configuration
└── 📄 ruff.toml                     # Code formatting configuration
```

## 📋 **File Organization Rules**

### **Root Directory**
- **Essential files only**: README, LICENSE, CHANGELOG, SECURITY
- **Configuration files**: Requirements, setup, environment templates
- **Build files**: Only top-level build and configuration files

### **Documentation (`docs/`)**
- **`api/`**: OpenAPI specs, endpoint documentation
- **`architecture/`**: System design, database schemas, diagrams
- **`deployment/`**: Docker, production setup, infrastructure
- **`development/`**: Contributing, coding standards, development setup
- **`user/`**: Usage guides, tutorials, examples

### **Testing (`tests/`)**
- **`integration/`**: End-to-end API tests, database integration
- **`unit/`**: Individual function and class tests
- **`performance/`**: Benchmarks, load tests, performance validation
- **`fixtures/`**: Test data, mock objects, shared utilities

### **Scripts (`scripts/`)**
- **`deployment/`**: Production deployment automation
- **`development/`**: Development workflow tools
- **`maintenance/`**: Database maintenance, cleanup utilities
- **`setup/`**: Initial project setup and installation

### **Configuration (`config/`)**
- **`docker/`**: Dockerfiles, docker-compose configurations
- **`database/`**: Schema definitions, migration scripts
- **`environments/`**: Environment-specific configuration templates

## 🔄 **Migration Strategy**

1. **Create new directory structure**
2. **Move files to appropriate locations**
3. **Update all file path references**
4. **Update import statements in Python code**
5. **Update documentation links**
6. **Test all functionality**
7. **Update CI/CD configurations**

## 📝 **Naming Conventions**

### **Files**
- **Python**: `snake_case.py`
- **Documentation**: `UPPERCASE.md` for root, `lowercase.md` for subdirectories
- **Configuration**: `lowercase.yml`, `lowercase.toml`
- **Scripts**: `snake_case.py` with descriptive names

### **Directories**
- **Lowercase with hyphens**: `api-docs/`, `integration-tests/`
- **Clear, descriptive names**: `user-guides/`, `deployment-configs/`

## 🧪 **Testing Organization**

### **Test Naming**
- **Integration**: `test_integration_*.py`
- **Unit**: `test_unit_*.py`  
- **Performance**: `test_performance_*.py`
- **API**: `test_api_*.py`

### **Test Structure**
```python
tests/
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_database_integration.py
│   └── test_openapi_validation.py
├── unit/
│   ├── test_database_operations.py
│   ├── test_version_management.py
│   └── test_response_models.py
└── performance/
    ├── test_search_performance.py
    └── test_memory_storage_benchmarks.py
```

---

**Maintained by**: Managing Director  
**Last Updated**: July 17, 2025  
**Version**: 2.0.2 (Phoenix)  
**Next Review**: Sprint 30
