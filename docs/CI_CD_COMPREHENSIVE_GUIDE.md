# CI/CD System Comprehensive Guide - Second Brain v3.0.0

## Table of Contents

1. [CI/CD Architecture Overview](#cicd-architecture-overview)
2. [Developer Guide](#developer-guide)
3. [Workflow Documentation](#workflow-documentation)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Performance Optimization](#performance-optimization)
6. [Monitoring and Metrics](#monitoring-and-metrics)

---

## CI/CD Architecture Overview

### System Philosophy

Our CI/CD system implements a **Tiered Testing Strategy** that balances speed with reliability:

- **Speed First**: Fast feedback for developers (< 5 minutes for core tests)
- **Reliability Second**: Comprehensive validation for production readiness
- **Resource Efficient**: Parallel execution and smart test selection
- **Developer Friendly**: Clear feedback and actionable error messages

### Pipeline Architecture

```mermaid
graph TD
    A[Code Push] --> B[Smoke Tests]
    B --> C{All Pass?}
    C -->|No| D[❌ Block Pipeline]
    C -->|Yes| E[Fast Feedback Tests]
    E --> F[Unit Tests]
    E --> G[Basic Integration]
    E --> H[Core API Tests]
    F --> I{Success Rate > 90%?}
    G --> I
    H --> I
    I -->|No| J[⚠️ Warning Continue]
    I -->|Yes| K[Comprehensive Validation]
    K --> L[Full Integration]
    K --> M[Security Tests]
    K --> N[Database Tests]
    L --> O{All Critical Pass?}
    M --> O
    N --> O
    O -->|No| P[🚫 Block Deployment]
    O -->|Yes| Q[Performance Benchmarks]
    Q --> R[Load Tests]
    Q --> S[Memory Profiling]
    R --> T[📊 Generate Reports]
    S --> T
    T --> U[🚀 Ready for Deployment]
```

### Stage Breakdown

#### Stage 1: Smoke Tests (30-60 seconds)
**Purpose**: Critical path validation - fastest possible feedback

**Triggers**:
- Every commit to any branch
- Pull request creation/update
- Manual trigger

**Tests Included**:
- Environment validation
- Critical import verification
- Basic application startup
- Health endpoint connectivity
- Database connection test

**Failure Behavior**: Any failure blocks the entire pipeline

#### Stage 2: Fast Feedback (2-5 minutes)
**Purpose**: Core functionality validation with rapid feedback

**Triggers**:
- After smoke tests pass
- Hourly scheduled runs
- Developer manual execution

**Test Groups** (run in parallel):
- **Unit Tests**: Isolated component testing
- **Basic Integration**: Service interaction tests
- **Core API**: Essential endpoint validation

**Failure Behavior**: >10% failure rate blocks pipeline

#### Stage 3: Comprehensive Validation (10-15 minutes)
**Purpose**: Full feature validation before deployment consideration

**Triggers**:
- After fast feedback passes
- Before merge to main branch
- Nightly comprehensive builds
- Pre-deployment validation

**Tests Included**:
- Complete integration test suite
- End-to-end workflow validation
- Database migration testing
- Security vulnerability scanning
- Cross-service communication tests

**Failure Behavior**: >5% failure rate blocks deployment

#### Stage 4: Performance Benchmarks (5-20 minutes)
**Purpose**: Performance regression detection and load validation

**Triggers**:
- After comprehensive validation passes
- Before production deployment
- Weekly performance baseline updates

**Tests Included**:
- Response time benchmarks
- Throughput measurement
- Memory leak detection
- Database performance validation
- Concurrent user simulation

**Failure Behavior**: Informational only - doesn't block deployment but generates alerts

### Decision Flow Chart

```mermaid
flowchart TD
    Start([Code Push/PR]) --> Smoke[🔥 Smoke Tests]
    Smoke --> SmokePass{All Pass?}
    SmokePass -->|No| BlockPipeline[❌ Block Pipeline<br/>Notify Developer]
    SmokePass -->|Yes| FastFeedback[⚡ Fast Feedback Tests]
    
    FastFeedback --> FastResults{Results Analysis}
    FastResults -->|< 90% Success| FastWarn[⚠️ Continue with Warning]
    FastResults -->|≥ 90% Success| FastPass[✅ Proceed]
    FastWarn --> Comprehensive[🔍 Comprehensive Tests]
    FastPass --> Comprehensive
    
    Comprehensive --> CompResults{Critical Tests}
    CompResults -->|Any Critical Fail| BlockDeploy[🚫 Block Deployment]
    CompResults -->|All Critical Pass| Performance[📊 Performance Tests]
    
    Performance --> PerfResults{Performance Check}
    PerfResults -->|Major Regression| PerfWarn[⚠️ Performance Alert]
    PerfResults -->|Within Limits| PerfPass[✅ Performance OK]
    
    PerfWarn --> Deploy[🚀 Deploy with Monitoring]
    PerfPass --> Deploy
    BlockPipeline --> End([End])
    BlockDeploy --> End
    Deploy --> End
```

---

## Developer Guide

### How to Run Tests Locally

#### Quick Start Commands

```bash
# 🔥 Smoke tests - Run before every commit (< 1 minute)
make test-smoke

# ⚡ Fast feedback - Run before pushing (< 5 minutes)
make test-fast

# 🔍 Comprehensive - Run before creating PR (< 15 minutes)
make test-comprehensive

# 📊 Performance - Run before releases (< 20 minutes)
make test-performance

# 🤖 Full CI simulation - Run before major changes
make ci-full
```

#### Detailed Test Commands

```bash
# Run specific test groups
make test-fast-unit              # Unit tests only
make test-fast-integration       # Basic integration tests
make test-fast-api              # Core API tests

# Legacy pytest commands (for specific debugging)
python -m pytest tests/unit/ -v -m "unit and not slow"
python -m pytest tests/integration/ -v -m "integration and not slow"
python -m pytest tests/validation/ -v

# Advanced testing with custom options
python scripts/ci_runner.py --stage fast --group unit --save-report unit_report.json
python scripts/ci_runner.py --stage comprehensive --exit-on-failure
```

### How to Debug CI Failures

#### Step 1: Identify the Failure Stage

Check the CI logs to identify which stage failed:

```bash
# Check the stage that failed
grep -E "(FAIL|ERROR|BLOCK)" ci_logs.txt

# Look for specific error patterns
grep -E "(ImportError|ModuleNotFoundError|ConnectionError)" ci_logs.txt
```

#### Step 2: Reproduce Locally

```bash
# Reproduce the exact CI environment
export ENVIRONMENT=test
export TESTING=true
export LOG_LEVEL=WARNING

# Run the specific failed stage
make test-smoke        # If smoke tests failed
make test-fast-unit    # If unit tests failed
make test-comprehensive # If comprehensive tests failed
```

#### Step 3: Debug Specific Test Failures

```bash
# Run specific failing test with verbose output
python -m pytest tests/path/to/failing_test.py::test_name -v -s

# Run test with debugging
python -m pytest tests/path/to/failing_test.py::test_name -v -s --pdb

# Run test with coverage to see what's not being tested
python -m pytest tests/path/to/failing_test.py --cov=app --cov-report=html
```

#### Step 4: Check Dependencies and Environment

```bash
# Validate environment setup
python scripts/validate_environment.py

# Check dependency versions
pip list | grep -E "(fastapi|pydantic|pytest|sqlalchemy)"

# Verify database connectivity
python -c "from app.database import get_database; print('DB OK')"
```

### Best Practices for Writing CI-Friendly Tests

#### 1. Test Isolation

```python
# ✅ GOOD: Isolated test with proper setup/teardown
@pytest.fixture(autouse=True)
async def clean_database():
    await database.truncate_all_tables()
    yield
    # Cleanup happens automatically

async def test_memory_creation():
    memory_service = get_memory_service()
    memory = await memory_service.create_memory(test_data)
    assert memory.id is not None

# ❌ BAD: Test depends on external state
async def test_memory_count():
    # This test will fail if other tests create memories
    memories = await memory_service.list_memories()
    assert len(memories) == 5  # Brittle assumption
```

#### 2. Fast Test Design

```python
# ✅ GOOD: Fast test with mocked external dependencies
@patch('app.services.openai_client.OpenAIClient')
async def test_embedding_generation(mock_openai):
    mock_openai.return_value.generate_embedding.return_value = [0.1] * 1536
    
    result = await embedding_service.generate_embedding("test text")
    assert len(result) == 1536

# ❌ BAD: Slow test with real API calls
async def test_embedding_generation_real():
    # This makes actual API calls - slow and unreliable
    result = await embedding_service.generate_embedding("test text")
    assert len(result) == 1536
```

#### 3. Reliable Test Markers

```python
# Use pytest markers for test categorization
@pytest.mark.unit
@pytest.mark.fast
def test_memory_validation():
    pass

@pytest.mark.integration
@pytest.mark.requires_database
async def test_memory_persistence():
    pass

@pytest.mark.performance
@pytest.mark.slow
def test_bulk_memory_processing():
    pass
```

#### 4. Environment-Agnostic Tests

```python
# ✅ GOOD: Use environment variables with defaults
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///test.db")

# ✅ GOOD: Use pathlib for cross-platform paths
from pathlib import Path
test_file = Path(__file__).parent / "fixtures" / "test_data.json"

# ❌ BAD: Hardcoded paths
test_file = "/Users/someone/project/tests/fixtures/test_data.json"
```

### Development Workflow Integration

#### Pre-Commit Workflow

```bash
# Before committing any code
make pre-commit

# This runs:
# - Smoke tests (critical path validation)
# - Fast unit tests (core functionality)
# - Code formatting (black, ruff)
# - Basic linting
```

#### Pre-Push Workflow

```bash
# Before pushing to remote
make pre-push

# This runs:
# - All fast feedback tests
# - Comprehensive validation
# - Security checks
# - Integration tests
```

#### Pre-Release Workflow

```bash
# Before creating a release
make pre-release

# This runs:
# - Complete CI pipeline simulation
# - Performance benchmarks
# - Load testing
# - Documentation validation
```

---

## Workflow Documentation

### GitHub Actions Workflow

Our CI/CD system uses a single comprehensive workflow file: `.github/workflows/ci-tiered.yml`

#### Workflow Structure

```yaml
name: CI/CD Pipeline - Tiered Testing Strategy

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Nightly comprehensive tests

env:
  PYTHONUNBUFFERED: 1
  PYTHONPATH: .
  ENVIRONMENT: test
  TESTING: true
```

#### Job Dependencies

```mermaid
graph TD
    A[smoke-tests] --> B[fast-feedback]
    B --> C[comprehensive-validation]
    C --> D[performance-benchmarks]
    A --> E[consolidate-results]
    B --> E
    C --> E
    D --> E
    E --> F[notify]
```

### Job Definitions

#### 1. Smoke Tests Job

```yaml
smoke-tests:
  name: 🔥 Smoke Tests
  runs-on: ubuntu-latest
  timeout-minutes: 3
  outputs:
    should-continue: ${{ steps.smoke-result.outputs.should-continue }}
```

**Purpose**: Validate critical path in under 60 seconds
**Outputs**: Boolean flag indicating whether pipeline should continue
**Failure Behavior**: Stops entire pipeline immediately

#### 2. Fast Feedback Job

```yaml
fast-feedback:
  name: ⚡ Fast Feedback
  needs: smoke-tests
  if: needs.smoke-tests.outputs.should-continue == 'true'
  runs-on: ubuntu-latest
  timeout-minutes: 8
  strategy:
    fail-fast: false
    matrix:
      test-group: [unit, integration-basic, api-core]
```

**Purpose**: Parallel execution of core functionality tests
**Strategy**: Matrix strategy runs 3 parallel jobs
**Failure Behavior**: Individual job failures don't stop other jobs

#### 3. Comprehensive Validation Job

```yaml
comprehensive-validation:
  name: 🔍 Comprehensive Validation
  needs: [smoke-tests, fast-feedback]
  if: |
    needs.smoke-tests.outputs.should-continue == 'true' &&
    (github.ref == 'refs/heads/main' || 
     github.event_name == 'pull_request' ||
     github.event_name == 'schedule')
  runs-on: ubuntu-latest
  timeout-minutes: 20
  services:
    postgres:
      image: pgvector/pgvector:pg16
    redis:
      image: redis:7-alpine
```

**Purpose**: Full validation with real services
**Services**: PostgreSQL with pgvector, Redis
**Trigger Conditions**: Only on main branch, PRs, or scheduled runs

#### 4. Performance Benchmarks Job

```yaml
performance-benchmarks:
  name: 📊 Performance Benchmarks
  needs: [smoke-tests, fast-feedback, comprehensive-validation]
  if: |
    needs.smoke-tests.outputs.should-continue == 'true' &&
    (github.ref == 'refs/heads/main' || github.event_name == 'schedule')
  runs-on: ubuntu-latest
  timeout-minutes: 25
```

**Purpose**: Performance regression detection
**Trigger Conditions**: Only on main branch or scheduled runs
**Failure Behavior**: Continues on error (non-blocking)

### Environment Variables and Secrets

#### Required Environment Variables

```yaml
env:
  PYTHONUNBUFFERED: 1          # Immediate output for debugging
  PYTHONPATH: .                # Ensure imports work
  ENVIRONMENT: test            # Test configuration mode
  TESTING: true               # Enable test-specific behavior
  LOG_LEVEL: WARNING          # Reduce log noise in CI
  DATABASE_URL: postgresql://secondbrain:changeme@localhost:5432/secondbrain_test
  REDIS_URL: redis://localhost:6379
```

#### Required Secrets

```yaml
secrets:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY || 'test-key-mock' }}
```

**Setup Instructions**:
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add `OPENAI_API_KEY` with your OpenAI API key
3. The workflow uses a fallback mock key if not provided

### Deployment Process

#### Deployment Readiness Criteria

A build is considered deployment-ready when:

1. **All Critical Tests Pass**: Smoke and comprehensive tests must pass
2. **Success Rate ≥ 80%**: Overall test success rate meets threshold
3. **No Security Issues**: Security validation passes
4. **Performance Within Limits**: No major performance regressions

#### Deployment Decision Logic

```python
def determine_deployment_readiness(test_results):
    blocking_failures = any(r.should_block for r in test_results)
    overall_success_rate = calculate_success_rate(test_results)
    
    deployment_ready = (
        not blocking_failures and 
        overall_success_rate >= 0.8
    )
    
    return deployment_ready
```

#### Post-Deployment Monitoring

After deployment, the system:

1. **Generates Performance Baseline**: New performance metrics become baseline
2. **Updates Success Rate Trends**: Historical success rate tracking
3. **Creates Deployment Report**: Comprehensive deployment summary
4. **Notifies Stakeholders**: Slack/email notifications with results

### Artifact Management

#### Generated Artifacts

Each stage generates specific artifacts:

**Smoke Tests**:
- `smoke_report.json` - Test execution results
- `smoke_coverage.xml` - Basic coverage report

**Fast Feedback**:
- `fast_unit_report.json` - Unit test results
- `fast_integration_report.json` - Integration test results
- `fast_api_report.json` - API test results

**Comprehensive Validation**:
- `comprehensive_report.json` - Complete test results
- `htmlcov/` - HTML coverage reports
- `coverage.xml` - Coverage report for Codecov

**Performance Benchmarks**:
- `performance_report.json` - Benchmark results
- `load_test_results.json` - Load testing data
- `memory_profile.json` - Memory usage analysis

#### Artifact Retention

- **Pull Requests**: 30 days
- **Main Branch**: 90 days
- **Tagged Releases**: Permanent
- **Scheduled Runs**: 14 days

---

## Troubleshooting Guide

### Common Failures and Solutions

#### 1. Smoke Test Failures

**Symptom**: Pipeline fails immediately in smoke test stage

**Common Causes**:
- Import errors
- Environment setup issues
- Database connectivity problems

**Debugging Steps**:

```bash
# 1. Check import issues locally
python -c "import app.app; print('Imports OK')"

# 2. Validate environment
python scripts/validate_environment.py

# 3. Test database connection
python -c "from app.database import get_database; print('DB OK')"

# 4. Run smoke tests with verbose output
python scripts/ci_runner.py --stage smoke --save-report debug_smoke.json
```

**Common Solutions**:

```bash
# Fix missing dependencies
pip install -r config/requirements-ci.txt

# Reset virtual environment
rm -rf .venv
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r config/requirements.txt

# Check Docker services
docker-compose ps
docker-compose logs postgres
```

#### 2. Fast Feedback Test Failures

**Symptom**: Unit or integration tests failing in fast feedback stage

**Common Causes**:
- Test isolation issues
- Mock configuration problems
- Resource constraints

**Debugging Steps**:

```bash
# 1. Run specific failing test group
make test-fast-unit

# 2. Run with detailed output
python -m pytest tests/unit/ -v -s --tb=long

# 3. Check for resource issues
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# 4. Validate test isolation
python -m pytest tests/unit/test_failing.py -v --setup-show
```

**Common Solutions**:

```python
# Fix test isolation
@pytest.fixture(autouse=True)
async def reset_state():
    # Clear any global state
    await clear_test_data()
    yield
    # Cleanup

# Fix mock configuration
@patch('app.services.external_service.ExternalService')
def test_with_proper_mock(mock_service):
    mock_service.return_value.method.return_value = expected_value
    # Test implementation
```

#### 3. Comprehensive Test Database Issues

**Symptom**: Database-related test failures in comprehensive stage

**Common Causes**:
- PostgreSQL service not ready
- Migration issues
- Connection pool exhaustion

**Debugging Steps**:

```bash
# 1. Check PostgreSQL service status
docker-compose exec postgres pg_isready -U secondbrain

# 2. Check database logs
docker-compose logs postgres

# 3. Test connection manually
docker-compose exec postgres psql -U secondbrain -c "SELECT 1;"

# 4. Check migration status
docker-compose run --rm app alembic current
```

**Common Solutions**:

```yaml
# Increase service startup time
services:
  postgres:
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 10  # Increased retries
```

```python
# Add connection retry logic
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_database_connection():
    return await database.connect()
```

#### 4. Performance Test Timeouts

**Symptom**: Performance tests timing out or showing poor results

**Common Causes**:
- Resource constraints in CI
- Network latency
- Database not optimized

**Debugging Steps**:

```bash
# 1. Run performance tests locally
make test-performance

# 2. Check resource usage during tests
python scripts/run_performance_tests.py --type benchmark --verbose

# 3. Profile the application
python -m cProfile -o profile.stats main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

**Common Solutions**:

```python
# Adjust performance thresholds for CI
PERFORMANCE_THRESHOLDS = {
    "response_time_ms": 500 if os.getenv("CI") else 200,
    "throughput_rps": 20 if os.getenv("CI") else 50,
}

# Use connection pooling
DATABASE_CONFIG = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
```

### Error Pattern Recognition

#### Import-Related Errors

```bash
# Pattern: ModuleNotFoundError
grep -E "ModuleNotFoundError|ImportError" ci_logs.txt

# Common fixes:
# 1. Add missing dependencies to requirements.txt
# 2. Fix PYTHONPATH in environment
# 3. Check for circular imports
```

#### Database Connection Errors

```bash
# Pattern: Connection errors
grep -E "connection.*refused|timeout|psycopg2" ci_logs.txt

# Common fixes:
# 1. Increase database startup wait time
# 2. Add connection retry logic
# 3. Check service dependencies
```

#### Memory/Resource Errors

```bash
# Pattern: Memory or resource exhaustion
grep -E "MemoryError|OSError.*resource|timeout" ci_logs.txt

# Common fixes:
# 1. Reduce parallel test workers
# 2. Add memory cleanup in fixtures
# 3. Increase CI resource limits
```

### Debugging CI in GitHub Actions

#### 1. Enable Debug Logging

Add to workflow file:

```yaml
env:
  ACTIONS_STEP_DEBUG: true
  DEBUG: true
```

#### 2. SSH Access for Debugging

Use action for SSH access:

```yaml
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: failure()
```

#### 3. Artifact Download for Analysis

```bash
# Download artifacts locally
gh run download [run-id]

# Analyze test reports
python scripts/analyze_test_results.py downloaded-artifacts/
```

### Local CI Simulation

#### Complete CI Simulation

```bash
# Run exact CI pipeline locally
make ci-full

# Run with CI environment variables
export CI=true
export GITHUB_ACTIONS=true
export ENVIRONMENT=test
make ci-full
```

#### Debug Specific Stages

```bash
# Debug smoke tests
python scripts/ci_runner.py --stage smoke --save-report debug_smoke.json
cat debug_smoke.json | jq '.stages[0].tests[]'

# Debug with timeout
timeout 300 python scripts/ci_runner.py --stage comprehensive
```

---

## Performance Optimization

### Test Execution Speed Optimization

#### 1. Parallel Test Execution

**Current Configuration**:
- Unit tests: 4 parallel workers
- Integration tests: 2 parallel workers
- Performance tests: 1 worker (resource intensive)

**Optimization Strategies**:

```python
# pytest-xdist configuration
pytest.ini:
[tool:pytest]
addopts = -n auto --dist worksteal
```

```bash
# Dynamic worker allocation based on resources
python -m pytest -n $(nproc) tests/unit/
python -m pytest -n 2 tests/integration/  # Limited for database tests
```

#### 2. Smart Test Selection

**Test Categorization**:

```python
# Fast tests (< 1 second each)
@pytest.mark.fast
@pytest.mark.unit
def test_memory_validation():
    pass

# Slow tests (> 10 seconds each)
@pytest.mark.slow
@pytest.mark.integration
def test_end_to_end_workflow():
    pass
```

**Conditional Execution**:

```bash
# Run only fast tests in development
pytest -m "fast and not slow"

# Run comprehensive tests only on main branch
pytest -m "slow" --maxfail=5
```

#### 3. Resource Management

**Database Connection Pooling**:

```python
# Optimized database configuration for tests
TEST_DATABASE_CONFIG = {
    "pool_size": 2,  # Reduced for test environment
    "max_overflow": 5,
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "echo": False,  # Disable SQL logging in tests
}
```

**Memory Management**:

```python
# Cleanup fixtures to prevent memory leaks
@pytest.fixture(autouse=True)
def cleanup_memory():
    yield
    gc.collect()  # Force garbage collection
    
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### CI Infrastructure Optimization

#### 1. Docker Layer Caching

```dockerfile
# Optimized Dockerfile for CI
FROM python:3.11-slim as base

# Install system dependencies in separate layer
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY config/requirements-ci.txt .
RUN pip install --no-cache-dir -r requirements-ci.txt

# Copy application code last
COPY app/ ./app/
```

#### 2. Artifact Optimization

```yaml
# Compress artifacts to reduce storage
- name: Upload test results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      *.json
      htmlcov/
    retention-days: 30
    compression-level: 6
```

#### 3. Matrix Strategy Optimization

```yaml
# Optimized matrix for faster feedback
strategy:
  fail-fast: false  # Continue other jobs even if one fails
  matrix:
    test-group: [unit, integration-basic, api-core]
    include:
      - test-group: unit
        timeout: 5
        workers: 4
      - test-group: integration-basic
        timeout: 8
        workers: 2
      - test-group: api-core
        timeout: 3
        workers: 2
```

### Performance Monitoring

#### 1. Test Execution Metrics

**Key Metrics Tracked**:
- Individual test execution time
- Stage completion time
- Resource usage (CPU, memory)
- Success/failure rates
- Flaky test identification

**Metric Collection**:

```python
# Built into ci_runner.py
def track_test_performance(test_name, execution_time, resource_usage):
    metrics = {
        "test_name": test_name,
        "execution_time": execution_time,
        "memory_mb": resource_usage.get("memory_mb", 0),
        "cpu_percent": resource_usage.get("cpu_percent", 0),
        "timestamp": datetime.now().isoformat()
    }
    
    # Store in performance database or file
    with open("test_performance.jsonl", "a") as f:
        f.write(json.dumps(metrics) + "\n")
```

#### 2. Performance Regression Detection

**Threshold Configuration**:

```python
PERFORMANCE_THRESHOLDS = {
    "smoke_tests": {"max_time": 60, "warning_time": 45},
    "fast_feedback": {"max_time": 300, "warning_time": 240},
    "comprehensive": {"max_time": 900, "warning_time": 720},
    "performance": {"max_time": 1200, "warning_time": 900},
}

def check_performance_regression(current_time, stage_name):
    threshold = PERFORMANCE_THRESHOLDS.get(stage_name, {})
    max_time = threshold.get("max_time", float("inf"))
    warning_time = threshold.get("warning_time", max_time * 0.8)
    
    if current_time > max_time:
        return "REGRESSION"
    elif current_time > warning_time:
        return "WARNING"
    else:
        return "OK"
```

#### 3. Resource Usage Optimization

**Memory Usage Tracking**:

```python
import psutil
import tracemalloc

def monitor_memory_usage():
    """Monitor memory usage during test execution"""
    tracemalloc.start()
    initial_memory = psutil.Process().memory_info().rss
    
    try:
        yield
    finally:
        final_memory = psutil.Process().memory_info().rss
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_stats = {
            "initial_mb": initial_memory / 1024 / 1024,
            "final_mb": final_memory / 1024 / 1024,
            "delta_mb": (final_memory - initial_memory) / 1024 / 1024,
            "peak_traced_mb": peak / 1024 / 1024,
        }
        
        log_memory_usage(memory_stats)
```

---

## Monitoring and Metrics

### CI/CD Pipeline Metrics

#### 1. Core Performance Metrics

**Pipeline Execution Metrics**:
- Total pipeline execution time
- Stage-by-stage execution time
- Success/failure rates by stage
- Flaky test identification and trends
- Resource utilization during tests

**Quality Metrics**:
- Test coverage trends
- Code quality scores
- Security vulnerability counts
- Performance regression detection
- Deployment readiness percentage

#### 2. Metric Collection Implementation

```python
# Built into scripts/ci_runner.py
class MetricsCollector:
    def __init__(self):
        self.metrics = []
        self.start_time = datetime.now()
    
    def record_stage_metrics(self, stage_result):
        """Record metrics for a completed stage"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage_result.stage,
            "duration_seconds": stage_result.execution_time,
            "total_tests": stage_result.total_tests,
            "passed_tests": stage_result.passed_tests,
            "failed_tests": stage_result.failed_tests,
            "success_rate": stage_result.success_rate,
            "should_block": stage_result.should_block,
            "resource_usage": stage_result.resource_usage,
        }
        
        self.metrics.append(metrics)
        self._export_metrics(metrics)
    
    def _export_metrics(self, metrics):
        """Export metrics to monitoring system"""
        # Could integrate with Prometheus, DataDog, etc.
        with open("ci_metrics.jsonl", "a") as f:
            f.write(json.dumps(metrics) + "\n")
```

#### 3. Dashboard and Alerting

**Key Dashboard Panels**:

1. **Pipeline Health**:
   - Success rate over time
   - Average execution time by stage
   - Failure rate trends

2. **Test Quality**:
   - Flaky test trends
   - Test coverage over time
   - New test additions/removals

3. **Performance Trends**:
   - Response time percentiles
   - Resource usage trends
   - Performance regression alerts

**Alerting Rules**:

```yaml
# Example alerting configuration
alerts:
  - name: "High CI Failure Rate"
    condition: "success_rate < 0.8 for 3 consecutive runs"
    severity: "critical"
    notification: ["slack", "email"]
    
  - name: "CI Performance Degradation"
    condition: "avg_execution_time > baseline * 1.5"
    severity: "warning"
    notification: ["slack"]
    
  - name: "Flaky Test Increase"
    condition: "flaky_test_count > 5 in last day"
    severity: "warning"
    notification: ["slack"]
```

### Test Quality Monitoring

#### 1. Flaky Test Detection

```python
# Built into test result analysis
def analyze_flaky_tests(test_history):
    """Analyze test history to identify flaky tests"""
    flaky_tests = []
    
    for test_name, results in test_history.items():
        # Test is flaky if it has both passes and failures recently
        recent_results = results[-10:]  # Last 10 runs
        has_passes = any(r["status"] == "PASS" for r in recent_results)
        has_failures = any(r["status"] == "FAIL" for r in recent_results)
        
        if has_passes and has_failures:
            failure_rate = sum(1 for r in recent_results if r["status"] == "FAIL") / len(recent_results)
            flaky_tests.append({
                "test_name": test_name,
                "failure_rate": failure_rate,
                "last_10_results": [r["status"] for r in recent_results]
            })
    
    return sorted(flaky_tests, key=lambda x: x["failure_rate"], reverse=True)
```

#### 2. Coverage Monitoring

```python
# Coverage trend analysis
def analyze_coverage_trends(coverage_reports):
    """Analyze test coverage trends over time"""
    trends = {
        "overall_coverage": [],
        "module_coverage": {},
        "new_code_coverage": [],
        "coverage_changes": []
    }
    
    for report in coverage_reports:
        trends["overall_coverage"].append({
            "timestamp": report["timestamp"],
            "coverage_percent": report["summary"]["coverage_percent"]
        })
        
        # Track coverage changes
        if len(trends["overall_coverage"]) > 1:
            previous = trends["overall_coverage"][-2]["coverage_percent"]
            current = trends["overall_coverage"][-1]["coverage_percent"]
            change = current - previous
            
            trends["coverage_changes"].append({
                "timestamp": report["timestamp"],
                "change_percent": change,
                "direction": "increase" if change > 0 else "decrease"
            })
    
    return trends
```

### Deployment Readiness Tracking

#### 1. Readiness Score Calculation

```python
def calculate_deployment_readiness_score(pipeline_results):
    """Calculate deployment readiness score (0-100)"""
    
    # Base score from test success rate
    base_score = pipeline_results["overall_success_rate"] * 100
    
    # Penalties
    critical_failure_penalty = len(pipeline_results["critical_failures"]) * 20
    flaky_test_penalty = min(pipeline_results["flaky_test_count"] * 2, 10)
    coverage_penalty = max(0, (80 - pipeline_results["coverage_percent"]) * 0.5)
    
    # Bonuses
    performance_bonus = 5 if pipeline_results["performance_within_limits"] else 0
    security_bonus = 5 if pipeline_results["security_tests_passed"] else 0
    
    # Calculate final score
    score = (
        base_score 
        - critical_failure_penalty 
        - flaky_test_penalty 
        - coverage_penalty 
        + performance_bonus 
        + security_bonus
    )
    
    return max(0, min(100, score))
```

#### 2. Deployment Decision Matrix

```python
def make_deployment_decision(readiness_score, pipeline_results):
    """Make deployment decision based on multiple factors"""
    
    decision_matrix = {
        "deploy": False,
        "deploy_with_monitoring": False,
        "block_deployment": False,
        "manual_review_required": False,
        "reasons": []
    }
    
    # Critical blocking conditions
    if pipeline_results["critical_failures"]:
        decision_matrix["block_deployment"] = True
        decision_matrix["reasons"].append("Critical test failures detected")
    
    if pipeline_results["security_vulnerabilities"]:
        decision_matrix["block_deployment"] = True
        decision_matrix["reasons"].append("Security vulnerabilities found")
    
    # Deployment readiness based on score
    if readiness_score >= 95:
        decision_matrix["deploy"] = True
        decision_matrix["reasons"].append("Excellent test results")
    elif readiness_score >= 85:
        decision_matrix["deploy_with_monitoring"] = True
        decision_matrix["reasons"].append("Good test results, deploy with enhanced monitoring")
    elif readiness_score >= 75:
        decision_matrix["manual_review_required"] = True
        decision_matrix["reasons"].append("Moderate test results, manual review recommended")
    else:
        decision_matrix["block_deployment"] = True
        decision_matrix["reasons"].append(f"Low readiness score: {readiness_score}/100")
    
    return decision_matrix
```

### Integration with External Monitoring

#### 1. Prometheus Metrics Export

```python
# Example Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
ci_pipeline_runs = Counter('ci_pipeline_runs_total', 'Total CI pipeline runs', ['status', 'branch'])
ci_test_duration = Histogram('ci_test_duration_seconds', 'Test execution duration', ['stage'])
ci_success_rate = Gauge('ci_success_rate', 'Current CI success rate')
ci_flaky_tests = Gauge('ci_flaky_tests_count', 'Number of flaky tests')

# Export metrics
def export_ci_metrics(pipeline_result):
    ci_pipeline_runs.labels(
        status='success' if pipeline_result['deployment_ready'] else 'failure',
        branch=os.getenv('GITHUB_REF_NAME', 'unknown')
    ).inc()
    
    for stage in pipeline_result['stages']:
        ci_test_duration.labels(stage=stage['stage']).observe(stage['execution_time'])
    
    ci_success_rate.set(pipeline_result['summary']['overall_success_rate'])
    ci_flaky_tests.set(pipeline_result['summary']['flaky_tests'])
```

#### 2. Slack/Teams Integration

```python
def send_ci_notification(pipeline_result, webhook_url):
    """Send CI results to Slack/Teams"""
    
    status_emoji = "✅" if pipeline_result['deployment_ready'] else "❌"
    color = "good" if pipeline_result['deployment_ready'] else "danger"
    
    message = {
        "attachments": [{
            "color": color,
            "title": f"{status_emoji} CI/CD Pipeline Results",
            "fields": [
                {
                    "title": "Branch",
                    "value": os.getenv('GITHUB_REF_NAME', 'unknown'),
                    "short": True
                },
                {
                    "title": "Success Rate",
                    "value": f"{pipeline_result['summary']['overall_success_rate']:.1%}",
                    "short": True
                },
                {
                    "title": "Total Tests",
                    "value": str(pipeline_result['summary']['total_tests']),
                    "short": True
                },
                {
                    "title": "Deployment Ready",
                    "value": "Yes" if pipeline_result['deployment_ready'] else "No",
                    "short": True
                }
            ]
        }]
    }
    
    # Send to webhook
    import requests
    requests.post(webhook_url, json=message)
```

This comprehensive CI/CD documentation provides developers with all the information needed to understand, use, and troubleshoot the testing and deployment system. The tiered approach ensures fast feedback while maintaining thorough validation for production deployments.