# CI/CD Developer Quick Reference - Second Brain v3.0.0

## Quick Commands Cheat Sheet

### 🚀 Essential Daily Commands

```bash
# Before committing (< 1 minute)
make test-smoke

# Before pushing (< 5 minutes)  
make test-fast

# Before creating PR (< 15 minutes)
make test-comprehensive

# Complete CI simulation (< 25 minutes)
make ci-full
```

### 🔧 Debugging Failed Tests

```bash
# Find out what failed
make test-smoke 2>&1 | grep -E "(FAIL|ERROR)"

# Run specific test with full output
python -m pytest tests/path/to/test.py::test_name -v -s

# Debug with breakpoint
python -m pytest tests/path/to/test.py::test_name -v -s --pdb

# Check environment issues
python scripts/validate_environment.py
```

### 🏃‍♂️ Development Workflow

#### Pre-Commit Checklist
- [ ] `make test-smoke` passes
- [ ] Code formatted: `make format`
- [ ] No obvious issues: `make lint`

#### Pre-Push Checklist  
- [ ] `make test-fast` passes
- [ ] Integration tests work
- [ ] No import errors

#### Pre-PR Checklist
- [ ] `make test-comprehensive` passes  
- [ ] All new tests included
- [ ] Documentation updated if needed

---

## Understanding Test Failures

### 🔥 Smoke Test Failures (CRITICAL - Pipeline Stops)

**What it means**: Basic functionality is broken
**Impact**: Blocks entire pipeline immediately
**Action**: Fix immediately before any other work

```bash
# Common smoke test failures:

# Import Error
❌ ImportError: cannot import name 'SomeClass'
→ Fix: Check imports in affected files
→ Command: python -c "import app.module_name"

# Database Connection  
❌ Connection refused on localhost:5432
→ Fix: Start database service
→ Command: docker-compose up -d postgres

# Health Endpoint
❌ Health check failed with 500 error
→ Fix: Check application startup
→ Command: python app/app.py (check console output)
```

### ⚡ Fast Feedback Failures (WARNING - Continue with Caution)

**What it means**: Core functionality has issues
**Impact**: Pipeline continues but deployment may be blocked
**Action**: Fix soon, but not blocking for development

```bash
# Common fast feedback failures:

# Unit Test Failure
❌ test_memory_creation FAILED
→ Fix: Check business logic in the failing component
→ Command: python -m pytest tests/unit/test_memory.py -v

# Integration Test Failure  
❌ test_api_endpoint FAILED
→ Fix: Check service interactions and API contracts
→ Command: python -m pytest tests/integration/test_api.py -v

# Mock Configuration Issue
❌ AttributeError: Mock object has no attribute 'method'
→ Fix: Check mock setup in test fixtures
→ Command: grep -r "mock.*method" tests/
```

### 🔍 Comprehensive Test Failures (BLOCKING - No Deployment)

**What it means**: Full feature validation failed
**Impact**: Blocks deployment to production
**Action**: Must fix before merging to main

```bash
# Common comprehensive failures:

# Database Migration Issue
❌ Migration failed: table already exists  
→ Fix: Check migration scripts and database state
→ Command: docker-compose exec postgres psql -U secondbrain -c "\dt"

# Security Test Failure
❌ Security vulnerability detected
→ Fix: Address security issue immediately
→ Command: python -m bandit -r app/

# End-to-End Workflow Failure
❌ Complete user workflow test failed
→ Fix: Check entire feature integration
→ Command: python -m pytest tests/comprehensive/ -v -k "workflow"
```

---

## CI/CD Pipeline Status Interpretation

### Pipeline Status Icons

| Icon | Status | Meaning | Action Required |
|------|--------|---------|-----------------|
| 🎉 | EXCELLENT | All tests pass, excellent metrics | ✅ Deploy freely |
| ✅ | GOOD | Tests pass, minor warnings | ✅ Deploy with normal monitoring |
| ⚠️ | NEEDS_IMPROVEMENT | Some issues detected | 🔄 Review and improve |
| ❌ | FAILING | Critical issues found | 🚫 Fix before deployment |

### Stage Status Quick Reference

```bash
# Smoke Tests (30-60s)
🔥 PASS → Continue to next stage
🔥 FAIL → Stop pipeline, fix critical issues

# Fast Feedback (2-5min)  
⚡ PASS → Continue to comprehensive tests
⚡ WARN → Continue with warnings logged
⚡ FAIL → Block deployment if >10% failure rate

# Comprehensive (10-15min)
🔍 PASS → Ready for performance tests  
🔍 FAIL → Block deployment, fix critical issues

# Performance (5-20min)
📊 PASS → Ready for deployment
📊 WARN → Deploy with enhanced monitoring
📊 FAIL → Performance regression detected (non-blocking)
```

---

## Local Testing Best Practices

### 🎯 Test Selection Strategy

```bash
# Development cycle - run frequently
make test-smoke              # 30-60 seconds

# Feature development - run after major changes  
make test-fast-unit          # 2-3 minutes
make test-fast-integration   # 3-4 minutes

# Pre-commit - run before committing
make pre-commit              # 5-6 minutes

# Pre-push - run before pushing  
make pre-push                # 10-15 minutes

# Pre-release - run before major releases
make pre-release             # 20-30 minutes
```

### 🔧 Efficient Debugging Workflow

