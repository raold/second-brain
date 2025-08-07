# Second Brain - Docker-First Development
# Zero host Python dependencies required

.PHONY: help
help: ## Show this help message
	@echo "Second Brain - Docker-First Development Commands"
	@echo "================================================"
	@echo ""
	@echo "🐳 Docker-first approach: All commands prefer Docker, fallback to .venv"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m%-20s\033[0m %s\n", "Command", "Description"} /^[a-zA-Z_-]+:.*?##/ { printf "\033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER = docker
VERSION ?= 3.0.0
REGISTRY ?= secondbrain
APP_NAME = secondbrain

# Core development commands (Docker-first with .venv fallback)
.PHONY: setup
setup: ## Set up development environment (Docker + .venv fallback)
	@python scripts/dev start

.PHONY: dev
dev: ## Start development environment (Docker-first)
	@python scripts/dev start

.PHONY: dev-stop
dev-stop: ## Stop development environment
	@python scripts/dev stop

.PHONY: dev-logs
dev-logs: ## Show development logs
	$(DOCKER_COMPOSE) logs -f app

.PHONY: shell
shell: ## Enter development shell (Docker-first)
	@python scripts/dev shell

.PHONY: status
status: ## Show development environment status
	@python scripts/dev status

.PHONY: db-shell
db-shell: ## Enter PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U secondbrain

# Enhanced Testing - Tiered CI/CD Strategy
.PHONY: test
test: ## Run all tests (legacy command)
	@python scripts/ci_runner.py --stage all

.PHONY: test-smoke
test-smoke: ## Run smoke tests (critical path, <60s)
	@python scripts/ci_runner.py --stage smoke

.PHONY: test-fast
test-fast: ## Run fast feedback tests (core functionality, <5min)
	@python scripts/ci_runner.py --stage fast

.PHONY: test-fast-unit
test-fast-unit: ## Run fast unit tests only
	@python scripts/ci_runner.py --stage fast --group unit

.PHONY: test-fast-integration
test-fast-integration: ## Run fast integration tests only
	@python scripts/ci_runner.py --stage fast --group integration-basic

.PHONY: test-fast-api
test-fast-api: ## Run fast API tests only
	@python scripts/ci_runner.py --stage fast --group api-core

.PHONY: test-comprehensive
test-comprehensive: ## Run comprehensive validation tests (<15min)
	@python scripts/ci_runner.py --stage comprehensive

.PHONY: test-performance
test-performance: ## Run performance benchmarks (<20min)
	@python scripts/ci_runner.py --stage performance

# Legacy test commands (for backward compatibility)
.PHONY: test-unit
test-unit: ## Run unit tests (legacy)
	@python -m pytest tests/unit/ -v -m "unit and not slow"

.PHONY: test-integration
test-integration: ## Run integration tests (legacy)
	@python -m pytest tests/integration/ -v -m "integration and not slow"

.PHONY: test-validation
test-validation: ## Run validation tests (legacy)
	@python -m pytest tests/validation/ -v

# CI/CD Pipeline Simulation
.PHONY: ci-smoke
ci-smoke: ## Simulate CI smoke tests stage
	@echo "🔥 Simulating CI Smoke Tests..."
	@python scripts/ci_runner.py --stage smoke --exit-on-failure

.PHONY: ci-fast
ci-fast: ## Simulate CI fast feedback stage
	@echo "⚡ Simulating CI Fast Feedback..."
	@python scripts/ci_runner.py --stage fast --exit-on-failure

.PHONY: ci-comprehensive
ci-comprehensive: ## Simulate CI comprehensive stage
	@echo "🔍 Simulating CI Comprehensive Tests..."
	@python scripts/ci_runner.py --stage comprehensive --exit-on-failure

.PHONY: ci-performance
ci-performance: ## Simulate CI performance stage
	@echo "📊 Simulating CI Performance Tests..."
	@python scripts/ci_runner.py --stage performance

.PHONY: ci-full
ci-full: ## Run complete CI pipeline simulation
	@echo "🤖 Running Full CI Pipeline Simulation..."
	@python scripts/ci_runner.py --stage all --save-report ci_simulation_report.json

.PHONY: ci-local
ci-local: ## Run CI pipeline locally with reporting
	@echo "🏠 Running Local CI Pipeline..."
	@python scripts/ci_runner.py --stage all --save-report local_ci_report.json

# Code Quality
.PHONY: lint
lint: ## Run linters (ruff, black, mypy)
	@echo "🔍 Running linters..."
	$(DOCKER_COMPOSE) run --rm app ruff check .
	$(DOCKER_COMPOSE) run --rm app black --check .
	$(DOCKER_COMPOSE) run --rm app mypy . --strict

.PHONY: format
format: ## Format code with black and ruff
	@echo "🎨 Formatting code..."
	$(DOCKER_COMPOSE) run --rm app black .
	$(DOCKER_COMPOSE) run --rm app ruff check --fix .

.PHONY: security
security: ## Run security checks (bandit, safety)
	@echo "🔒 Running security checks..."
	$(DOCKER_COMPOSE) run --rm app bandit -r app/
	$(DOCKER_COMPOSE) run --rm app safety check

# Database
.PHONY: db-migrate
db-migrate: ## Run database migrations
	$(DOCKER_COMPOSE) run --rm app alembic upgrade head

.PHONY: db-rollback
db-rollback: ## Rollback last migration
	$(DOCKER_COMPOSE) run --rm app alembic downgrade -1

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys data)
	@echo "⚠️  This will destroy all data. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d postgres
	sleep 5
	$(MAKE) db-migrate

