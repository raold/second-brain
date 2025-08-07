# CI/CD Workflow Documentation - Second Brain v3.0.0

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [GitHub Actions Implementation](#github-actions-implementation)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Process](#deployment-process)
5. [Monitoring and Notifications](#monitoring-and-notifications)
6. [Security and Secrets Management](#security-and-secrets-management)

---

## Workflow Overview

### Complete Pipeline Flow

```mermaid
graph TD
    subgraph "Triggers"
        A1[Push to main/develop]
        A2[Pull Request]
        A3[Scheduled Run]
        A4[Manual Trigger]
    end
    
    subgraph "Stage 1: Smoke Tests (30-60s)"
        B1[Environment Validation]
        B2[Critical Imports]
        B3[Health Endpoint]
        B4[Database Connectivity]
    end
    
    subgraph "Stage 2: Fast Feedback (2-5min)"
        C1[Unit Tests]
        C2[Basic Integration]
        C3[Core API Tests]
    end
    
    subgraph "Stage 3: Comprehensive (10-15min)"
        D1[Full Integration Tests]
        D2[Security Validation]
        D3[Database Migrations]
        D4[End-to-End Workflows]
    end
    
    subgraph "Stage 4: Performance (5-20min)"
        E1[Response Time Benchmarks]
        E2[Load Testing]
        E3[Memory Profiling]
        E4[Regression Detection]
    end
    
    subgraph "Results Processing"
        F1[Consolidate Results]
        F2[Generate Reports]
        F3[Update Metrics]
        F4[Deployment Decision]
    end
    
    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1
    
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> G1{All Pass?}
    
    G1 -->|No| H1[❌ Block Pipeline]
    G1 -->|Yes| C1
    
    C1 --> C2
    C2 --> C3
    C3 --> G2{Success Rate > 90%?}
    
    G2 -->|No| H2[⚠️ Continue with Warning]
    G2 -->|Yes| D1
    H2 --> D1
    
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> G3{Critical Tests Pass?}
    
    G3 -->|No| H3[🚫 Block Deployment]
    G3 -->|Yes| E1
    
    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> F1
    
    F1 --> F2
    F2 --> F3
    F3 --> F4
    F4 --> G4{Deploy Ready?}
    
    G4 -->|Yes| H4[🚀 Ready for Deployment]
    G4 -->|No| H5[🔄 Needs Improvement]
    
    H1 --> I1[End]
    H3 --> I1
    H4 --> I1
    H5 --> I1
```

### Stage Dependencies and Conditions

```mermaid
graph LR
    subgraph "Job Dependencies"
        A[smoke-tests] --> B[fast-feedback]
        B --> C[comprehensive-validation]
        C --> D[performance-benchmarks]
        A --> E[consolidate-results]
        B --> E
        C --> E
        D --> E
        E --> F[notify]
    end
    
    subgraph "Conditional Execution"
        G[Push to main] --> H[All Stages]
        I[Pull Request] --> J[Smoke + Fast + Comprehensive]
        K[Scheduled] --> L[All Stages + Extended Performance]
        M[Feature Branch] --> N[Smoke + Fast Only]
    end
```

---

## GitHub Actions Implementation

### Workflow File Structure

The complete workflow is defined in `.github/workflows/ci-tiered.yml`:

```yaml
name: CI/CD Pipeline - Tiered Testing Strategy

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM UTC
  workflow_dispatch:     # Manual trigger

env:
  PYTHONUNBUFFERED: 1
  PYTHONPATH: .
  ENVIRONMENT: test
  TESTING: true

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  checks: write
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
  
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
        
    - name: Install minimal dependencies
      run: |
        pip install --upgrade pip
        pip install pytest pytest-asyncio httpx psutil
        
    - name: Run smoke tests
      id: smoke-tests
      run: |
        python scripts/ci_runner.py --stage smoke --save-report smoke_report.json
      continue-on-error: false
      
    - name: Determine continuation
      id: smoke-result
      run: |
        if [ ${{ steps.smoke-tests.outcome }} == 'success' ]; then
          echo "should-continue=true" >> $GITHUB_OUTPUT
        else
          echo "should-continue=false" >> $GITHUB_OUTPUT
        fi
        
    - name: Upload smoke test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: smoke-test-results
        path: smoke_report.json
```

**Key Features**:
- **3-minute timeout**: Forces fast execution
- **Output variable**: Controls whether pipeline continues
- **Artifact upload**: Results available even on failure
- **No retries**: Smoke tests must be reliable

#### 2. Fast Feedback Job (Matrix Strategy)

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
      
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
        
    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r config/requirements-ci.txt
        
    - name: Set up test environment
      run: |
        mkdir -p temp logs
        
    - name: Run fast feedback tests
      run: |
        python scripts/ci_runner.py \
          --stage fast \
          --group ${{ matrix.test-group }} \
          --save-report fast_${{ matrix.test-group }}_report.json
          
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: fast-feedback-results-${{ matrix.test-group }}
        path: fast_${{ matrix.test-group }}_report.json
```

**Key Features**:
- **Matrix execution**: 3 parallel jobs for faster feedback
- **fail-fast: false**: All groups run even if one fails
- **Conditional execution**: Only runs if smoke tests pass
- **Group-specific reports**: Detailed results for each test group

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
      env:
        POSTGRES_USER: secondbrain
        POSTGRES_PASSWORD: changeme
        POSTGRES_DB: secondbrain_test
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
      ports:
        - 5432:5432
        
    redis:
      image: redis:7-alpine
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
      ports:
        - 6379:6379
```

**Key Features**:
- **Real services**: PostgreSQL with pgvector and Redis
- **Health checks**: Ensures services are ready before tests
- **Conditional execution**: Only on main, PRs, or scheduled runs
- **Extended timeout**: More time for comprehensive testing

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
  
  steps:
    - name: Run performance benchmarks
      env:
        DATABASE_URL: postgresql://secondbrain:changeme@localhost:5432/secondbrain_perf
        REDIS_URL: redis://localhost:6379
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY || 'test-key-mock' }}
      run: |
        python scripts/ci_runner.py \
          --stage performance \
          --save-report performance_report.json
      continue-on-error: true  # Don't block deployment on performance issues
```

**Key Features**:
- **Limited execution**: Only on main branch or scheduled runs
- **Non-blocking**: Performance issues don't prevent deployment
- **Dedicated database**: Separate DB for performance testing
- **Extended timeout**: Allows for thorough performance testing

### Results Consolidation and Notification

#### Consolidate Results Job

```yaml
consolidate-results:
  name: 📋 Consolidate Results
  needs: [smoke-tests, fast-feedback, comprehensive-validation, performance-benchmarks]
  if: always()
  runs-on: ubuntu-latest
  
  steps:
    - name: Download all test results
      uses: actions/download-artifact@v3
      with:
        path: test-results/
        
    - name: Consolidate test results
      run: |
        python scripts/consolidate_test_results.py \
          --results-dir test-results/ \
          --output final_test_report.json
          
    - name: Generate test summary
      run: |
        python scripts/generate_test_summary.py \
          --report final_test_report.json \
          --output test_summary.md
          
    - name: Comment test summary on PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          if (fs.existsSync('test_summary.md')) {
            const summary = fs.readFileSync('test_summary.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: summary
            });
          }
