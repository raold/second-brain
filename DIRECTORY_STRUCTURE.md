# 📁 Second Brain Directory Structure Guide

**PERMANENT REFERENCE** - This is the canonical guide for where files belong

## 🎯 Core Principles
1. **Clarity**: Every file has ONE obvious location
2. **Simplicity**: Flat structure where possible, nested only when necessary
3. **Purpose**: Directory names clearly indicate content purpose
4. **No Redundancy**: One file, one location, no duplicates

## 📂 Directory Structure

```
second-brain/
├── 📱 app/                    # Application source code
│   ├── api/                   # API endpoints and routes
│   ├── core/                  # Core business logic
│   ├── services/              # Service layer (memory, auth, etc.)
│   ├── models/                # Data models and schemas
│   ├── utils/                 # Utility functions and helpers
│   └── database/              # Database connections and queries
│
├── 🧪 tests/                  # All test files
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── e2e/                   # End-to-end tests
│   └── fixtures/              # Test fixtures and mocks
│
├── 📚 docs/                   # Documentation ONLY
│   ├── api/                   # API documentation
│   ├── guides/                # User and developer guides
│   ├── architecture/          # System design docs
│   └── releases/              # Release notes and changelogs
│
├── 🔧 scripts/                # Utility and automation scripts
│   ├── setup/                 # Installation and setup scripts
│   ├── testing/               # Test runners and helpers
│   ├── deployment/            # Deployment scripts
│   └── maintenance/           # Cleanup and maintenance scripts
│
├── 🎨 static/                 # Static files for web UI
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript files
│   ├── images/                # Images and icons
│   └── templates/             # HTML templates
│
├── 🐳 docker/                 # Docker configuration
│   ├── dev/                   # Development containers
│   ├── prod/                  # Production containers
│   └── compose/               # Docker Compose files
│
├── ☸️ k8s/                    # Kubernetes configuration
│   ├── base/                  # Base configurations
│   ├── overlays/              # Environment-specific overlays
│   └── charts/                # Helm charts
│
├── 🌐 frontend/               # Frontend application (if separate)
│   ├── src/                   # Source code
│   ├── public/                # Public assets
│   └── build/                 # Build output (gitignored)
│
├── 📊 data/                   # Data storage (gitignored)
│   ├── memories/              # Memory storage
│   ├── embeddings/            # Vector embeddings
│   └── cache/                 # Temporary cache
│
└── 🔧 config/                 # Configuration files
    ├── env/                   # Environment configs
    ├── nginx/                 # Web server configs
    └── ci/                    # CI/CD configs
```

## 📝 File Placement Rules

### ✅ What Goes Where

#### `/app` - Application Code
- ✅ Python source files (.py)
- ✅ Business logic
- ✅ API routes
- ✅ Database models
- ❌ Tests
- ❌ Documentation
- ❌ Configuration files

#### `/tests` - Test Files
- ✅ All test files (*_test.py, test_*.py)
- ✅ Test fixtures
- ✅ Mock data
- ✅ conftest.py
- ❌ Application code
- ❌ Documentation

#### `/docs` - Documentation
- ✅ Markdown documentation
- ✅ API specifications
- ✅ Architecture diagrams
- ✅ Release notes
- ❌ Code files
- ❌ Test files
- ❌ Config files

#### `/scripts` - Automation Scripts
- ✅ Setup scripts
- ✅ Deployment scripts
- ✅ Utility scripts
- ✅ Database migrations
- ❌ Application code
- ❌ Tests

#### `/static` - Web Assets
- ✅ CSS files
- ✅ JavaScript files
- ✅ Images
- ✅ HTML templates
- ❌ Backend code
- ❌ Documentation

#### `/docker` - Container Config
- ✅ Dockerfiles
- ✅ Docker Compose files
- ✅ Container scripts
- ❌ Application code
- ❌ Non-Docker configs

#### Root Directory `/`
- ✅ README.md
- ✅ LICENSE
- ✅ .gitignore
- ✅ requirements.txt / pyproject.toml
- ✅ Makefile
- ✅ Single main config files
- ❌ Multiple versions of same file
- ❌ Temporary files
- ❌ Cache directories

## 🚫 What NOT to Keep

### Never Commit These
- `__pycache__/` directories
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `*.pyc` files
- `.env` files with secrets
- `node_modules/`
- `venv/` or `.venv/` (except .venv for this project)
- `*.log` files
- `*.tmp` or `*.bak` files
- IDE configs (`.idea/`, `.vscode/` - optional)

### Remove Immediately
- Duplicate files (LICENSE vs LICENSE.md)
- Backup files (*_backup, *_old)
- Temporary test files
- Old archive directories
- Unused dependencies
- Dead code files

## 🔄 Regular Maintenance

### Weekly Cleanup Checklist
```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove pytest cache
rm -rf .pytest_cache

# Remove mypy cache
rm -rf .mypy_cache

# Remove temporary files
find . -name "*.tmp" -o -name "*.bak" -o -name "*~" -delete

# Remove empty directories
find . -type d -empty -delete
```

### Before Each Commit
1. Check for accidental cache files
2. Ensure no duplicate files
3. Verify file is in correct directory
4. Remove any temporary test files

## 📋 New File Checklist

When adding a new file, ask:

1. **Is this code?** → `/app`
2. **Is this a test?** → `/tests`
3. **Is this documentation?** → `/docs`
4. **Is this a script?** → `/scripts`
5. **Is this web content?** → `/static`
6. **Is this config?** → `/config` or root
7. **Is this temporary?** → Don't commit it

## 🎯 Examples

### ✅ Correct Placement
- API endpoint: `/app/api/routes/memories.py`
- Memory service: `/app/services/memory_service.py`
- Unit test: `/tests/unit/test_memory_service.py`
- Setup guide: `/docs/guides/setup.md`
- Database script: `/scripts/setup/init_db.py`
- CSS file: `/static/css/main.css`

### ❌ Incorrect Placement
- Test in app: `/app/test_memory.py` ❌
- Doc in root: `/API_GUIDE.md` ❌
- Script in app: `/app/setup_db.py` ❌
- Config in docs: `/docs/config.yaml` ❌

## 🔍 Quick Reference

| File Type | Location | Example |
|-----------|----------|---------|
| Python modules | `/app` | `/app/services/memory.py` |
| Tests | `/tests` | `/tests/unit/test_api.py` |
| Docs | `/docs` | `/docs/guides/api.md` |
| Scripts | `/scripts` | `/scripts/setup/install.py` |
| Web files | `/static` | `/static/js/app.js` |
| Docker | `/docker` | `/docker/Dockerfile.prod` |
| K8s | `/k8s` | `/k8s/deployment.yaml` |
| Config | `/config` or `/` | `/config/prod.env` |

## 🚀 Implementation

This structure is enforced through:
1. `.gitignore` - Prevents committing wrong files
2. CI/CD checks - Validates structure
3. Pre-commit hooks - Catches issues early
4. Code reviews - Human verification

---

**Remember**: A clean directory structure makes development faster, onboarding easier, and maintenance simpler. When in doubt, refer to this guide!