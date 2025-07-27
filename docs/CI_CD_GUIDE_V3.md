# Second Brain v3.0.0 - CI/CD Guide

## Overview

This guide covers the continuous integration and deployment pipeline for Second Brain v3.0.0, using GitHub Actions as the primary CI/CD platform.

## Current Status

- **CI (Continuous Integration)**: ✅ Active - Tests run on every push
- **CD (Continuous Deployment)**: ✅ Active - Docker deployment validation on every push

## CI/CD Architecture

```mermaid
graph LR
    A[Developer Push] --> B[GitHub]
    B --> C[GitHub Actions]
    
    C --> D[Lint & Format]
    C --> E[Type Check]
    C --> F[Unit Tests]
    C --> G[Integration Tests]
    C --> H[Security Scan]
    
    D --> I{All Checks Pass?}
    E --> I
    F --> I
    G --> I
    H --> I
    
    I -->|Yes| J[Build Docker Image]
    I -->|No| K[Notify Developer]
    
    J --> L[Push to Registry]
    L --> M[Deploy to Staging]
    M --> N[Run E2E Tests]
    N --> O{Tests Pass?}
    
    O -->|Yes| P[Deploy to Production]
    O -->|No| Q[Rollback]
    
    P --> R[Monitor]
    Q --> K
```

## GitHub Actions Workflows

### Continuous Integration (CI) - Test Workflow

The CI workflow runs on every push and pull request to ensure code quality and test coverage.

**File**: `.github/workflows/test.yml`

### Continuous Deployment (CD) - Docker Deployment Workflow

The CD workflow validates Docker deployment on every push to main branch.

**File**: `.github/workflows/cd.yml`

Key features:
- Builds and validates Docker images
- Tests container startup and health
- Validates all services are accessible
- Runs security scans on containers
- Ensures API endpoints respond correctly

### Main CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'
  DOCKER_REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint-and-format:
    name: Lint and Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Run Black
        run: black --check src/ tests/
      
      - name: Run Ruff
        run: ruff check src/ tests/
      
      - name: Run isort
        run: isort --check-only src/ tests/

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Run mypy
        run: mypy src/ --strict

  test:
    name: Test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration]
    
    services:
      postgres:
        image: ankane/pgvector:v0.5.1-pg16
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
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
      
      rabbitmq:
        image: rabbitmq:3-management
        env:
          RABBITMQ_DEFAULT_USER: test
          RABBITMQ_DEFAULT_PASS: test
        ports:
          - 5672:5672
      
      minio:
        image: minio/minio
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        options: >-
          --health-cmd "curl -f http://localhost:9000/minio/health/live"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 9000:9000

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-v3.txt
          pip install -r requirements-dev.txt
      
      - name: Set up test environment
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
          RABBITMQ_URL: amqp://test:test@localhost:5672/
          MINIO_ENDPOINT: localhost:9000
          MINIO_ACCESS_KEY: minioadmin
          MINIO_SECRET_KEY: minioadmin
          USE_MOCK_OPENAI: true
        run: |
          # Run migrations
          alembic upgrade head
          
          # Create MinIO bucket
          pip install minio
          python -c "
          from minio import Minio
          client = Minio('localhost:9000', 'minioadmin', 'minioadmin', secure=False)
          if not client.bucket_exists('test-bucket'):
              client.make_bucket('test-bucket')
          "
      
      - name: Run ${{ matrix.test-type }} tests
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
          RABBITMQ_URL: amqp://test:test@localhost:5672/
          MINIO_ENDPOINT: localhost:9000
          MINIO_ACCESS_KEY: minioadmin
          MINIO_SECRET_KEY: minioadmin
          USE_MOCK_OPENAI: true
        run: |
          if [ "${{ matrix.test-type }}" = "unit" ]; then
            pytest tests/unit/ -v --cov=src --cov-report=xml
          else
            pytest tests/integration/ -v --cov=src --cov-report=xml --cov-append
          fi
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: ${{ matrix.test-type }}

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
      
      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-results.json
      
      - name: Run Safety check
        run: |
          pip install safety
          safety check --json

  build-and-push:
    name: Build and Push Docker Image
    needs: [lint-and-format, type-check, test, security-scan]
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')
    
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.DOCKER_REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  deploy-staging:
    name: Deploy to Staging
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.secondbrain.example.com
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Kubernetes
        env:
          KUBE_CONFIG: ${{ secrets.STAGING_KUBE_CONFIG }}
        run: |
          echo "$KUBE_CONFIG" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          
          # Update image
          kubectl set image deployment/secondbrain-api \
            api=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:develop \
            -n secondbrain-staging
          
          # Wait for rollout
          kubectl rollout status deployment/secondbrain-api -n secondbrain-staging

  e2e-tests:
    name: E2E Tests
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install test dependencies
        run: |
          pip install pytest pytest-asyncio httpx
      
      - name: Run E2E tests
        env:
          API_URL: https://staging.secondbrain.example.com
          TEST_API_KEY: ${{ secrets.STAGING_API_KEY }}
        run: pytest tests/e2e/ -v

  deploy-production:
    name: Deploy to Production
    needs: [build-and-push, e2e-tests]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://api.secondbrain.example.com
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Kubernetes
        env:
          KUBE_CONFIG: ${{ secrets.PROD_KUBE_CONFIG }}
        run: |
          echo "$KUBE_CONFIG" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          
          # Update image
          kubectl set image deployment/secondbrain-api \
            api=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:main \
            -n secondbrain-prod
          
          # Wait for rollout
          kubectl rollout status deployment/secondbrain-api -n secondbrain-prod
      
      - name: Run smoke tests
        env:
          API_URL: https://api.secondbrain.example.com
        run: |
          # Basic health check
          curl -f $API_URL/health || exit 1
          
          # Check critical endpoints
          curl -f -H "Authorization: Bearer ${{ secrets.PROD_MONITORING_TOKEN }}" \
            $API_URL/api/v1/memories || exit 1
