# Manual Import Test Files

This directory contains manual test files that were previously scattered in the root directory. These files are primarily used for:

## Purpose
- Testing import chains and dependencies
- Verifying the application can start without import errors
- Quick manual verification during development
- Debugging import issues

## Files
- `test_imports.py` - General import testing
- `test_synthesis_imports.py` - Tests for synthesis module imports
- `test_key_imports.py` - Tests for critical imports
- `test_app_startup.py` - Application startup verification
- `test_server_start.py` - Server initialization tests
- `test_graph_metrics.py` - Graph metrics import tests
- `quick_app_test.py` - Quick application test
- `final_import_test.py` - Final import verification

## Usage
These are manual test files, not part of the automated test suite. Run them individually when debugging import issues:

```bash
python tests/manual/import_tests/test_imports.py
```

## Note
These files were moved from the root directory on 2025-07-31 as part of the folder structure cleanup initiative to maintain a cleaner project structure.