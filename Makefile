# Second Brain v3.0.0 - Makefile
# Production-ready build and deployment automation

.PHONY: help
help: ## Show this help message
	@echo 'Second Brain v3.0.0 - Available commands:'
	@echo ''
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m%-30s\033[0m %s\n", "Command", "Description"} /^[a-zA-Z_-]+:.*?##/ { printf "\033[36m%-30s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Variables
DOCKER_COMPOSE = docker compose
DOCKER = docker
VERSION ?= 3.0.0
REGISTRY ?= secondbrain
APP_NAME = secondbrain
PYTHON = python3.11

# Development
.PHONY: dev
dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	@cp -n .env.example .env || true
	$(DOCKER_COMPOSE) up -d --build

.PHONY: dev-logs
dev-logs: ## Show development logs
	$(DOCKER_COMPOSE) logs -f app

.PHONY: shell
shell: ## Enter app container shell
	$(DOCKER_COMPOSE) exec app /bin/bash

.PHONY: db-shell
db-shell: ## Enter PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U secondbrain

# Testing
.PHONY: test
test: ## Run all tests
	@echo "🧪 Running tests..."
	$(DOCKER_COMPOSE) run --rm app pytest -v

.PHONY: test-unit
test-unit: ## Run unit tests
	$(DOCKER_COMPOSE) run --rm app pytest tests/unit -v

.PHONY: test-integration
test-integration: ## Run integration tests
	$(DOCKER_COMPOSE) run --rm app pytest tests/integration -v

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	$(DOCKER_COMPOSE) run --rm app pytest tests/e2e -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	$(DOCKER_COMPOSE) run --rm app pytest --cov=app --cov-report=html --cov-report=term

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

# Performance
.PHONY: benchmark
benchmark: ## Run performance benchmarks
	@echo "⚡ Running benchmarks..."
	$(DOCKER_COMPOSE) run --rm app python -m pytest tests/performance -v

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

# CI/CD
.PHONY: ci
ci: ## Run CI pipeline locally
	@echo "🤖 Running CI pipeline..."
	@$(MAKE) check
	@$(MAKE) build-prod
	@echo "✅ CI pipeline passed!"

# Default target
.DEFAULT_GOAL := help