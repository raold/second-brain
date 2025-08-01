#!/usr/bin/env python3
"""
Update Makefile with enhanced CI/CD pipeline commands

This script adds the new CI/CD pipeline commands to the existing Makefile
while preserving existing functionality.
"""

def update_makefile():
    """Update Makefile with enhanced CI/CD commands."""
    
    # Read existing Makefile
    makefile_path = "/Users/dro/Documents/second-brain/Makefile"
    
    with open(makefile_path, 'r') as f:
        content = f.read()
    
    # Add new CI/CD commands after line 100
    new_commands = '''
# Enhanced CI/CD Pipeline Commands
.PHONY: ci-smoke
ci-smoke: ## Run CI smoke tests (<60s)
	@echo "🔥 Running CI Smoke Tests..."
	@python scripts/ci_runner.py --stage smoke --exit-on-failure

.PHONY: ci-core
ci-core: ## Run CI core validation (<10min)
	@echo "🧪 Running CI Core Validation..."
	@python scripts/ci_runner.py --stage fast --exit-on-failure

.PHONY: ci-security
ci-security: ## Run security and quality checks (<15min)
	@echo "🔒 Running Security & Quality Checks..."
	@$(MAKE) security
	@$(MAKE) lint

.PHONY: ci-full
ci-full: ## Run complete CI pipeline
	@echo "🤖 Running Complete CI Pipeline..."
	@python scripts/ci_runner.py --stage all --save-report ci_pipeline_report.json

# Deployment Health Checks
.PHONY: health-check
health-check: ## Check deployment health
	@echo "🏥 Running Health Checks..."
	@python scripts/deployment_health_check.py --url http://localhost:8000

.PHONY: health-check-staging
health-check-staging: ## Check staging environment health
	@echo "🏥 Checking Staging Health..."
	@python scripts/deployment_health_check.py --url https://staging.secondbrain.ai --environment staging

.PHONY: health-check-production
health-check-production: ## Check production environment health
	@echo "🏥 Checking Production Health..."
	@python scripts/deployment_health_check.py --url https://secondbrain.ai --environment production

# Performance Testing
.PHONY: perf-benchmark
perf-benchmark: ## Run performance benchmarks
	@echo "⚡ Running Performance Benchmarks..."
	@python scripts/run_performance_tests.py --type benchmark

.PHONY: perf-load-basic
perf-load-basic: ## Run basic load tests
	@echo "🚀 Running Basic Load Tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity basic

.PHONY: perf-load-moderate
perf-load-moderate: ## Run moderate load tests
	@echo "🚀 Running Moderate Load Tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity moderate

.PHONY: perf-load-intensive
perf-load-intensive: ## Run intensive load tests
	@echo "🚀 Running Intensive Load Tests..."
	@python scripts/run_performance_tests.py --type load --load-intensity intensive

.PHONY: perf-full
perf-full: ## Run complete performance test suite
	@echo "⚡ Running Complete Performance Suite..."
	@python scripts/run_performance_tests.py --type both --load-intensity moderate --save-report performance_report.json

.PHONY: perf-quick
perf-quick: ## Run quick performance tests (CI-friendly)
	@echo "⚡ Running Quick Performance Tests..."
	@python scripts/run_performance_tests.py --type both --quick

# Pre-commit and Pre-push Hooks
.PHONY: pre-commit
pre-commit: ## Run pre-commit checks (smoke + fast unit tests)
	@echo "🔧 Running Pre-Commit Checks..."
	@$(MAKE) ci-smoke
	@$(MAKE) test-fast-unit

.PHONY: pre-push
pre-push: ## Run pre-push checks (comprehensive validation)
	@echo "🚀 Running Pre-Push Checks..."
	@$(MAKE) ci-core
	@$(MAKE) ci-security

.PHONY: pre-release
pre-release: ## Run pre-release checks (full pipeline + performance)
	@echo "🎯 Running Pre-Release Checks..."
	@$(MAKE) ci-full
	@$(MAKE) perf-quick

# Pipeline Status and Reporting
.PHONY: pipeline-status
pipeline-status: ## Show CI/CD pipeline status
	@echo "📊 CI/CD Pipeline Status"
	@echo "========================"
	@echo "Smoke Tests: make ci-smoke (target: <60s)"
	@echo "Core Validation: make ci-core (target: <10min)"
	@echo "Security & Quality: make ci-security (target: <15min)"
	@echo "Performance: make perf-quick (target: <5min)"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make pre-commit  - Before committing code"
	@echo "  make pre-push    - Before pushing to remote"
	@echo "  make pre-release - Before creating release"

.PHONY: pipeline-report
pipeline-report: ## Generate comprehensive pipeline report
	@echo "📋 Generating Pipeline Report..."
	@python scripts/ci_runner.py --stage all --save-report comprehensive_pipeline_report.json
	@echo "Report saved to: comprehensive_pipeline_report.json"

# Help section for CI/CD
.PHONY: help-cicd
help-cicd: ## Show CI/CD pipeline help
	@echo "🤖 CI/CD Pipeline Commands"
	@echo "=========================="
	@echo ""
	@echo "🔥 Smoke Tests (Critical Path - <60s):"
	@echo "  make ci-smoke           - Run critical path validation"
	@echo ""
	@echo "🧪 Core Validation (<10min):"
	@echo "  make ci-core            - Run comprehensive testing"
	@echo "  make test-fast-unit     - Unit tests only"
	@echo "  make test-fast-integration - Integration tests only"
	@echo "  make test-fast-api      - API tests only"
	@echo ""
	@echo "🔒 Security & Quality (<15min):"
	@echo "  make ci-security        - Security and code quality"
	@echo "  make security           - Security scans only"
	@echo "  make lint               - Code quality only"
	@echo ""
	@echo "⚡ Performance Testing:"
	@echo "  make perf-benchmark     - Performance benchmarks"
	@echo "  make perf-load-basic    - Basic load testing"
	@echo "  make perf-quick         - Quick performance check"
	@echo ""
	@echo "🏥 Health Checks:"
	@echo "  make health-check       - Local deployment health"
	@echo "  make health-check-staging - Staging environment"
	@echo "  make health-check-production - Production environment"
	@echo ""
	@echo "🔧 Development Workflow:"
	@echo "  make pre-commit         - Before git commit"
	@echo "  make pre-push           - Before git push"
	@echo "  make pre-release        - Before release"
	@echo ""
	@echo "📊 Reporting:"
	@echo "  make pipeline-status    - Show pipeline overview"
	@echo "  make pipeline-report    - Generate detailed report"

'''
    
    # Find where to insert the new commands (after the existing CI/CD section)
    lines = content.split('\n')
    insert_index = -1
    
    for i, line in enumerate(lines):
        if 'ci-full:' in line and '## Run complete CI pipeline simulation' in line:
            # Find the end of this section
            for j in range(i+1, len(lines)):
                if lines[j].startswith('.PHONY:') and not lines[j+1].startswith('\t'):
                    insert_index = j
                    break
            break
    
    if insert_index == -1:
        # Fallback: add at the end
        insert_index = len(lines)
    
    # Insert new commands
    new_lines = lines[:insert_index] + new_commands.strip().split('\n') + lines[insert_index:]
    
    # Write updated Makefile
    with open(makefile_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Makefile updated with enhanced CI/CD pipeline commands")
    print("\n📋 New commands added:")
    print("- ci-smoke, ci-core, ci-security, ci-full")  
    print("- health-check variants for all environments")
    print("- perf-* commands for performance testing")
    print("- pre-commit, pre-push, pre-release hooks")
    print("- pipeline-status and pipeline-report")
    print("- help-cicd for detailed help")
    print("\n🚀 Try: make help-cicd")

if __name__ == "__main__":
    update_makefile()