```

### Pull Request Workflow

```yaml
# .github/workflows/pr.yml
name: Pull Request

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  pr-title:
    name: Validate PR Title
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  size-check:
    name: PR Size Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check PR size
        uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request;
            const additions = pr.additions;
            const deletions = pr.deletions;
            const total = additions + deletions;
            
            if (total > 1000) {
              core.warning(`Large PR detected: ${total} lines changed. Consider breaking it down.`);
            }

  dependency-review:
    name: Dependency Review
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v3
```

### Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Generate changelog
        id: changelog
        uses: mikepenz/release-changelog-builder-action@v4
        with:
          configuration: ".github/changelog-config.json"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body: ${{ steps.changelog.outputs.changelog }}
          draft: false
          prerelease: false
      
      - name: Build and push production image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./docker/Dockerfile
          push: true
          tags: |
            ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.ref_name }}
            ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          platforms: linux/amd64,linux/arm64
```

## Branch Protection Rules

### Main Branch
- Require pull request reviews (2 approvals)
- Dismiss stale pull request approvals
- Require review from CODEOWNERS
- Require status checks to pass:
  - lint-and-format
  - type-check
  - test (unit)
  - test (integration)
  - security-scan
- Require branches to be up to date
- Include administrators
- Restrict who can push

### Develop Branch
- Require pull request reviews (1 approval)
- Require status checks to pass
- Require branches to be up to date

## Secrets Management

### Required GitHub Secrets

```yaml
# Repository Secrets
STAGING_KUBE_CONFIG     # Base64 encoded kubeconfig for staging
PROD_KUBE_CONFIG        # Base64 encoded kubeconfig for production
STAGING_API_KEY         # API key for staging environment
PROD_MONITORING_TOKEN   # Token for production monitoring
CODECOV_TOKEN          # Codecov upload token
SONAR_TOKEN            # SonarCloud token (optional)

# Environment Secrets (Staging)
DATABASE_URL           # PostgreSQL connection string
REDIS_URL             # Redis connection string
RABBITMQ_URL          # RabbitMQ connection string
OPENAI_API_KEY        # OpenAI API key
JWT_SECRET_KEY        # JWT signing key

# Environment Secrets (Production)
# Same as staging but with production values
```