```

**Key Features**:
- **Runs always**: Even if previous jobs fail
- **Artifact aggregation**: Downloads all test results
- **Automated reporting**: Generates summary and comments on PRs
- **Final status determination**: Calculates deployment readiness

---

## Environment Configuration

### Environment Variables by Stage

#### Global Environment Variables

```yaml
env:
  PYTHONUNBUFFERED: 1          # Immediate output buffering
  PYTHONPATH: .                # Python import path
  ENVIRONMENT: test            # Application environment
  TESTING: true               # Enable test mode
  LOG_LEVEL: WARNING          # Reduce log verbosity
  PYTHONIOENCODING: utf-8     # Handle unicode properly
```

#### Stage-Specific Environment Variables

**Smoke Tests**:
```yaml
env:
  SECURITY_LEVEL: development
  API_TOKENS: test-token-32-chars-long-for-auth-1234567890abcdef
  DEBUG: false
```

**Comprehensive Tests**:
```yaml
env:
  DATABASE_URL: postgresql://secondbrain:changeme@localhost:5432/secondbrain_test
  REDIS_URL: redis://localhost:6379
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY || 'test-key-mock' }}
  ENABLE_REAL_SERVICES: true
```

**Performance Tests**:
```yaml
env:
  DATABASE_URL: postgresql://secondbrain:changeme@localhost:5432/secondbrain_perf
  REDIS_URL: redis://localhost:6379
  LOG_LEVEL: ERROR            # Minimal logging for performance
  PERFORMANCE_MODE: true