# Docker
.PHONY: build
build: ## Build Docker images
	@echo "🏗️  Building Docker images..."
	$(DOCKER_COMPOSE) build

.PHONY: build-prod
build-prod: ## Build production Docker image
	@echo "🏗️  Building production image..."
	$(DOCKER) build -f docker/Dockerfile --target runtime -t $(REGISTRY)/$(APP_NAME):$(VERSION) .

.PHONY: push
push: build-prod ## Push Docker image to registry
	@echo "📤 Pushing to registry..."
	$(DOCKER) push $(REGISTRY)/$(APP_NAME):$(VERSION)
	$(DOCKER) tag $(REGISTRY)/$(APP_NAME):$(VERSION) $(REGISTRY)/$(APP_NAME):latest
	$(DOCKER) push $(REGISTRY)/$(APP_NAME):latest

# Deployment
.PHONY: deploy-local
deploy-local: ## Deploy to local Docker
	@echo "🚀 Deploying locally..."
	$(DOCKER_COMPOSE) up -d

.PHONY: deploy-swarm
deploy-swarm: ## Deploy to Docker Swarm
	@echo "🚀 Deploying to Swarm..."
	docker stack deploy -c compose.yaml secondbrain

.PHONY: deploy-k8s
deploy-k8s: ## Deploy to Kubernetes (future)
	@echo "🚀 Deploying to Kubernetes..."
	@echo "TODO: Implement Helm deployment"
	# helm upgrade --install secondbrain ./helm/secondbrain

# Monitoring
.PHONY: logs
logs: ## Show all logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: stats
stats: ## Show container stats
	$(DOCKER) stats

.PHONY: health
health: ## Check service health
	@echo "🏥 Checking health..."
	@curl -f http://localhost:8000/health || echo "❌ App unhealthy"
	@curl -f http://localhost:9090/metrics || echo "❌ Metrics unavailable"
	@$(DOCKER_COMPOSE) ps

# Cleanup
.PHONY: clean
clean: ## Clean up containers and volumes
	@echo "🧹 Cleaning up..."
	$(DOCKER_COMPOSE) down

.PHONY: clean-all
clean-all: ## Clean everything including volumes (WARNING: destroys data)
	@echo "⚠️  This will destroy all data. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	$(DOCKER_COMPOSE) down -v
	$(DOCKER) system prune -af

# Utilities
.PHONY: backup
backup: ## Backup database and data
	@echo "💾 Creating backup..."
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U secondbrain > backups/db_$(shell date +%Y%m%d_%H%M%S).sql
	$(DOCKER_COMPOSE) run --rm -v $(PWD)/backups:/backup app tar czf /backup/data_$(shell date +%Y%m%d_%H%M%S).tar.gz /app/data

.PHONY: restore
restore: ## Restore from backup (specify BACKUP_FILE)
	@echo "📥 Restoring from backup..."
	@test -n "$(BACKUP_FILE)" || (echo "❌ Please specify BACKUP_FILE" && exit 1)
	$(DOCKER_COMPOSE) exec -T postgres psql -U secondbrain < $(BACKUP_FILE)

.PHONY: version
version: ## Show version information
	@echo "Second Brain v$(VERSION)"
	@echo "Docker: $(shell docker --version)"
	@echo "Docker Compose: $(shell docker compose version)"
	@echo "Python: $(shell $(PYTHON) --version)"

