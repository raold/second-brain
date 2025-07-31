# Folder Structure Cleanup Plan

## ✅ CLEANUP COMPLETED (2025-07-31 19:00)

### 1. Test Files Moved from Root Directory
The following test files have been moved to `tests/manual/import_tests/`:
- ✅ `test_app_startup.py`
- ✅ `test_synthesis_imports.py`
- ✅ `test_imports.py`
- ✅ `test_graph_metrics.py`
- ✅ `quick_app_test.py`
- ✅ `test_server_start.py`
- ✅ `test_key_imports.py`
- ✅ `final_import_test.py`

### 2. Script Files Moved from Root Directory
These scripts have been moved to `scripts/development/`:
- ✅ `auto_fix_imports.py`
- ✅ `check_imports.py`

### 3. Inconsistent Organization
- Some services are in `app/services/` while they should follow a cleaner structure
- Test files are scattered across multiple locations
- Documentation files are mixed in root with code files

## Proposed Clean Structure

```
second-brain/
├── app/                      # Application code
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration
│   ├── core/                # Core functionality
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   ├── routes/              # API routes
│   ├── repositories/        # Data access layer
│   ├── utils/               # Utilities
│   └── static/              # Static files
├── tests/                   # All test files
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── performance/        # Performance tests
│   ├── validation/         # Validation tests
│   └── manual/             # Manual test scripts
├── scripts/                # Development and deployment scripts
│   ├── setup/              # Setup scripts
│   ├── deployment/         # Deployment scripts
│   └── development/        # Development tools
├── docs/                   # All documentation
│   ├── api/                # API documentation
│   ├── architecture/       # Architecture docs
│   ├── development/        # Development guides
│   └── deployment/         # Deployment guides
├── config/                 # Configuration files
│   └── requirements/       # Requirements files
├── docker/                 # Docker related files
├── migrations/             # Database migrations
├── .github/               # GitHub specific files
│   └── workflows/         # CI/CD workflows
├── README.md              # Main README
├── LICENSE                # License file
├── pyproject.toml         # Python project config
├── docker-compose.yml     # Docker compose
└── Makefile              # Make commands
```

## Migration Plan

### Step 1: Move Test Files
```bash
# Move root test files to appropriate test directories
mkdir -p tests/manual/import_tests
mv test_app_startup.py tests/manual/import_tests/
mv test_synthesis_imports.py tests/manual/import_tests/
mv test_imports.py tests/manual/import_tests/
mv test_graph_metrics.py tests/manual/import_tests/
mv quick_app_test.py tests/manual/import_tests/
mv test_server_start.py tests/manual/import_tests/
mv test_key_imports.py tests/manual/import_tests/
mv final_import_test.py tests/manual/import_tests/
```

### Step 2: Move Script Files
```bash
# Move script files to scripts directory
mv auto_fix_imports.py scripts/development/
mv check_imports.py scripts/development/
```

### Step 3: Reorganize Documentation ✅ COMPLETED
```bash
# Move documentation to docs folder
mkdir -p docs/project docs/development docs/releases
mv CHANGELOG.md docs/
mv CODE_OF_CONDUCT.md docs/project/
mv CONTRIBUTING.md docs/project/
mv SECURITY.md docs/project/
mv OPENAI_SETUP.md docs/development/
mv PROJECT_SETUP.md docs/development/
mv project-setup-instructions.md docs/development/
mv QUICK_REFERENCE.md docs/development/
mv quick-reference.md docs/development/
mv RELEASE_NOTES_v3.0.0.md docs/releases/
mv IMPORT_FIXES_SUMMARY.md docs/development/
mv ROUTE_FIXES_SUMMARY.md docs/development/
```

### Step 4: Update Import Paths
All files that import from moved files need to be updated.

### Step 5: Update CI/CD and Scripts
Update any CI/CD workflows and scripts that reference the old paths.

## Files to Keep in Root

These files should remain in the root directory:
- `README.md` - Main project README
- `LICENSE` - License file
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Pytest configuration
- `ruff.toml` - Ruff configuration
- `docker-compose.yml` - Main docker compose
- `Dockerfile` - Main dockerfile
- `Makefile` - Make commands
- `.gitignore` - Git ignore file
- `alembic.ini` - Alembic configuration
- `main.py` - Application entry point

## Implementation Script ✅ CREATED

The automated cleanup script has been created at `scripts/cleanup_folder_structure.py`.

### Usage:
```bash
# Dry run (check what would be moved)
python scripts/cleanup_folder_structure.py

# Execute cleanup
python scripts/cleanup_folder_structure.py --execute
```

## Summary of Changes Made

1. **Test Files**: 8 test files moved from root to `tests/manual/import_tests/`
2. **Scripts**: 2 development scripts moved from root to `scripts/development/`
3. **Documentation**: 12 documentation files organized into `docs/` subdirectories
4. **Automation**: Created cleanup script for future maintenance

The root directory is now clean and contains only essential project files.