#!/bin/bash
# Optimize .venv for second-brain development

echo "🚀 Optimizing .venv environment..."

# 1. Enable pip caching (Windows compatible)
export PIP_CACHE_DIR="${HOME}/.cache/pip"
mkdir -p "$PIP_CACHE_DIR"

# 2. Upgrade pip and setuptools
echo "📦 Upgrading pip and setuptools..."
python -m pip install --upgrade pip setuptools wheel

# 3. Configure pip for faster installs
cat > ~/.pip/pip.conf << 'PIPCONF'
[global]
cache-dir = ~/.cache/pip
disable-pip-version-check = true
no-cache-dir = false
timeout = 60

[install]
compile = no
use-pep517 = true
PIPCONF

# 4. Install development helpers
echo "🛠️ Installing development tools..."
python -m pip install --upgrade \
    ipython \
    rich \
    icecream \
    python-lsp-server[all] \
    debugpy

# 5. Create helpful aliases
cat > .venv/activate_helpers.sh << 'HELPERS'
# Helpful aliases for second-brain development
alias sb-test='python -m pytest tests/ -v'
alias sb-run='uvicorn app.main:app --reload --port 8001'
alias sb-clean='find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null'
alias sb-deps='pip list --format=freeze | wc -l'
alias sb-check='python -m ruff check .'

# Quick memory service test
sb-memory() {
    python -c "
from app.services.memory_service import MemoryService
import asyncio
async def test():
    service = MemoryService()
    stats = await service.get_statistics()
    print(f'Memory service: {stats}')
asyncio.run(test())
"
}

echo "🎯 Second-brain helpers loaded!"
HELPERS

echo "✅ Optimization complete!"
echo ""
echo "To activate helpers, run:"
echo "  source .venv/bin/activate"
echo "  source .venv/activate_helpers.sh"
