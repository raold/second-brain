# Naming Conventions Reference - Second Brain CI/CD System

> **PERMANENT REFERENCE** - Ensures consistency across the entire project ecosystem

## 🎯 Purpose

This document establishes mandatory naming conventions for all CI/CD artifacts, development tools, and project assets. These conventions ensure:

- **Consistency**: Predictable naming across all project components
- **Automation**: Tools can rely on standardized patterns
- **Discoverability**: Easy to find and understand file purposes
- **Scalability**: Naming scales with project growth

## 📋 Table of Contents

1. [GitHub Actions Workflows](#github-actions-workflows)
2. [Test Naming Conventions](#test-naming-conventions)  
3. [Script Naming Conventions](#script-naming-conventions)
4. [Environment Variables](#environment-variables)
5. [Documentation Files](#documentation-files)
6. [Configuration Files](#configuration-files)
7. [Docker and Containerization](#docker-and-containerization)
8. [Database and Migration Files](#database-and-migration-files)
9. [Validation and Enforcement](#validation-and-enforcement)

---

## 🔄 GitHub Actions Workflows

### Pattern: `{stage}-{purpose}-{scope}.yml`

#### CI Workflows (Continuous Integration)
```
ci-smoke-tests.yml           # Critical path validation (<60s)
ci-core-validation.yml       # Fast feedback loop (<5min)
ci-comprehensive-tests.yml   # Full test suite (<15min)
ci-security-quality.yml      # Code quality and security
ci-performance-tests.yml     # Load testing and benchmarks
ci-tiered.yml               # Multi-stage tiered testing
```

#### CD Workflows (Continuous Deployment)
```
cd-staging-deployment.yml    # Staging environment deployment
cd-production-release.yml    # Production deployment with approval
cd-hotfix-deployment.yml     # Emergency hotfix deployment
cd-rollback-recovery.yml     # Automated rollback procedures
```

#### Specialized Workflows
```
maintenance-dependency-update.yml    # Automated dependency updates
security-vulnerability-scan.yml      # Security scanning
docs-auto-generation.yml            # Documentation updates
release-notes-generation.yml        # Automated release notes
```

### Workflow Job Naming
```yaml
jobs:
  smoke-tests:           # Snake case, descriptive
    name: "🔥 Critical Path Validation"
    
  security-scan:         # Action type clearly indicated
    name: "🔒 Security Scan"
    
  deploy-production:     # Environment explicitly named
    name: "🚀 Deploy to Production"
```

### Workflow Step Naming
```yaml
steps:
  - name: "📥 Checkout Code"        # Action icon + verb + object
  - name: "🐍 Setup Python"        # Tool icon + action
  - name: "⚡ Install Dependencies"  # Speed icon for optimization
  - name: "🧪 Run Unit Tests"       # Test icon + test type
  - name: "📊 Generate Report"      # Report icon + action
```

---

## 🧪 Test Naming Conventions

### Test File Naming: `test_{feature}_{aspect}.py`

#### Unit Tests (`tests/unit/`)
```
test_models.py                    # Core model testing
test_basic_functionality.py       # Basic feature validation
test_memory_service.py            # Service-specific tests
test_api_endpoints.py             # API endpoint validation
test_error_handling.py            # Error handling scenarios
test_security_audit.py           # Security-focused tests
test_dependency_injection.py     # DI pattern validation
```

#### Integration Tests (`tests/integration/`)
```
test_memory_workflow.py           # End-to-end workflows
test_api_integration.py           # API integration flows
test_database_operations.py       # Database interaction tests
test_external_services.py         # Third-party integrations
test_security_validation.py       # Security integration tests
```

#### Validation Tests (`tests/validation/`)
```
test_comprehensive_validation.py  # Environment validation
test_code_quality.py             # Code quality checks
test_docker_deployment.py         # Docker environment tests
test_environment_setup.py         # Development environment
```

#### Performance Tests (`tests/performance/`)
```
test_load_scenarios.py           # Load testing scenarios
test_performance_benchmark.py    # Performance benchmarks
test_enterprise_load.py          # Enterprise-scale testing
test_memory_usage.py             # Memory profiling tests
```

### Test Function Naming: `test_{action}_{condition}_{expected_result}`

```python
# Memory model tests
def test_memory_creation_basic():
def test_memory_creation_with_all_fields():
def test_memory_validation_invalid_type_raises_error():
def test_memory_serialization_produces_valid_dict():

# API endpoint tests  
def test_health_endpoint_returns_200_status():
def test_memory_create_valid_data_returns_created():
def test_memory_create_invalid_data_returns_400():
def test_auth_required_endpoint_without_token_returns_401():

# Service layer tests
def test_memory_service_create_valid_memory_succeeds():
def test_memory_service_duplicate_detection_prevents_creation():
def test_memory_service_search_empty_query_returns_all():
```

### Test Class Naming: `Test{FeatureName}{Aspect}`

```python
class TestMemoryModel:                 # Model testing
class TestMemoryService:               # Service testing  
class TestHealthEndpoints:             # Endpoint testing
class TestAuthenticationFlow:          # Flow testing
class TestDatabaseOperations:          # Database testing
class TestSecurityValidation:          # Security testing
```

### Test Markers: `@pytest.mark.{category}`

```python
@pytest.mark.unit                     # Unit test marker
@pytest.mark.integration              # Integration test marker
@pytest.mark.validation               # Validation test marker
@pytest.mark.performance              # Performance test marker
@pytest.mark.smoke                    # Smoke test marker
@pytest.mark.critical                 # Critical path marker
@pytest.mark.slow                     # Slow-running test marker
@pytest.mark.security                 # Security-focused marker
@pytest.mark.api                      # API test marker
@pytest.mark.database                 # Database test marker
```

---

## 📜 Script Naming Conventions

### CI Scripts: `ci_{action}.py`
```
ci_runner.py                      # Main CI orchestrator
ci_test_runner.py                 # Test execution runner
ci_quality_checker.py             # Code quality validation
ci_security_scanner.py            # Security validation
ci_performance_tester.py          # Performance testing
ci_report_generator.py            # CI report generation
```

### CD Scripts: `cd_{action}.py`
```
cd_deploy_staging.py              # Staging deployment
cd_deploy_production.py           # Production deployment
cd_rollback_manager.py            # Rollback management
cd_health_validator.py            # Post-deployment validation
cd_notification_sender.py         # Deployment notifications
```

### Utility Scripts: `util_{purpose}.py`
```
util_environment_setup.py         # Environment configuration
util_dependency_manager.py        # Dependency management
util_database_migrator.py         # Database migrations
util_log_analyzer.py              # Log analysis
util_performance_profiler.py      # Performance profiling
```

### Development Scripts: `dev_{purpose}.py`
```
dev_server_manager.py             # Development server
dev_test_data_generator.py        # Test data creation
dev_docker_manager.py             # Docker management
dev_code_formatter.py             # Code formatting
dev_import_fixer.py               # Import fixing
```

### Maintenance Scripts: `maint_{purpose}.py`
```
maint_cleanup_logs.py             # Log cleanup
maint_database_vacuum.py          # Database maintenance
maint_cache_cleaner.py            # Cache management
maint_dependency_updater.py       # Dependency updates
```

---

## 🔧 Environment Variables

### CI Variables: `CI_{PURPOSE}_{DETAIL}`
```bash
CI_STAGE=smoke                    # Current CI stage
CI_TIMEOUT=300                    # Stage timeout in seconds
CI_MAX_FAILURES=5                 # Maximum allowed failures
CI_PARALLEL_JOBS=4                # Parallel execution limit
CI_RETRY_COUNT=3                  # Retry attempts
CI_REPORT_FORMAT=json             # Report output format
CI_COVERAGE_THRESHOLD=80          # Coverage requirement
```

### CD Variables: `CD_{PURPOSE}_{DETAIL}`
```bash
CD_ENVIRONMENT=staging            # Target environment
CD_DEPLOYMENT_TYPE=canary         # Deployment strategy
CD_HEALTH_CHECK_URL=/health       # Health endpoint
CD_ROLLBACK_ENABLED=true          # Rollback capability
CD_APPROVAL_REQUIRED=true         # Manual approval gate
CD_NOTIFICATION_WEBHOOK=url       # Notification endpoint
```

### Test Variables: `TEST_{PURPOSE}_{DETAIL}`
```bash
TEST_DATABASE_URL=sqlite:///test.db   # Test database
TEST_REDIS_URL=redis://localhost:6379 # Test cache
TEST_LOG_LEVEL=INFO                   # Test logging level
TEST_TIMEOUT=30                       # Test timeout
TEST_COVERAGE_MIN=75                  # Minimum coverage
TEST_PARALLEL=true                    # Parallel execution
```

### Security Variables: `SECRET_{SERVICE}_{TYPE}`
```bash
# GitHub Secrets (encrypted)
SECRET_OPENAI_API_KEY             # OpenAI API access
SECRET_DATABASE_URL               # Production database
SECRET_REDIS_URL                  # Production cache
SECRET_DOCKER_REGISTRY_TOKEN      # Container registry
SECRET_NOTIFICATION_WEBHOOK       # Alert notifications
SECRET_AWS_ACCESS_KEY_ID          # AWS access
SECRET_AWS_SECRET_ACCESS_KEY      # AWS secret
```

### Application Variables: `APP_{FEATURE}_{SETTING}`
```bash
APP_DEBUG_MODE=false              # Debug configuration
APP_LOG_LEVEL=INFO                # Application logging
APP_DATABASE_POOL_SIZE=20         # Connection pool
APP_CACHE_TTL=3600               # Cache timeout
APP_API_RATE_LIMIT=100           # Rate limiting
APP_HEALTH_CHECK_INTERVAL=30     # Health check frequency
```

---

## 📚 Documentation Files

### Guides: `{TOPIC}_GUIDE.md`
```
CI_CD_DEVELOPER_GUIDE.md          # Developer CI/CD guide
TESTING_STRATEGY_GUIDE.md         # Testing strategy
DEPLOYMENT_OPERATIONS_GUIDE.md    # Deployment operations
SECURITY_IMPLEMENTATION_GUIDE.md  # Security guide
PERFORMANCE_OPTIMIZATION_GUIDE.md # Performance guide
TROUBLESHOOTING_GUIDE.md          # Problem resolution
```

### References: `{TOPIC}_REFERENCE.md`
```
API_SPECIFICATION_REFERENCE.md    # API documentation
NAMING_CONVENTIONS_REFERENCE.md   # This document
ENVIRONMENT_VARIABLES_REFERENCE.md # Environment config
WORKFLOW_DEFINITIONS_REFERENCE.md  # GitHub Actions
DATABASE_SCHEMA_REFERENCE.md      # Database structure
```

### Summaries: `{TOPIC}_SUMMARY.md`
```
CI_CD_PIPELINE_SUMMARY.md         # Pipeline overview
TEST_SUITE_SUMMARY.md             # Test suite status
SECURITY_AUDIT_SUMMARY.md         # Security assessment
PERFORMANCE_ANALYSIS_SUMMARY.md   # Performance metrics
DEPLOYMENT_STATUS_SUMMARY.md      # Deployment state
```

### Implementation: `{TOPIC}_IMPLEMENTATION.md`
```
DOCKER_CONTAINERIZATION_IMPLEMENTATION.md  # Docker setup
DATABASE_MIGRATION_IMPLEMENTATION.md       # Migration strategy
MONITORING_OBSERVABILITY_IMPLEMENTATION.md # Monitoring setup
SECURITY_HARDENING_IMPLEMENTATION.md       # Security measures
```

---

## ⚙️ Configuration Files

### CI/CD Configuration
```
pytest.ini                        # Pytest configuration
pytest_ci.ini                     # CI-specific pytest config
pyproject.toml                     # Project configuration
ruff.toml                         # Linting configuration
.github/workflows/                 # GitHub Actions workflows
```

### Docker Configuration
```
Dockerfile                        # Main application container
Dockerfile.multimodal             # Multimodal variant
docker-compose.yml                # Development orchestration  
docker-compose.production.yml     # Production orchestration
.dockerignore                     # Docker ignore patterns
```

### Database Configuration
```
alembic.ini                       # Database migration config
init.sql                          # Database initialization
migrations/                       # Migration scripts directory
```

### Requirements Files
```
requirements.txt                  # Core dependencies
requirements-dev.txt              # Development dependencies
requirements-ci.txt               # CI/CD dependencies
requirements-production.txt       # Production dependencies
requirements-multimodal.txt       # Multimodal dependencies
```

---

## 🐳 Docker and Containerization

### Container Naming
```
second-brain-app                  # Main application container
second-brain-db                   # Database container
second-brain-cache                # Redis cache container
second-brain-nginx                # Web server container
```

### Image Tagging
```
ghcr.io/user/second-brain:latest          # Latest stable
ghcr.io/user/second-brain:v1.2.3          # Semantic version
ghcr.io/user/second-brain:staging-latest  # Staging environment
ghcr.io/user/second-brain:pr-123          # Pull request
ghcr.io/user/second-brain:commit-abc123   # Commit-specific
```

### Docker Compose Services
```yaml
services:
  app:                            # Main application
  db:                             # PostgreSQL database
  cache:                          # Redis cache
  nginx:                          # Reverse proxy
  prometheus:                     # Monitoring
  grafana:                        # Metrics dashboard
```

---

## 🗃️ Database and Migration Files

### Migration File Naming: `{version}_{description}.py`
```
001_initial_schema.py             # Initial database schema
002_add_pgvector.py               # Vector extension
003_user_preferences.py           # User preference tables
004_memory_importance.py          # Importance scoring
005_search_analytics.py           # Search tracking
006_synthesis_tables.py           # Synthesis features
```

### SQL Files: `{purpose}_{description}.sql`
```
init_database.sql                 # Database initialization
create_indexes.sql                # Index creation
add_constraints.sql               # Constraint addition
optimize_queries.sql              # Query optimization
cleanup_orphaned_data.sql         # Data cleanup
```

---

## ✅ Validation and Enforcement

### Automated Validation

#### Pre-commit Hooks
```bash
# File naming validation
scripts/validate_naming_conventions.py

# Documentation consistency
scripts/validate_documentation.py  

# Configuration validation
scripts/validate_configurations.py
```

#### CI Pipeline Validation
```yaml
# In .github/workflows/ci-core-validation.yml
- name: "📋 Validate Naming Conventions"
  run: python scripts/validate_naming_conventions.py

- name: "📚 Check Documentation Consistency"  
  run: python scripts/validate_documentation.py
```

### Validation Script Example

```python
#!/usr/bin/env python3
"""
Naming Convention Validator for Second Brain CI/CD System
Validates all project artifacts follow naming conventions.
"""

import re
from pathlib import Path
from typing import List, Tuple

class NamingValidator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
    
    def validate_workflow_files(self) -> List[str]:
        """Validate GitHub Actions workflow naming."""
        workflow_dir = self.project_root / ".github" / "workflows"
        pattern = re.compile(r'^(ci|cd|maintenance|security|docs|release)-[a-z-]+\.yml$')
        
        violations = []
        for workflow_file in workflow_dir.glob("*.yml"):
            if not pattern.match(workflow_file.name):
                violations.append(f"Workflow file {workflow_file.name} doesn't match pattern")
        
        return violations
    
    def validate_test_files(self) -> List[str]:
        """Validate test file naming."""
        tests_dir = self.project_root / "tests"
        pattern = re.compile(r'^test_[a-z_]+\.py$')
        
        violations = []
        for test_file in tests_dir.rglob("test_*.py"):
            if not pattern.match(test_file.name):
                violations.append(f"Test file {test_file.name} doesn't match pattern")
        
        return violations
    
    def validate_script_files(self) -> List[str]:
        """Validate script file naming."""
        scripts_dir = self.project_root / "scripts"
        patterns = [
            re.compile(r'^ci_[a-z_]+\.py$'),
            re.compile(r'^cd_[a-z_]+\.py$'),
            re.compile(r'^util_[a-z_]+\.py$'),
            re.compile(r'^dev_[a-z_]+\.py$'),
            re.compile(r'^maint_[a-z_]+\.py$'),
        ]
        
        violations = []
        for script_file in scripts_dir.glob("*.py"):
            if not any(pattern.match(script_file.name) for pattern in patterns):
                violations.append(f"Script file {script_file.name} doesn't match any valid pattern")
        
        return violations
```

### Integration with Development Workflow

#### Make Target for Validation
```makefile
# In Makefile
validate-naming:
	python scripts/validate_naming_conventions.py
	python scripts/validate_documentation.py
	python scripts/validate_configurations.py

pre-commit: validate-naming
	# Run all pre-commit validations
```

#### IDE Integration
```json
// In .vscode/settings.json
{
  "files.associations": {
    "ci-*.yml": "yaml",
    "cd-*.yml": "yaml", 
    "test_*.py": "python",
    "*_GUIDE.md": "markdown",
    "*_REFERENCE.md": "markdown"
  }
}
```

---

## 🎯 Quick Reference Summary

### Essential Patterns
```
Workflows:     {stage}-{purpose}-{scope}.yml
Tests:         test_{feature}_{aspect}.py  
Scripts:       {category}_{action}.py
Environment:   {SCOPE}_{PURPOSE}_{DETAIL}
Documentation: {TOPIC}_{TYPE}.md
```

### Validation Commands
```bash
# Validate all naming conventions
make validate-naming

# Run specific validators
python scripts/validate_naming_conventions.py
python scripts/validate_documentation.py
python scripts/validate_configurations.py

# Check before commit
make pre-commit
```

### Key Benefits
- **Predictability**: Easy to find and understand files
- **Automation**: Tools can rely on naming patterns
- **Consistency**: Uniform approach across all components
- **Scalability**: Conventions grow with the project
- **Maintainability**: Clear structure reduces cognitive load

---

**This document is automatically validated in CI/CD pipelines and must be kept current with any naming convention changes.**

*Last Updated: 2025-08-01*
*Version: 2.0.0*
*Maintained by: CI/CD Pipeline Automation*