# Performance Testing (Enhanced)
.PHONY: benchmark
benchmark: ## Run performance benchmarks
	@echo "⚡ Running performance benchmarks..."
	@python scripts/run_performance_tests.py --type benchmark

.PHONY: load-test
load-test: ## Run load tests (moderate intensity)
	@echo "🚀 Running load tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity moderate

.PHONY: load-test-basic
load-test-basic: ## Run basic load tests (CI-friendly)
	@echo "🚀 Running basic load tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity basic

.PHONY: load-test-intensive
load-test-intensive: ## Run intensive load tests
	@echo "🚀 Running intensive load tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity intensive

.PHONY: perf-test
perf-test: ## Run complete performance test suite
	@echo "⚡ Running complete performance test suite..."
	@python scripts/run_performance_tests.py --type both --load-intensity moderate

.PHONY: perf-test-quick
perf-test-quick: ## Run quick performance tests (CI/CD)
	@echo "⚡ Running quick performance tests..."
	@python scripts/run_performance_tests.py --type both --quick

.PHONY: profile
profile: ## Profile application
	@echo "📊 Profiling application..."
	$(DOCKER_COMPOSE) run --rm -e PROFILING=true app

# Development Workflow
.PHONY: setup
setup: ## Initial project setup
	@echo "🔧 Setting up project..."
	@cp -n .env.example .env || true
	@$(MAKE) build
	@$(MAKE) db-migrate
	@echo "✅ Setup complete! Run 'make dev' to start."

.PHONY: update
update: ## Update dependencies
	@echo "📦 Updating dependencies..."
	$(DOCKER_COMPOSE) run --rm app pip-compile --upgrade requirements.in
	$(DOCKER_COMPOSE) run --rm app pip-compile --upgrade requirements-dev.in

.PHONY: check
check: lint test security ## Run all checks (lint, test, security)
	@echo "✅ All checks passed!"

# Enhanced CI/CD
.PHONY: ci
ci: ## Run CI pipeline locally (new tiered approach)
	@echo "🤖 Running Enhanced CI Pipeline..."
	@$(MAKE) ci-full

# Security & Compliance
.PHONY: security-scan
security-scan: ## Run comprehensive security scans
	@echo "🔒 Running security scans..."
	@python scripts/ci_runner.py --stage security --save-report security_report.json

.PHONY: license-check
license-check: ## Check license compliance
	@echo "📜 Checking license compliance..."
	@python scripts/ci_runner.py --stage license-check --save-report license_report.json

.PHONY: vulnerability-scan
vulnerability-scan: ## Scan for vulnerabilities
	@echo "🛡️ Scanning for vulnerabilities..."
	@python scripts/ci_runner.py --stage vulnerability --save-report vulnerability_report.json

# Advanced Testing
.PHONY: test-parallel
test-parallel: ## Run tests in parallel
	@echo "⚡ Running tests in parallel..."
	@python -m pytest -n auto tests/

.PHONY: test-coverage
test-coverage: ## Generate detailed coverage report
	@echo "📊 Generating coverage report..."
	@python -m pytest --cov=app --cov-report=html --cov-report=xml --cov-report=json

.PHONY: test-mutation
test-mutation: ## Run mutation testing (when available)
	@echo "🧬 Running mutation tests..."
	@echo "TODO: Implement mutation testing with mutmut"

# Performance & Load Testing
.PHONY: stress-test
stress-test: ## Run stress tests
	@echo "💪 Running stress tests..."
	@python scripts/run_performance_tests.py --type stress

.PHONY: memory-test
memory-test: ## Run memory usage tests
	@echo "🧠 Running memory tests..."
	@python scripts/run_performance_tests.py --type memory

.PHONY: cpu-profile
cpu-profile: ## Profile CPU usage
	@echo "⚡ Profiling CPU usage..."
	@python scripts/run_performance_tests.py --type cpu-profile

# Code Quality Enhancement
.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "🔍 Running type checks..."
	$(DOCKER_COMPOSE) run --rm app mypy app/ --strict --show-error-codes

.PHONY: complexity-check
complexity-check: ## Check code complexity
	@echo "📈 Checking code complexity..."
	$(DOCKER_COMPOSE) run --rm app python -m mccabe --min 10 app/

.PHONY: dead-code
dead-code: ## Find dead code
	@echo "💀 Finding dead code..."
	$(DOCKER_COMPOSE) run --rm app vulture app/

