# Changelog

All notable changes to Second Brain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.2.3] - 2025-08-06

### Added
- Comprehensive QA report documenting code quality status
- Summary documentation for v4.2.1 release
- Professional release management workflow

### Changed
- Skipped v4.2.2 to align with user expectations
- Enhanced documentation organization

### Fixed
- Version consistency across all configuration files
- Documentation references to current version

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