### Secrets Rotation

```yaml
# .github/workflows/rotate-secrets.yml
name: Rotate Secrets

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly
  workflow_dispatch:

jobs:
  rotate:
    name: Rotate Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Rotate JWT Secret
        run: |
          NEW_SECRET=$(openssl rand -base64 32)
          # Update in Kubernetes
          kubectl create secret generic secondbrain-secrets \
            --from-literal=JWT_SECRET_KEY=$NEW_SECRET \
            --dry-run=client -o yaml | kubectl apply -f -
```

## Quality Gates

### Code Coverage
- Minimum coverage: 80%
- New code coverage: 90%
- Coverage trends tracked in Codecov

### Performance Benchmarks
```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmark

on:
  push:
    branches: [main, develop]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run benchmarks
        run: |
          python -m pytest tests/benchmarks/ \
            --benchmark-only \
            --benchmark-json=benchmark.json
      
      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
```

## Monitoring & Alerts

### Build Status Dashboard
```yaml
# README.md badges
![CI/CD](https://github.com/user/secondbrain/workflows/CI/CD/badge.svg)
![Coverage](https://codecov.io/gh/user/secondbrain/branch/main/graph/badge.svg)
![Security](https://snyk.io/test/github/user/secondbrain/badge.svg)
```

### Slack Notifications
```yaml
- name: Notify Slack
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Build failed in ${{ github.repository }}'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Rollback Procedures

### Automatic Rollback
```yaml
- name: Check deployment health
  run: |
    for i in {1..10}; do
      if curl -f https://api.example.com/health; then
        echo "Health check passed"
        exit 0
      fi
      sleep 30
    done
    echo "Health check failed, rolling back"
    kubectl rollout undo deployment/secondbrain-api
    exit 1
```

### Manual Rollback
```bash
# List deployment history
kubectl rollout history deployment/secondbrain-api

# Rollback to previous version
kubectl rollout undo deployment/secondbrain-api

# Rollback to specific revision
kubectl rollout undo deployment/secondbrain-api --to-revision=3
```

## Cost Optimization

### GitHub Actions Optimization
1. **Use caching**: Cache dependencies, Docker layers
2. **Matrix builds**: Parallelize independent jobs
3. **Conditional runs**: Skip unnecessary workflows
4. **Self-hosted runners**: For resource-intensive tasks

### Resource Usage
```yaml
# Limit concurrent workflows
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Best Practices

### 1. Commit Messages
Follow conventional commits:
```
feat: add new memory search algorithm
fix: resolve cache invalidation issue
docs: update API documentation
perf: optimize database queries
test: add integration tests for search
```

### 2. PR Guidelines
- Keep PRs small and focused
- Include tests with new features
- Update documentation
- Add PR description template

### 3. Security
- Never commit secrets
- Use environment variables
- Scan dependencies regularly
- Enable Dependabot

### 4. Performance
- Monitor build times
- Optimize Docker images
- Use build caching
- Parallelize tests

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check logs in Actions tab
   - Verify all secrets are set
   - Ensure services are healthy

2. **Test Failures**
   - Run tests locally first
   - Check service dependencies
   - Verify test data setup

3. **Deployment Issues**
   - Verify Kubernetes connectivity
   - Check image pull permissions
   - Review deployment logs

### Debug Mode
```yaml
- name: Debug
  if: failure()
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    kubectl describe pod -l app=secondbrain-api
    kubectl logs -l app=secondbrain-api --tail=100
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Kubernetes GitHub Actions](https://github.com/Azure/k8s-deploy)
- [Codecov Integration](https://docs.codecov.com/docs/github-actions)