```bash
# Step 1: Identify the failing test category
make test-smoke        # If this fails, stop and fix
make test-fast         # If this fails, identify specific group

# Step 2: Run specific failing group
make test-fast-unit           # Only unit tests
make test-fast-integration    # Only integration tests  
make test-fast-api           # Only API tests

# Step 3: Drill down to specific test
python -m pytest tests/unit/test_specific.py -v

# Step 4: Debug with detailed output  
python -m pytest tests/unit/test_specific.py::test_function -v -s --tb=long

# Step 5: Fix and verify
python -m pytest tests/unit/test_specific.py::test_function -v
make test-fast  # Verify broader test suite still passes
```

### 🏃‍♂️ Performance Tips

```bash
# Run tests in parallel (faster)
python -m pytest tests/unit/ -n auto

# Run only changed tests (during development)
python -m pytest tests/unit/ --lf  # Last failed
python -m pytest tests/unit/ --ff  # Failed first

# Skip slow tests during development
python -m pytest tests/ -m "not slow"

# Run specific test markers
python -m pytest tests/ -m "unit and not integration"
```

---

## Common Error Patterns & Quick Fixes

### Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'app.something'
# Quick Fix:
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -c "import app.something"  # Test the fix

# Permanent Fix: Add to .env or pytest.ini
PYTHONPATH=.
```

### Database Connection Issues  

```bash
# Error: Connection refused / Database not ready
# Quick Fix:
docker-compose up -d postgres redis
sleep 10  # Wait for services to start
make test-smoke

# Check if services are ready:
docker-compose ps
docker-compose logs postgres
```

### Test Isolation Problems

```python
# Error: Tests pass individually but fail together
# Quick Fix: Add proper cleanup
@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await database.truncate_all_tables()
    cache.clear()
```

### Mock Configuration Issues

```python
# Error: Mock not working as expected
# Quick Fix: Use proper mock setup
@patch('app.services.external_service.ExternalAPI')
def test_with_mock(mock_api):
    mock_api.return_value.method.return_value = "expected_result"
    # Test implementation
```

### Resource/Memory Issues

```bash
# Error: Tests running out of memory or timing out
# Quick Fix: Reduce parallel workers
python -m pytest tests/ -n 2  # Instead of -n auto

# Check resource usage:
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

---

## Environment Variables Quick Reference

### Required for Testing

```bash
# Core testing environment
export ENVIRONMENT=test
export TESTING=true
export PYTHONPATH=.

# Database (for integration tests)
export DATABASE_URL=postgresql://secondbrain:changeme@localhost:5432/secondbrain_test

# Redis (for caching tests)  
export REDIS_URL=redis://localhost:6379

# API Keys (use test keys)
export OPENAI_API_KEY=test-key-mock
export API_TOKENS=test-token-32-chars-long-for-auth-1234567890abcdef

# Performance tuning
export LOG_LEVEL=WARNING  # Reduce log noise
export DEBUG=false        # Disable debug mode
```

### CI-Specific Variables

```bash
# GitHub Actions sets these automatically
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_REF_NAME=main

# Performance adjustments for CI
export MAX_WORKERS=2
export TEST_TIMEOUT=300
```

---

## Troubleshooting Checklist

### Before Running Tests

- [ ] Virtual environment activated: `.venv/Scripts/activate`
- [ ] Dependencies installed: `pip install -r config/requirements-ci.txt`
- [ ] Environment variables set correctly
- [ ] Database and Redis services running (if needed)
- [ ] No conflicting processes on test ports

### When Tests Fail

- [ ] Check the specific error message
- [ ] Verify environment setup: `python scripts/validate_environment.py`
- [ ] Run failing test in isolation: `pytest tests/path/to/test.py::test_name -v`
- [ ] Check for resource issues: memory, disk space, network
- [ ] Verify mock configurations and test data setup
- [ ] Check for database/service connectivity

### Before Asking for Help

- [ ] Read the full error message and stack trace
- [ ] Check if the same test passes in isolation
- [ ] Verify the issue reproduces consistently
- [ ] Check recent changes that might have caused the issue
- [ ] Look for similar issues in project documentation or issues

---

## GitHub Actions Integration

### PR Comments

When you create a PR, the CI system automatically:
- Runs all applicable test stages
- Posts a summary comment with results
- Updates the comment as new commits are pushed
- Provides links to detailed test reports

### Status Checks

Your PR will show status checks for:
- 🔥 **Smoke Tests** - Must pass to continue
- ⚡ **Fast Feedback** - Must have >90% pass rate  
- 🔍 **Comprehensive** - Must pass for deployment readiness
- 📊 **Performance** - Informational, doesn't block

### Artifact Downloads

After CI runs, you can download:
- Test result JSON files
- Coverage reports (HTML)
- Performance benchmark data
- Consolidated pipeline report

```bash
# Download artifacts using GitHub CLI
gh run download [run-id]

# View test results locally
python scripts/analyze_test_results.py downloaded-artifacts/
```

---

## Quick Links

- 📋 [Comprehensive CI/CD Guide](./CI_CD_COMPREHENSIVE_GUIDE.md)
- 🧪 [Testing Strategy](./CI_CD_TESTING_STRATEGY.md)  
- 🐳 [Docker Development Guide](./development/DEVELOPMENT_GUIDE_v3.0.0.md)
- 📖 [API Documentation](./API_DOCUMENTATION_INDEX.md)
- 🏗️ [Architecture Overview](./ARCHITECTURE_V3.md)

**Need Help?** Check the troubleshooting section above or create an issue with:
- Command you ran
- Full error message  
- Environment details (`python --version`, `docker --version`)
- Steps to reproduce