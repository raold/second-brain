# Development Scripts

This directory contains development utility scripts for maintaining and debugging the Second Brain codebase.

## Scripts

### auto_fix_imports.py
Automatically fixes import issues in the codebase by:
- Detecting missing imports
- Organizing import statements
- Removing unused imports

### check_imports.py
Validates all imports in the codebase:
- Checks for circular dependencies
- Verifies all imports resolve correctly
- Reports import chains

## Usage

```bash
python scripts/development/check_imports.py
python scripts/development/auto_fix_imports.py
```

## Note
These scripts were moved from the root directory on 2025-07-31 as part of the folder structure cleanup initiative.