```

### Service Configuration

#### PostgreSQL Service

```yaml
postgres:
  image: pgvector/pgvector:pg16
  env:
    POSTGRES_USER: secondbrain
    POSTGRES_PASSWORD: changeme
    POSTGRES_DB: secondbrain_test
    POSTGRES_INITDB_ARGS: "--auth-host=md5"
  options: >-
    --health-cmd pg_isready
    --health-interval 10s
    --health-timeout 5s
    --health-retries 5
    --health-start-period 30s
  ports:
    - 5432:5432
```

**Features**:
- **pgvector extension**: For vector similarity operations
- **Health checks**: Ensures database is ready before tests
- **Custom initialization**: Proper authentication setup
- **Start period**: Allows extra time for first startup

#### Redis Service

```yaml
redis:
  image: redis:7-alpine
  env:
    REDIS_PASSWORD: ""
  options: >-
    --health-cmd "redis-cli ping"
    --health-interval 10s
    --health-timeout 5s
    --health-retries 5
  ports:
    - 6379:6379
```

**Features**:
- **Alpine image**: Smaller, faster startup
- **No password**: Simplified for testing
- **Health checks**: Ping command verification
- **Standard port**: Default Redis configuration

---

## Deployment Process

### Deployment Decision Flow

```mermaid
flowchart TD
    A[Pipeline Complete] --> B{Smoke Tests Pass?}
    B -->|No| C[❌ Block All Deployment]
    B -->|Yes| D{Fast Feedback Success Rate}
    
    D -->|< 90%| E[⚠️ Deploy with Caution]
    D -->|≥ 90%| F{Comprehensive Tests}
    
    F -->|Critical Failures| G[🚫 Block Deployment]
    F -->|All Pass| H{Performance Results}
    
    H -->|Major Regression| I[⚠️ Deploy with Monitoring]
    H -->|Within Limits| J[✅ Deploy Freely]
    
    E --> K[Enhanced Monitoring Required]
    I --> K
    J --> L[Standard Monitoring]
    K --> M[Deploy to Staging First]
    L --> N[Can Deploy Direct to Production]
    
    C --> O[Fix Issues Before Any Deployment]
    G --> O
    M --> P[Manual Approval for Production]
    N --> Q[Automatic Production Deployment]
```

### Deployment Readiness Criteria

#### Critical Requirements (Must Pass)

1. **Smoke Tests**: 100% pass rate required
   - Environment validation
   - Critical imports
   - Health endpoint
   - Database connectivity

2. **Security Tests**: No vulnerabilities allowed
   - Code security scanning
   - Dependency vulnerability checks
   - Authentication/authorization tests

3. **Data Integrity**: Database operations must be safe
   - Migration tests
   - Data consistency validation
   - Backup/restore verification

#### Quality Requirements (Strong Preference)

1. **Test Success Rate**: ≥80% overall, ≥90% preferred
2. **Coverage**: ≥70% code coverage maintained
3. **Performance**: No major regressions (>20% degradation)
4. **Flaky Tests**: <5% of total test suite

### Deployment Environments

#### Staging Deployment (Automatic)

**Triggers**:
- All tests pass with good quality metrics
- Manual trigger for testing purposes
- Scheduled deployments for validation

**Configuration**:
```yaml
staging:
  environment: staging
  database: staging_postgres
  redis: staging_redis
  monitoring: enhanced
  rollback: automatic_on_error
```

**Validation Steps**:
1. Deploy to staging environment
2. Run smoke tests against staging
3. Validate core user workflows
4. Check performance metrics
5. Approve for production or rollback

#### Production Deployment (Conditional)

**Triggers**:
- Staging validation passes
- Manual approval (for major changes)
- Automated (for minor changes with excellent test results)

**Configuration**:
```yaml
production:
  environment: production
  database: production_postgres_cluster
  redis: production_redis_cluster
  monitoring: comprehensive
  rollback: manual_approval_required
