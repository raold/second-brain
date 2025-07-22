# Second Brain v2.8.x CI/CD Workflows

This directory contains the GitHub Actions workflows for the Second Brain v2.8.x series.

## Active Workflows

### Core Pipeline
- **`ci-v2.8.yml`** - Main CI/CD pipeline with quality checks, testing, building, and deployment
  - Runs on: Push to main/develop, PRs, manual dispatch
  - Features: Parallel test matrix, multi-platform Docker builds, security scanning

### Specialized Workflows
- **`test-suite-v2.8.yml`** - Comprehensive test suite with detailed test groups
  - Runs on: Push, PR, weekly schedule, manual dispatch
  - Test groups: Unit, Integration, Performance, Security, API, AI/ML

- **`migration-tests-v2.8.yml`** - Migration system testing
  - Runs on: Changes to migration files
  - Tests: Database migrations, memory migrations, dashboard migrations

- **`deploy-v2.8.yml`** - Deployment workflow for staging and production
  - Runs on: Successful CI completion, manual dispatch
  - Environments: Staging (auto), Production (manual approval)

- **`pages.yml`** - GitHub Pages deployment for documentation
  - Runs on: Push to main, manual dispatch
  - Deploys: Static site, dashboards, API documentation

## Disabled/Legacy Workflows

The following workflows have been disabled and renamed with `.disabled` extension:
- `ci.yaml.disabled` - Legacy v2.4.3 pipeline
- `migration-tests.yml.disabled` - Old migration tests
- `deploy-v2.yml.disabled` - Old deployment workflow

## Workflow Features

### 🚀 Performance Optimizations
- Parallel job execution with matrix strategy
- Intelligent caching for dependencies and build artifacts
- Multi-platform Docker builds (AMD64 & ARM64)
- Concurrent test execution with pytest-xdist

### 🔒 Security
- Container vulnerability scanning with Trivy
- Secret detection with detect-secrets
- SAST scanning with Bandit and Semgrep
- SBOM generation for supply chain security

### 📊 Quality Assurance
- Linting with Ruff (combining Black, isort, flake8, and more)
- Type checking with mypy
- Code coverage tracking with Codecov
- Performance benchmarking for critical paths

### 🏗️ Build & Deploy
- Multi-stage Docker builds
- Automatic version detection from code
- Environment-specific configurations
- Health checks and rollback procedures

## Environment Variables

### Required Secrets
- `GITHUB_TOKEN` - Automatically provided
- `CODECOV_TOKEN` - For coverage reporting
- `OPENAI_API_KEY` - For production deployments
- `DATABASE_URL` - PostgreSQL connection string
- `API_TOKENS` - Authentication tokens

### Workflow Configuration
```yaml
env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'
  REGISTRY: ghcr.io
  USE_MOCK_DATABASE: 'true'  # For CI tests
  RUFF_VERSION: '0.12.4'
```

## Usage

### Manual Workflow Dispatch

Run specific test groups:
```bash
gh workflow run test-suite-v2.8.yml -f test_group=unit
```

Deploy to staging:
```bash
gh workflow run deploy-v2.8.yml -f environment=staging
```

### Branch Protection

Recommended branch protection rules for `main`:
- Require PR reviews (1+)
- Require status checks:
  - `quality-checks`
  - `test-suite / Unit Tests - Core`
  - `test-suite / Integration Tests`
  - `build-docker`
- Require branches to be up to date
- Include administrators

## Monitoring

### Workflow Status
- GitHub Actions tab: View all workflow runs
- Branch protection: Ensure critical checks pass
- Deployment environments: Track deployment status

### Metrics
- Test coverage: Target 70%+ coverage
- Build time: Optimized for <10 minutes
- Test performance: Parallel execution with timeout limits

## Troubleshooting

### Common Issues

1. **Linting failures**: Run `ruff check . --fix` locally
2. **Test failures**: Check if `USE_MOCK_DATABASE` is set correctly
3. **Docker build issues**: Ensure multi-platform support is enabled
4. **Deployment failures**: Verify environment secrets are set

### Debug Mode

Enable debug logging:
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

## Migration from Legacy Workflows

If you're upgrading from v2.4.x workflows:

1. Update your branch protection rules to use new workflow names
2. Update any external integrations pointing to old workflows
3. Verify all secrets are available in new environments
4. Test workflows in a feature branch before merging

## Contributing

When modifying workflows:
1. Test changes in a feature branch
2. Use workflow dispatch for manual testing
3. Ensure backward compatibility
4. Update this README with any changes

---

For more information, see the [GitHub Actions documentation](https://docs.github.com/en/actions).