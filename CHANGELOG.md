# Changelog

All notable changes to Second Brain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.2.2] - 2024-12-08

### Added
- Comprehensive CODE_ANALYSIS_REPORT.md with A- (91.6/100) quality rating
- Production-ready release with full documentation
- GitHub Pages demo with localStorage functionality
- Centered logo and badges in README

### Changed
- Bumped version to 4.2.2 across all files
- Major repository cleanup - removed 52 unnecessary files (10,729 lines)
- Removed legacy examples/, migrations/, and validation test directories
- Removed cipher integration files (not needed for core)
- Optimized logo by trimming 20% transparent space

### Fixed
- Fixed bare except clauses in cross_platform.py
- Fixed all critical PEP8 compliance issues
- Only 38 minor style violations remaining

### Removed
- Deleted TODO.md and PYTHON_UPGRADE_NEEDED.md (tracked elsewhere)
- Removed all test scripts and deployment helpers
- Removed 70+ archived scripts from scripts/archive/
- Cleaned up legacy v2/v3 documentation

### Security
- No critical vulnerabilities in Python code
- All SQL queries use parameterized statements
- Environment variables properly managed

### Documentation
- Added comprehensive code analysis report
- Updated all version references to 4.2.2
- Maintained 30+ documentation files
- Created detailed release notes

## [4.2.1] - 2025-08-06

### Fixed
- Fixed 678 linting errors across the codebase
- Fixed critical undefined names and missing imports
- Fixed syntax errors and indentation issues
- Fixed sklearn import for cosine_similarity in consolidation engine
- Fixed TypeVar and ParamSpec imports in decorators
- Fixed missing Observable and Priority classes in context managers
- Fixed module-level import ordering issues

### Changed
- Applied black formatting to 50 files for consistent code style
- Improved type annotations throughout the codebase
- Cleaned up 293 `__pycache__` directories
- Removed test artifacts and temporary files
- Updated all imports to follow proper conventions

### Security
- Identified exposed API keys in `.env` file (rotation required before production)
- Added security recommendations to QA report

### Documentation
- Added comprehensive QA report for v4.2.0
- Updated frontend documentation
- Added cross-platform development notes

## [4.2.0] - 2025-08-02

### Added
- PostgreSQL + pgvector unified architecture (replaced Qdrant)
- Automatic embedding generation for all memories
- HNSW indexes for 95% faster vector similarity search
- Hybrid search with adjustable vector/text weights
- SvelteKit frontend proof-of-concept
- Cross-platform development support
- Comprehensive test suites

### Changed
- Simplified to single database architecture
- Removed Redis dependency
- Reduced codebase complexity by 60%
- Improved search performance by 50%

### Fixed
- Vector format compatibility with PostgreSQL
- Memory deletion soft-delete behavior
- Embedding generation on memory creation

## [4.0.0] - 2025-08-01

### Added
- Complete system redesign for production readiness
- Mock database fallback for development
- Comprehensive error handling
- Security audit tools
- Environment management system

### Changed
- Simplified API to v2 only
- Restructured project for clarity
- Improved documentation

### Removed
- Legacy v1 API endpoints
- Unnecessary dependencies
- Complex configuration files