```

**Safety Measures**:
1. Blue-green deployment strategy
2. Database migration validation
3. Service health monitoring
4. Automated rollback triggers
5. Manual rollback capability

### Deployment Automation

#### GitHub Actions Deployment Workflow

```yaml
deploy:
  name: 🚀 Deploy Application
  needs: [consolidate-results]
  if: |
    needs.consolidate-results.outputs.deployment-ready == 'true' &&
    github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  environment: 
    name: production
    url: https://secondbrain.example.com
  
  steps:
    - name: Deploy to staging
      run: |
        # Deploy to staging first
        ./scripts/deploy.sh staging
        
    - name: Validate staging deployment
      run: |
        # Run staging validation tests
        ./scripts/validate_deployment.sh staging
        
    - name: Deploy to production
      if: success()
      run: |
        # Deploy to production
        ./scripts/deploy.sh production
        
    - name: Validate production deployment
      run: |
        # Run production validation tests
        ./scripts/validate_deployment.sh production
        
    - name: Notify deployment success
      if: success()
      run: |
        # Send success notifications
        ./scripts/notify_deployment.sh success
        
    - name: Rollback on failure
      if: failure()
      run: |
        # Automatic rollback
        ./scripts/rollback.sh production
        ./scripts/notify_deployment.sh failure
```

---

## Monitoring and Notifications

### Real-time Monitoring

#### Pipeline Execution Monitoring

**Metrics Tracked**:
- Stage execution times
- Test success/failure rates
- Resource utilization
- Error patterns
- Performance trends

**Dashboards**:
- **Developer Dashboard**: Individual test results, failure analysis
- **Team Dashboard**: Overall pipeline health, trends
- **Management Dashboard**: Deployment readiness, quality metrics

#### Test Quality Monitoring

```python
# Example monitoring implementation
class CIPipelineMonitor:
    def __init__(self):
        self.metrics_collector = PrometheusMetrics()
        self.alert_manager = AlertManager()
    
    def record_stage_completion(self, stage_result):
        # Record metrics
        self.metrics_collector.record_stage_duration(
            stage=stage_result.stage,
            duration_seconds=stage_result.execution_time
        )
        
        self.metrics_collector.record_test_results(
            stage=stage_result.stage,
            passed=stage_result.passed_tests,
            failed=stage_result.failed_tests,
            success_rate=stage_result.success_rate
        )
        
        # Check for alerts
        if stage_result.should_block:
            self.alert_manager.send_alert(
                severity="critical",
                message=f"Pipeline blocked at {stage_result.stage} stage",
                details=stage_result.error_summary
            )
        elif stage_result.success_rate < 0.9:
            self.alert_manager.send_alert(
                severity="warning",
                message=f"Low success rate in {stage_result.stage}: {stage_result.success_rate:.1%}",
                details=stage_result.failure_summary
            )
```

### Notification System

#### Slack Integration

```yaml
- name: Notify Slack on Success
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: success
    channel: '#dev-ci-cd'
    text: |
      ✅ CI/CD Pipeline completed successfully!
      Branch: ${{ github.ref_name }}
      Commit: ${{ github.sha }}
      Tests: ${{ env.TOTAL_TESTS }} passed
      Deployment: Ready
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

- name: Notify Slack on Failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    channel: '#dev-ci-cd'
    text: |
      ❌ CI/CD Pipeline failed!
      Branch: ${{ github.ref_name }}
      Stage: ${{ env.FAILED_STAGE }}
      Please check the logs and fix issues.
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

#### Email Notifications

```yaml
- name: Send Email Notification
  if: always()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "CI/CD Pipeline ${{ job.status }}: ${{ github.repository }}"
    to: team@company.com
    from: ci-cd@company.com
    body: |
      Pipeline Status: ${{ job.status }}
      Repository: ${{ github.repository }}
      Branch: ${{ github.ref_name }}
      Commit: ${{ github.sha }}
      
      View details: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

#### Pull Request Comments

The system automatically posts detailed test results as PR comments:

```markdown
# 🎉 CI/CD Pipeline Results

**Status:** EXCELLENT  
**Deployment Ready:** 🚀 YES  
**Confidence Score:** 95.0/100  
**Generated:** 2024-01-15 10:30:25 UTC