# Documentation & Reporting
.PHONY: generate-docs
generate-docs: ## Generate API documentation
	@echo "📚 Generating documentation..."
	@python scripts/update_documentation.py --generate-all

.PHONY: api-spec
api-spec: ## Generate OpenAPI specification
	@echo "📋 Generating API spec..."
	@python scripts/generate_openapi_spec.py

.PHONY: metrics-report
metrics-report: ## Generate metrics and health report
	@echo "📊 Generating metrics report..."
	@python scripts/generate_metrics_report.py

# Docker Testing Enhancement
.PHONY: docker-test
docker-test: ## Run tests in Docker containers
	@echo "🐳 Running tests in Docker..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up --build --abort-on-container-exit

.PHONY: docker-security
docker-security: ## Scan Docker images for security issues
	@echo "🐳🔒 Scanning Docker images..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image secondbrain:latest

# Environment Validation
.PHONY: validate-env
validate-env: ## Validate environment configuration
	@echo "✅ Validating environment..."
	@python scripts/validate_environment.py --comprehensive

.PHONY: validate-deps
validate-deps: ## Validate dependencies
	@echo "📦 Validating dependencies..."
	@python scripts/validate_dependencies.py --check-security

.PHONY: validate-config
validate-config: ## Validate configuration files
	@echo "⚙️ Validating configuration..."
	@python scripts/validate_configurations.py --check-security

# Project Standards Validation (NEW)
.PHONY: validate-naming
validate-naming: ## Validate naming conventions across project
	@echo "📋 Validating naming conventions..."
	@python scripts/validate_naming_conventions.py --verbose

.PHONY: validate-docs
validate-docs: ## Validate documentation consistency
	@echo "📚 Validating documentation consistency..."
	@python scripts/validate_documentation.py --verbose

.PHONY: validate-standards
validate-standards: ## Validate all project standards (naming, docs, config)
	@echo "🎯 Validating all project standards..."
	@python scripts/validate_naming_conventions.py
	@python scripts/validate_documentation.py
	@python scripts/validate_configurations.py --check-security
	@echo "✅ All project standards validated!"

.PHONY: fix-standards
fix-standards: ## Attempt to fix standards violations (dry-run)
	@echo "🔧 Attempting to fix standards violations (dry-run)..."
	@python scripts/validate_naming_conventions.py --fix --dry-run
	@echo "Run without --dry-run to apply fixes"

# Test Reporting
.PHONY: test-report
test-report: ## Generate comprehensive test report
	@echo "📋 Generating test report..."
	@python scripts/ci_runner.py --stage all --save-report comprehensive_test_report.json
	@python scripts/generate_test_summary.py --report comprehensive_test_report.json --output test_summary.html

# Developer Convenience Commands
.PHONY: pre-commit
pre-commit: ## Run pre-commit checks (standards + smoke + fast tests)
	@echo "🔧 Running pre-commit checks..."
	@$(MAKE) validate-standards
	@$(MAKE) test-smoke
	@$(MAKE) test-fast-unit

.PHONY: pre-push
pre-push: ## Run pre-push checks (comprehensive tests)
	@echo "🚀 Running pre-push checks..."
	@$(MAKE) test-comprehensive

.PHONY: pre-release
pre-release: ## Run pre-release checks (all tests + performance)
	@echo "🎯 Running pre-release checks..."
	@$(MAKE) ci-full
	@$(MAKE) perf-test-quick

# Help sections
.PHONY: help-testing
help-testing: ## Show detailed testing help
	@echo "🧪 Testing Commands - Tiered Strategy"
	@echo "====================================="
	@echo ""
	@echo "Quick Testing (for development):"
	@echo "  make test-smoke         - Critical path tests (<60s)"
	@echo "  make test-fast          - Core functionality tests (<5min)"
	@echo "  make pre-commit         - Pre-commit validation"
	@echo ""
	@echo "Comprehensive Testing:"
	@echo "  make test-comprehensive - Full validation (<15min)"
	@echo "  make test-performance   - Performance benchmarks (<20min)"
	@echo "  make ci-full           - Complete CI simulation"
	@echo ""
	@echo "Development Workflow:"
	@echo "  make pre-commit        - Before committing code"
	@echo "  make pre-push          - Before pushing to remote"
	@echo "  make pre-release       - Before releasing"

# Default target
.DEFAULT_GOAL := help