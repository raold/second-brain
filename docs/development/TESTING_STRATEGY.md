# 🧪 Testing Strategy for Second Brain

## Overview

This document outlines the comprehensive testing strategy for Second Brain, integrating with the centralized version management system and multi-branch development workflow.

## 🏗️ Testing Environments

### 1. **Development** (`develop` branch)
- **Branch**: `develop`
- **Purpose**: Experimental features and active development
- **CI/CD**: ✅ GitHub Actions on every push
- **Commands**:
  ```bash
  python scripts/version_manager.py test unit integration
  ```

### 2. **Local Development**
- **Branch**: `feature/*`, `develop`
- **Purpose**: Individual feature development and initial validation
- **Commands**:
  ```bash
  python scripts/version_manager.py test unit
  python scripts/version_manager.py test integration
  ```

### 3. **Integration Testing** (`testing` branch)
- **Branch**: `develop` → `testing`
- **Purpose**: Feature integration and cross-compatibility validation
- **CI/CD**: ✅ GitHub Actions on merges from develop
- **Commands**:
  ```bash
  python scripts/version_manager.py test all
  ```

### 4. **PR Testing** (testing → main)
- **Branch**: `testing` → `main` (Pull Request)
- **Purpose**: Code review and comprehensive validation
- **Automated**: GitHub Actions CI/CD pipeline
- **Manual**: Code review + testing checklist

### 5. **Staging/Pre-Production**
- **Branch**: `main`
- **Purpose**: Final validation before production release
- **Commands**:
  ```bash
  python scripts/version_manager.py validate X.Y.Z
  python scripts/test_production_readiness.py
  ```

### 6. **Production**
- **Branch**: `v*.*.*` tags
- **Purpose**: Live system monitoring and health checks
- **Monitoring**: Continuous health endpoint monitoring

## 🧪 Test Types & Structure

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions and classes
- **Speed**: Fast (< 1 second per test)
- **Coverage**: High code coverage target (>90%)
- **Command**: `python scripts/version_manager.py test unit`

### Integration Tests (`tests/integration/`)
- **Purpose**: Test API endpoints and database interactions
- **Speed**: Medium (1-10 seconds per test)
- **Coverage**: Critical user workflows
- **Command**: `python scripts/version_manager.py test integration`

### Performance Tests (`tests/performance/`)
- **Purpose**: Benchmark response times and throughput
- **Speed**: Slow (10+ seconds per test)
- **Coverage**: Critical performance paths
- **Command**: `python scripts/version_manager.py test performance`

### Migration Tests (`tests/migration/`)
- **Purpose**: Validate database schema changes
- **Speed**: Medium (depends on migration complexity)
- **Coverage**: All database migrations
- **Command**: `python scripts/version_manager.py test migration`

## 🔄 Testing Workflows

### Develop Branch Workflow (New!)
```bash
# 1. Start feature development
git checkout develop
git pull origin develop
# Make changes...

# 2. Run fast tests during development
python scripts/version_manager.py test unit

# 3. Before committing, validate integration
python scripts/version_manager.py test unit integration

# 4. Commit to develop (CI will run automatically)
git commit -m "feat: experimental feature"
git push origin develop

# 5. When ready for integration, merge to testing
git checkout testing
git pull origin testing
git merge develop
python scripts/version_manager.py test all  # Full validation
git push origin testing
```

### Testing Branch Workflow (Integration)
```bash
# 1. Work on integrated features
git checkout testing
# Merge from develop or work directly...

# 2. Run comprehensive tests
python scripts/version_manager.py test all

# 3. Before PR to main
python scripts/version_manager.py validate X.Y.Z

# 4. Create PR with full testing checklist
```

### Traditional Development Workflow (Direct Testing)
```bash
# 1. Work on feature
git checkout testing
# Make changes...

# 2. Run relevant tests during development
python scripts/version_manager.py test unit

# 3. Before committing, run all tests
python scripts/version_manager.py test all

# 4. Commit and push
git commit -m "feat: new feature"
git push origin testing
```