## 📊 Pipeline Overview

| Metric | Value |
|--------|-------|
| Stages Passed | 4/4 |
| Tests Passed | 245/250 |
| Success Rate | 98.0% |
| Failed Tests | 3 |
| Skipped Tests | 2 |
| Flaky Tests | 0 |

## 🔍 Stage Results

- ✅ **Smoke**: PASS
- ✅ **Fast Unit**: PASS
- ✅ **Fast Integration**: PASS
- ✅ **Fast Api Core**: PASS
- ✅ **Comprehensive**: PASS
- ✅ **Performance**: PASS

## 💡 Recommendations

- ✅ All critical tests passed - Ready for deployment
- Consider setting up production monitoring
- Review performance benchmarks for optimization opportunities

---
🎉 **All critical tests passed!** This build is ready for deployment.
```

---

## Security and Secrets Management

### Required Secrets

#### GitHub Repository Secrets

```bash
# Required for API integration
OPENAI_API_KEY=sk-...                    # OpenAI API key for embeddings

# Optional for enhanced notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...  # Slack notifications
EMAIL_USERNAME=notifications@company.com        # Email notifications
EMAIL_PASSWORD=app-specific-password            # Email app password

# Optional for external monitoring
PROMETHEUS_ENDPOINT=https://prometheus.company.com
DATADOG_API_KEY=...                     # DataDog integration
```

#### Environment-Specific Secrets

**Development/Testing**:
```bash
# Use mock values for testing
OPENAI_API_KEY=test-key-mock
API_TOKENS=test-token-32-chars-long-for-auth-1234567890abcdef
DATABASE_PASSWORD=changeme
```

**Staging**:
```bash
# Limited production-like keys
OPENAI_API_KEY=sk-staging-...
DATABASE_PASSWORD=staging-secure-password
REDIS_PASSWORD=staging-redis-password
```

**Production**:
```bash
# Full production secrets
OPENAI_API_KEY=sk-prod-...
DATABASE_PASSWORD=highly-secure-production-password
REDIS_PASSWORD=production-redis-password
ENCRYPTION_KEY=...
```

### Security Best Practices

#### Secret Rotation

```yaml
# Example secret rotation workflow
rotate-secrets:
  name: 🔄 Rotate Secrets
  if: github.event_name == 'schedule'
  runs-on: ubuntu-latest
  
  steps:
    - name: Generate new API tokens
      run: |
        # Generate new tokens
        NEW_TOKEN=$(python scripts/generate_secure_token.py)
        echo "NEW_TOKEN=$NEW_TOKEN" >> $GITHUB_ENV
        
    - name: Update secrets
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        # Update GitHub secrets
        gh secret set API_TOKENS --body "$NEW_TOKEN"
        
    - name: Deploy with new secrets
      run: |
        # Trigger deployment with new secrets
        gh workflow run deploy.yml
```

#### Security Scanning

```yaml
security-scan:
  name: 🔒 Security Scan
  runs-on: ubuntu-latest
  
  steps:
    - name: Run Bandit security scan
      run: |
        python -m bandit -r app/ -f json -o bandit-report.json
        
    - name: Check for secrets in code
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: main
        head: HEAD
        
    - name: Dependency vulnerability scan
      run: |
        python -m safety check --json --output safety-report.json
        
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
```

#### Access Control

**Repository Permissions**:
- **Read**: All team members
- **Write**: Senior developers, DevOps team
- **Admin**: Tech leads, DevOps leads

**Secret Access**:
- **Development secrets**: All developers
- **Staging secrets**: Senior developers, QA team
- **Production secrets**: DevOps team, Tech leads only

**Environment Protection Rules**:
```yaml
environments:
  staging:
    protection_rules:
      - type: required_reviewers
        required_reviewers: 1
      - type: wait_timer
        wait_timer: 5  # 5 minutes
        
  production:
    protection_rules:
      - type: required_reviewers
        required_reviewers: 2
      - type: wait_timer
        wait_timer: 30  # 30 minutes
      - type: deployment_branch_policy
        deployment_branch_policy: main
```

This comprehensive workflow documentation provides complete understanding of how the CI/CD system operates, from trigger to deployment, with all the necessary configuration details and security considerations.