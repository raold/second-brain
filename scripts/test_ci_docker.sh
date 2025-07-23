#!/bin/bash
# Test CI/CD using Docker to avoid local environment issues

set -e

echo "=== Second Brain v2.8.2 CI/CD Test (Docker) ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker to run CI/CD tests.${NC}"
    exit 1
fi

echo -e "${YELLOW}Building Docker image for CI/CD testing...${NC}"

# Create a temporary Dockerfile for testing
cat > Dockerfile.ci-test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install pytest pytest-asyncio pytest-cov

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV USE_MOCK_DATABASE=true
ENV API_TOKENS=test-key-1,test-key-2

# Run tests
CMD ["bash", "-c", "python scripts/run_ci_checks.py"]
EOF

# Create the CI check script
cat > scripts/run_ci_checks.py << 'EOF'
#!/usr/bin/env python3
"""Run CI/CD checks inside Docker container"""

import subprocess
import sys
import os

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def run_command(cmd, description):
    """Run a command and report status."""
    print(f"\n{YELLOW}=== {description} ==={RESET}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{GREEN}✓ {description} passed{RESET}")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"{RED}✗ {description} failed{RESET}")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False
    except Exception as e:
        print(f"{RED}✗ {description} error: {e}{RESET}")
        return False

def main():
    """Run all CI/CD checks."""
    checks = [
        ("ruff --version", "Ruff Version Check"),
        ("ruff check . --exit-zero", "Ruff Linting"),
        ("ruff format --check . --diff", "Ruff Formatting"),
        ("python -m py_compile app/models/synthesis/*.py", "Synthesis Models Syntax"),
        ("python -m py_compile app/services/synthesis/*.py", "Synthesis Services Syntax"),
        ("python -m py_compile app/routes/synthesis_routes.py", "Synthesis Routes Syntax"),
        ("python -c 'from app.models.synthesis import *'", "Synthesis Models Import"),
        ("python -c 'from app.services.synthesis import *'", "Synthesis Services Import"),
        ("python -c 'from app.routes.synthesis_routes import router'", "Synthesis Routes Import"),
        ("pytest tests/unit/synthesis/test_report_models.py::TestReportModels::test_report_type_enum -v", "Sample Unit Test"),
        ("pytest -m synthesis --collect-only", "Synthesis Test Collection"),
    ]
    
    failed_checks = []
    for cmd, description in checks:
        if not run_command(cmd, description):
            failed_checks.append(description)
    
    print(f"\n{'='*60}")
    if not failed_checks:
        print(f"{GREEN}✓ All CI/CD checks passed!{RESET}")
        return 0
    else:
        print(f"{RED}✗ {len(failed_checks)} checks failed:{RESET}")
        for check in failed_checks:
            print(f"  - {check}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Build the Docker image
docker build -f Dockerfile.ci-test -t second-brain-ci-test . || {
    echo -e "${RED}Failed to build Docker image${NC}"
    exit 1
}

# Run the CI/CD tests
echo -e "${YELLOW}Running CI/CD tests in Docker...${NC}"
docker run --rm second-brain-ci-test

# Cleanup
rm -f Dockerfile.ci-test scripts/run_ci_checks.py

echo -e "${GREEN}CI/CD test complete!${NC}"