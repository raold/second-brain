# CI/CD Guide - Second Brain v2.8.2

## Overview

This guide explains the CI/CD pipeline setup for Second Brain and how to troubleshoot common issues.

## GitHub Actions Workflow

The main CI/CD pipeline is defined in `.github/workflows/ci-v2.8.yml` and runs on:
- Every push to main, develop, release/*, and feature/* branches
- Every pull request to main or develop
- Manual workflow dispatch

### Pipeline Stages

1. **Quality Checks** (10m)
   - Ruff linting and formatting
   - Type checking with mypy
   - Security scanning with bandit
   - Secret detection

2. **Test Suite** (15m, parallel)
   - Unit Tests (split into Core and Extended)
   - Integration Tests
   - API Tests
   - Migration Tests
   - Bulk Operations Tests
   - AI/ML Tests
   - Performance Tests

3. **Build & Package** (5m)
   - Docker image build
   - Dependency validation
   - Version consistency check

4. **Deploy** (5m, conditional)
   - Staging deployment (on develop branch)
   - Production deployment (on main branch, manual approval)

## Common CI/CD Issues and Fixes

### 1. Ruff Version Mismatch

**Issue**: `ruff==0.12.4` expected by CI but `ruff==0.1.6` in requirements.txt

**Fix**:
```bash
# Update requirements.txt
sed -i 's/ruff==0.1.6/ruff==0.12.4/' requirements.txt
```

### 2. Missing Module Imports

**Issue**: `ModuleNotFoundError: No module named 'app.models.synthesis'`

**Fix**: Ensure all package directories have `__init__.py` files:
```bash
touch app/models/__init__.py
touch app/services/__init__.py
```

### 3. Test Discovery Issues

**Issue**: Tests not found or skipped

**Fix**: Check pytest.ini configuration and ensure test markers are defined:
```ini
markers =
    synthesis: marks tests as synthesis feature tests
    api: marks tests as API endpoint tests
    endpoint: marks tests as API endpoint tests
```

### 4. Database Connection Failures

**Issue**: Tests fail due to database connection

**Fix**: Tests should use mock database:
```python
# In conftest.py
os.environ["USE_MOCK_DATABASE"] = "true"
```

### 5. Import Path Issues

**Issue**: Python can't find modules

**Fix**: CI sets PYTHONPATH correctly:
```yaml
env:
  PYTHONPATH: ${{ github.workspace }}
```

## Pre-Push Validation

Before pushing to main, run the validation script:

```bash
python scripts/validate_ci.py
```

This checks:
- File existence
- Python syntax
- Import validity
- Requirements consistency
- Test file validity

## Local Testing

To replicate CI locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# 2. Run linting
ruff check .
ruff format --check .

# 3. Run tests with mock database
export USE_MOCK_DATABASE=true
export PYTHONPATH=.
pytest tests/unit/synthesis -v

# 4. Run specific test groups
pytest -m synthesis -v
pytest -m "not integration" -v
```

## Debugging Failed Builds

1. **Check the GitHub Actions logs**:
   - Go to Actions tab in GitHub
   - Click on the failed workflow run
   - Expand the failed job to see detailed logs

2. **Run debug workflow**:
   ```bash
   # Trigger debug workflow manually
   gh workflow run debug-ci.yml
   ```

3. **Common log patterns to look for**:
   - `ModuleNotFoundError` - Missing dependencies or import issues
   - `SyntaxError` - Python syntax errors
   - `AssertionError` - Test assertions failing
   - `ConnectionError` - Database or service connection issues

## Test Organization

Tests are organized by type and run in parallel:

```
tests/
├── unit/
│   ├── synthesis/          # Synthesis feature unit tests
│   ├── test_*.py          # Other unit tests
├── integration/
│   ├── synthesis/          # Synthesis integration tests
│   └── test_*.py          # Other integration tests
├── performance/           # Performance tests
└── conftest.py           # Shared fixtures
```

## Environment Variables

The CI uses these environment variables:

```yaml
PYTHON_VERSION: '3.11'
NODE_VERSION: '20'
POSTGRES_VERSION: '16'
REDIS_VERSION: '7'
DOCKER_BUILDKIT: '1'
RUFF_VERSION: '0.12.4'
```

## Pre-commit Hooks

Install pre-commit hooks to catch issues early:

```bash
pip install pre-commit
pre-commit install
```

This runs:
- Ruff linting and formatting
- File cleanup (trailing whitespace, EOF)
- YAML/JSON validation
- Import checks

## Deployment

### Staging Deployment

Automatic on push to develop branch:
- Builds Docker image
- Pushes to staging registry
- Deploys to staging environment

### Production Deployment

Manual approval required on push to main:
- Builds Docker image with production optimizations
- Creates GitHub release
- Deploys to production after approval

## Monitoring CI/CD

1. **Build Status Badge**: Add to README.md:
   ```markdown
   ![CI/CD](https://github.com/yourusername/second-brain/workflows/Second%20Brain%20v2.8.x%20CI/CD%20Pipeline/badge.svg)
   ```

2. **Slack Notifications**: Configure in GitHub settings

3. **Build Time Tracking**: Monitor in Actions -> Insights

## Troubleshooting Checklist

- [ ] All Python files have proper syntax
- [ ] All required `__init__.py` files exist
- [ ] Requirements.txt versions match CI expectations
- [ ] Tests use mock database (USE_MOCK_DATABASE=true)
- [ ] No hardcoded secrets or API keys
- [ ] All imports can be resolved
- [ ] Test markers are defined in pytest.ini
- [ ] Pre-commit hooks pass locally

## Getting Help

If CI/CD continues to fail:

1. Run the debug workflow: `.github/workflows/debug-ci.yml`
2. Check the validation script: `scripts/validate_ci.py`
3. Review recent changes that might have broken CI
4. Check GitHub Actions status page for outages

Remember: A passing CI is required for merging to main!