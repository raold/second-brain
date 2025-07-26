# Claude Memory - Second Brain Project

## 🏗️ Project Structure Update (2025-07-26)

The project has been reorganized for clarity:
- **main.py** - New application entry point in root directory
- **app/** - Main application module containing all core functionality
- **archive/src_clean_architecture/** - Archived clean architecture attempt (for reference)

To run the application:
```bash
# From project root
python main.py

# Or with uvicorn
uvicorn main:app --reload
```

## 🚨 CRITICAL PROJECT REQUIREMENTS

### Virtual Environment Usage - MANDATORY
**ALWAYS USE THE PROJECT'S .venv FOR ALL OPERATIONS**

- **Never use system Python** - always use `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix)
- **Never install packages globally** - all pip installs must target the .venv
- **The .venv is machine-specific** - each developer's machine has its own .venv with local paths
- **Setup script creates portable .venv** - `python scripts/setup_dev_environment.py` works on any machine

### Correct Commands
```bash
# CORRECT - Always use .venv Python
.venv/Scripts/python.exe scripts/test_runner.py --validation
.venv/Scripts/python.exe -m pip install package_name

# WRONG - Never use system Python
python scripts/test_runner.py --validation
python -m pip install package_name
```

### File Organization
- **Scripts**: All development scripts are in `scripts/` directory
- **Tests**: All tests are in `tests/` with subdirectories (unit, integration, validation, e2e)
- **Config**: All requirements files are in `config/` directory
- **Docs**: All documentation is in `docs/` directory

### Testing Commands
```bash
# Environment validation
python scripts/test_runner.py --validation

# Run specific test types
python scripts/test_runner.py --unit
python scripts/test_runner.py --integration
python scripts/test_runner.py --all

# Setup environment (works on any machine)
python scripts/setup_dev_environment.py
```

### Why This Matters
- **Portability**: Code must work on work computer, laptop, home desktop
- **Dependency Isolation**: Avoid conflicts with system packages
- **Version Control**: Specific package versions in .venv prevent CI/CD failures
- **Team Consistency**: Everyone uses same dependency versions

## Project Context
- **Architecture**: Clean Architecture (v3.0.0) with Domain/Application/Infrastructure layers
- **Tech Stack**: FastAPI, PostgreSQL with pgvector, Redis, Pydantic 2.5.3
- **File Structure**: Organized with scripts/, tests/, config/, docs/ directories
- **CI/CD**: GitHub Actions with dependency validation and testing

**Remember**: The user was frustrated about hardcoded Python paths from different machines. The .venv solution ensures portability across all their computers.