### PR Testing Workflow
When `pr_testing: true` in version configuration:

1. **Automated GitHub Actions** runs full test suite
2. **Manual Review Checklist**:
   - ✅ Unit tests pass
   - ✅ Integration tests pass  
   - ✅ Performance tests pass
   - ✅ Migration tests pass
   - ✅ Code review completed
   - ✅ Documentation updated
   - ✅ Security considerations reviewed
   - ✅ Breaking changes documented

### Release Validation Workflow
```bash
# 1. Validate all pre-release requirements
python scripts/version_manager.py validate 2.4.2

# 2. Prepare release
python scripts/version_manager.py prepare 2.4.2

# 3. Follow generated git workflow commands

# 4. Test production readiness
python scripts/test_production_readiness.py http://localhost:8000

# 5. Deploy to production
docker-compose up -d --build

# 6. Verify production deployment
curl http://localhost:8000/health
python scripts/test_production_readiness.py http://your-domain.com
```

## 📊 Testing Standards

### Coverage Requirements
- **Unit Tests**: >90% code coverage
- **Integration Tests**: All API endpoints covered
- **Performance Tests**: Critical paths benchmarked
- **Migration Tests**: All migrations validated

### Performance Thresholds
- **Health Endpoint**: < 100ms response time
- **API Endpoints**: < 500ms average response time
- **Database Queries**: < 200ms for simple queries
- **Memory Operations**: < 1s for create/read operations

### Quality Gates
All releases must pass:
1. ✅ All unit tests
2. ✅ All integration tests
3. ✅ Performance benchmarks within thresholds
4. ✅ All migration tests
5. ✅ Security scans clean
6. ✅ Production readiness validation

## 🛠️ Testing Tools & Configuration

### pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
addopts = 
    --cov=app 
    --cov-report=term-missing 
    --cov-report=html
    --cov-report=xml
    --strict-markers
    --verbose

markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Slow-running tests
```

### GitHub Actions Integration
- Automatic test execution on PR creation
- Coverage reporting
- Performance regression detection
- Security scanning integration

## 🚀 Production Readiness Testing

### Health Checks
- **Endpoint**: `/health`
- **Frequency**: Every 30 seconds
- **Timeout**: 10 seconds
- **Expected**: 200 OK response

### System Validation
```bash
# Run comprehensive production readiness tests
python scripts/test_production_readiness.py

# Tests include:
# - Health endpoint responsiveness
# - API endpoint functionality  
# - Database connectivity
# - Performance baselines
# - Memory operations
```

### Monitoring & Alerting
- **Application**: Health endpoint monitoring
- **Database**: Connection pool monitoring
- **Performance**: Response time tracking
- **Errors**: Error rate and type monitoring

## 📝 Test Data Management

### Test Fixtures
- Located in `tests/fixtures/`
- Realistic but anonymized data
- Consistent across test runs

### Database Testing
- Isolated test database
- Automatic cleanup after tests
- Migration testing on separate schemas

## 🔧 Configuration

### Environment Variables
```bash
# Testing configuration
TESTING=true
TEST_DATABASE_URL=postgresql://test_user:test_pass@localhost/test_db
LOG_LEVEL=DEBUG
```

### Test-Specific Settings
- Reduced timeouts for faster tests
- In-memory databases where appropriate
- Mock external services

## 📚 Best Practices

### Writing Tests
1. **Arrange-Act-Assert** pattern
2. **Descriptive test names** that explain what's being tested
3. **Independent tests** that don't rely on order
4. **Clean fixtures** for consistent state

### Test Maintenance
1. **Regular test review** and cleanup
2. **Performance test baseline updates**
3. **Test data refresh** to match production patterns
4. **Documentation updates** with code changes

---

This comprehensive testing strategy ensures high-quality releases while maintaining development velocity through the centralized version management system.
